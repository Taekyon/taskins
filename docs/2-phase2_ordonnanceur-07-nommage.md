# Taskins — Convention de nommage

## Identifiant racine

`taskins` — utilisé comme base pour l'image Docker, le package Python, les volumes et le réseau.

## Structure des modules (par couche)

Voir `03-architecture-applicative.md` pour l'arborescence complète : `routes/`, `services/`, `models/`, `schemas/`, `core/`.

## Endpoints API REST

Préfixe `/api/v1`, ressources au pluriel, kebab-case.

```
GET    /api/v1/workflows
POST   /api/v1/workflows
GET    /api/v1/workflows/{id}
POST   /api/v1/workflows/{id}/submit
POST   /api/v1/workflows/{id}/execute
GET    /api/v1/workflows/{id}/executions
GET    /api/v1/machines
POST   /api/v1/machines
GET    /api/v1/users
```

## Docker

| Élément | Nom |
|---|---|
| Image | `taskins:latest` |
| Service Compose | `taskins` |
| Conteneur | `taskins-app` |
| Volume base de données | `taskins-db` (suffixé par environnement en multi-environnement — voir `09-environnement-docker.md`) |
| Réseau | `taskins-net` |
| Fichiers Compose | `docker-compose.yml`, `docker-compose.dev.yml` |

## Variables d'environnement

`SCREAMING_SNAKE_CASE`, préfixe `TASKINS_`.

```env
TASKINS_SECRET_KEY=
TASKINS_DEBUG=false
TASKINS_DB_PATH=/app/data/taskins.db
TASKINS_SSH_KEY_PATH=/app/secrets/taskins_ed25519
TASKINS_SCHEDULER_INTERVAL=10
```
