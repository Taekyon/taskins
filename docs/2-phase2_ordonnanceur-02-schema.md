# Instructions pour créer le schéma SQL

Ce document décrit, étape par étape, le contenu du fichier SQL permettant de créer la base de données SQLite.

```sql
-- Taskins — Schéma de base de données (SQLite)
-- Compagnon de 02-modele-donnees.md
--
-- CORRECTION : workflows.status ne porte que le cycle conception/approbation
-- (DRAFT, PENDING_APPROVAL, PENDING). Les états RUNNING/DONE/FAILED ont été
-- retirés de cette table et appartiennent exclusivement à executions.status,
-- pour rester cohérent avec "1 Workflow -> N Executions" (F4, exécutions
-- multiples). Voir 00-index.md pour le détail du raisonnement.

PRAGMA foreign_keys = ON;  -- a exécuter a chaque connexion, pas une seule fois

-- ============================================================
-- SECTION 1 — UTILISATEURS ET GROUPES
-- ============================================================

CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    is_admin      INTEGER NOT NULL DEFAULT 0,  -- 0 = standard, 1 = administrateur
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE groups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Table de liaison Many-to-Many entre utilisateurs et groupes
CREATE TABLE user_groups (
    user_id  INTEGER NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, group_id)
);

-- ============================================================
-- SECTION 2 — MACHINES CIBLES
-- ============================================================

CREATE TABLE machines (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    alias      TEXT    NOT NULL UNIQUE,               -- nom logique référencé dans le YAML : "worker-1"
    host       TEXT    NOT NULL,                       -- IP, hostname ou FQDN : paramiko résout les trois
    ssh_user   TEXT    NOT NULL DEFAULT 'svc-taskins',
    ssh_port   INTEGER NOT NULL DEFAULT 22,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- SECTION 3 — WORKFLOWS ET TÂCHES
-- ============================================================

CREATE TABLE workflows (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT,
    owner_id    INTEGER NOT NULL REFERENCES users(id),
    group_id    INTEGER NOT NULL REFERENCES groups(id),
    status      TEXT    NOT NULL DEFAULT 'DRAFT',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),  -- a mettre a jour manuellement par l'application
    CHECK (status IN ('DRAFT','PENDING_APPROVAL','PENDING'))
);

CREATE TABLE tasks (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id             INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    name                    TEXT    NOT NULL,
    command                 TEXT    NOT NULL,
    machine_id              INTEGER NOT NULL REFERENCES machines(id),
    order_index             INTEGER NOT NULL,            -- position dans la séquence (commence à 1)
    condition_task_id       INTEGER REFERENCES tasks(id),  -- NULL = pas de condition
    condition_expected_code INTEGER,                        -- NULL = pas de condition
    UNIQUE (workflow_id, name),
    UNIQUE (workflow_id, order_index),
    -- Les deux colonnes de condition sont soit toutes les deux NULL, soit toutes les deux renseignées
    CHECK (
        (condition_task_id IS NULL AND condition_expected_code IS NULL) OR
        (condition_task_id IS NOT NULL AND condition_expected_code IS NOT NULL)
    )
    -- NOTE : condition_task_id doit référencer une tâche de order_index inférieur,
    -- dans le même workflow. Non exprimable en CHECK SQLite — à valider en couche applicative.
);

-- ============================================================
-- SECTION 4 — EXÉCUTIONS ET RÉSULTATS
-- ============================================================

CREATE TABLE executions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER NOT NULL REFERENCES workflows(id),
    status      TEXT    NOT NULL DEFAULT 'PENDING',
    started_at  TEXT,            -- NULL avant démarrage
    finished_at TEXT,            -- NULL avant fin
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (status IN ('PENDING','RUNNING','DONE','FAILED'))
);

CREATE TABLE task_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    task_id      INTEGER NOT NULL REFERENCES tasks(id),
    status       TEXT    NOT NULL DEFAULT 'PENDING',
    return_code  INTEGER,   -- NULL jusqu'à la fin de la commande SSH
    stdout       TEXT,
    stderr       TEXT,
    started_at   TEXT,
    finished_at  TEXT,
    UNIQUE (execution_id, task_id),   -- un seul résultat par tâche par exécution
    CHECK (status IN ('PENDING','RUNNING','DONE','FAILED'))
);

-- ============================================================
-- DONNÉES INITIALES (V1)
-- ============================================================

-- Groupe par défaut — contourne la logique de visibilité en V1
INSERT INTO groups (name) VALUES ('all');

-- Exemple de machine cible — a remplacer/compléter via l'interface web (approche A)
INSERT INTO machines (alias, host, ssh_user, ssh_port)
VALUES ('worker-1', '192.168.X.X', 'svc-taskins', 22);
```