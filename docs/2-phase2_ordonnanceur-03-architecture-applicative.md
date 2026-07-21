# Taskins — Architecture applicative

## Principe retenu

FastAPI sert à la fois l'API REST et les pages web (rendu serveur via Jinja2), dans un seul processus et un seul conteneur. Pas de frontend JavaScript séparé en V1.

## Séparation stricte API / Web

Pour permettre un découplage futur du frontend sans réécrire la logique métier, les routes API et les routes web sont physiquement séparées et n'exécutent jamais de logique métier elles-mêmes — elles appellent uniquement les fonctions de `services/`.

```
taskins/routes/
  api/
    workflows.py     # /api/v1/workflows/...
    machines.py       # /api/v1/machines/...
    users.py            # /api/v1/users/...
  web/
    dashboard.py        # /workflows, /workflows/{id} (pages HTML)
    admin.py              # /admin/users, /admin/machines
```

```python
# routes/web/dashboard.py
@router.get("/workflows")
def list_workflows_page(request: Request, db: Session = Depends(get_db)):
    workflows = workflow_service.list_visible(db)
    return templates.TemplateResponse("workflows.html", {"request": request, "workflows": workflows})

# routes/api/workflows.py
@router.get("/api/v1/workflows")
def list_workflows_api(db: Session = Depends(get_db)):
    return workflow_service.list_visible(db)
```

Détacher le frontend plus tard consiste à supprimer `routes/web/` et `templates/` — l'API n'a jamais dépendu du HTML.

## Structure complète des dossiers

```
taskins/
  main.py

  routes/
    api/
      workflows.py
      machines.py
      users.py
    web/
      dashboard.py
      admin.py

  services/
    workflow_service.py
    machine_service.py
    user_service.py

  core/
    engine.py          # boucle asyncio du moteur d'ordonnancement
    ssh_client.py        # wrapper paramiko — voir 04-protocole-ssh.md
    database.py            # connexion SQLite, session SQLAlchemy
    config.py                # lecture du .env via pydantic-settings — voir 09

  models/               # modèles SQLAlchemy, miroir de 02-schema.sql
  schemas/              # schémas Pydantic (validation entrée/sortie API)
  templates/            # fichiers Jinja2 (.html)
```

## Cycle de vie du moteur

Le moteur tourne comme tâche asyncio de fond, lancée au démarrage de FastAPI via `lifespan`, dans le même processus que le serveur web.

```python
# main.py
from contextlib import asynccontextmanager
import asyncio
from taskins.core.engine import run_engine_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    engine_task = asyncio.create_task(run_engine_loop())
    yield
    engine_task.cancel()

app = FastAPI(lifespan=lifespan)
```

Chaque cycle de la boucle est protégé individuellement, pour qu'une exception sur une exécution ne tue pas la boucle entière :

```python
async def run_engine_loop():
    while True:
        try:
            await scan_and_process_pending_executions()
        except Exception as e:
            logger.error(f"Erreur dans le cycle du moteur : {e}")
        await asyncio.sleep(settings.scheduler_interval)
```

Note : `scan_and_process_pending_executions` — et non `pending_workflows` — voir la correction documentée dans `00-index.md` et `02-modele-donnees.md`.
