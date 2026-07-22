-- Étape 11 — planifications (exécution différée + récurrence cron).
-- Alternative au reset de volume, pour conserver une base existante.

CREATE TABLE schedules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id     INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    kind            TEXT    NOT NULL,
    cron_expression TEXT,
    machine_id      INTEGER REFERENCES machines(id),
    next_run_at     TEXT,
    last_run_at     TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    owner_id        INTEGER NOT NULL REFERENCES users(id),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (kind IN ('ONCE','CRON')),
    CHECK ((kind = 'ONCE' AND cron_expression IS NULL) OR
           (kind = 'CRON' AND cron_expression IS NOT NULL))
);

ALTER TABLE executions ADD COLUMN schedule_id INTEGER REFERENCES schedules(id);
