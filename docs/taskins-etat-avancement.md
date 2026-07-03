# Taskins — État d'avancement (résumé de reprise)
 
## Contexte
Ordonnanceur de tâches, PoC pour PME (2-3 semaines). Stack : FastAPI, SQLite, SQLAlchemy, paramiko, Jinja2, Docker. Conception figée dans `phase1_ordonnanceur-synthese.md` et `phase2_ordonnanceur-*.md` (docs de référence, lecture seule, non modifiables).
 
## Comptes système (VMs)
- `adm-taskins` : administration (sudo, accès interactif).
- `svc-taskins` : compte de service dédié à l'app (exécution + SSH sortant vers machines cibles).
- `scheduler` : nom utilisé dans les docs de conception (phase1/phase2), **obsolète**, remplacé par `svc-taskins` dans le code. Les docs de conception ne peuvent pas être corrigées (lecture seule) — incohérence connue et assumée.
## Avancement Phase 3 (Réalisation)
 
**Étape 1 — Structure projet : FAIT**
Arborescence `taskins/{core,models,schemas,services,routes/{api,web},templates}`, Dockerfile, `docker-compose.yml`/`.dev.yml`, `requirements.txt`.
⚠️ Proxy d'entreprise : build nécessite `--build-arg HTTP_PROXY/HTTPS_PROXY/NO_PROXY`, déclarés dans `docker-compose.dev.yml` sous `build.args`.
 
**Étape 2 — Modèle de données : FAIT**
Modèles SQLAlchemy (User, Group, Machine, Workflow, Task, Execution, TaskResult). `core/database.py` : `init_db()`, PRAGMA `foreign_keys=ON`, seed (groupe `all` + machine `worker-1`).
 
**Étape 3 — Authentification : FAIT**
bcrypt via passlib, session par cookie signé (Starlette `SessionMiddleware`), bootstrap admin via `TASKINS_BOOTSTRAP_ADMIN_USERNAME`/`PASSWORD` (si table `users` vide). Routes `/login`, `/logout`. Dépendances `core/dependencies.py` (`require_user_web/api`, `require_admin_web/api`).
⚠️ `bcrypt==4.0.1` **obligatoire** en pin — `passlib` 1.7.4 casse avec `bcrypt>=4.1`.
⚠️ Starlette récent : `TemplateResponse(request, nom, contexte)` — `request` en 1er argument positionnel, ancien style `(nom, {"request": ...})` cassé.
 
**Étape 4 — Services/API Machines + Utilisateurs : FAIT**
CRUD machines (`GET` tous connectés, `POST` admin), users (`GET`/`POST`/`PATCH` admin only — F12/F13). Extensions ajoutées au-delà de `07-nommage.md` : `POST /api/v1/users`, `PATCH /api/v1/users/{id}`.
 
**Correction transverse (post étape 4) — FAIT**
Renommage compte de service `scheduler` → `svc-taskins` (défaut `ssh_user` dans `models/machine.py`, `schemas/machine.py`, seed `database.py`). Dockerfile documente en commentaire la décision de rester en `root` (bind mount `secrets/` + risque de désalignement d'UID), à revoir en phase 4 (déploiement).
 
**Étape 5 — Services/API Workflows (création) : FAIT**
`POST /api/v1/workflows` : JSON structuré (name/description/tasks ;
tâche = name/command/target/condition ;
condition = {task, return_code}), validé par `schemas/workflow.py` (Pydantic) + règles métier dans `workflow_service.py` (noms de tâches uniques, cible existante dans `machines`, condition référençant une tâche antérieure). `GET /api/v1/workflows`, `GET /api/v1/workflows/{id}`.
⚠️ Divergence assumée avec la conception figée : `1-phase1_ordonnanceur-synthese.md` ("Format de définition des workflows : YAML") et `2-phase2_ordonnanceur-08-format-yaml.md` décrivent un contrat YAML. L'implémentation retient un JSON structuré équivalent
(mêmes champs) comme contrat canonique de l'API — YAML n'est plus utilisé côté serveur. Docs de conception non modifiables (lecture seule) — incohérence connue et assumée, même traitement que scheduler/svc-taskins. Export YAML à partir du JSON (affichage/portabilité) : hors périmètre V1, à considérer plus tard.

## Points ouverts (à trancher en priorité à la reprise)
1. `PATCH /api/v1/machines/{id}` pas encore implémenté — question posée à l'utilisateur, sans réponse au moment de ce résumé.
2. Infra VMs pas encore faite : création `adm-taskins`/`svc-taskins`, régénération clé ed25519 pour `svc-taskins`, dépôt de la clé publique sur `scheduler-worker`.
3. Volume `taskins-db-dev` à réinitialiser (sinon `worker-1` garde `ssh_user='scheduler'`).
4. Dockerfile `USER` : reporté à la phase 4, pas encore fait.
## Suite prévue (plan)
5. Services/API Workflows — création (YAML, format figé dans `08-format-yaml.md`), soumission, exécution.
6. Moteur d'ordonnancement + client SSH (`core/engine.py`, `core/ssh_client.py` — stubs actuels).
7. Interface web complète (remplace `login.html`/`home.html` temporaires — dashboard, admin users/machines).
8. Tests fonctionnels.
## Reprise
Code complet livré : `taskins-correction-svc.zip` (dernier état). Pour relancer : dézip à la racine, renseigner `.env.dev` (`TASKINS_SECRET_KEY`, `TASKINS_BOOTSTRAP_ADMIN_USERNAME`, `TASKINS_BOOTSTRAP_ADMIN_PASSWORD`), `docker compose -f docker-compose.dev.yml build && up`.