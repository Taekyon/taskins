"""Configuration commune aux tests.

Trois précautions structurantes :

1. Les variables d'environnement sont posées AVANT tout import de `taskins` :
   `core.database` construit son moteur SQLAlchemy à l'import, à partir de
   `settings`. Les poser après n'aurait aucun effet.

2. `TASKINS_SCHEDULER_INTERVAL` est mis très haut pour que la boucle de fond
   ne se déclenche jamais pendant un test. Les tests appellent explicitement
   `scan_and_process_pending_executions()` : le moteur est ainsi déterministe,
   plutôt que dépendant du temps qui passe.

3. `execute_command` est remplacé dès l'import par un enregistreur : aucun test
   n'ouvre de vraie connexion SSH.
"""

import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="taskins-test-")
os.close(_db_fd)

os.environ["TASKINS_SECRET_KEY"] = "cle-de-test"
os.environ["TASKINS_DB_PATH"] = _db_path
os.environ["TASKINS_BOOTSTRAP_ADMIN_USERNAME"] = "admin"
os.environ["TASKINS_BOOTSTRAP_ADMIN_PASSWORD"] = "motdepasse-admin"
os.environ["TASKINS_TIMEZONE"] = "Europe/Paris"
os.environ["TASKINS_DEFAULT_TASK_TIMEOUT"] = "300"
os.environ["TASKINS_SCHEDULE_GRACE_SECONDS"] = "60"
os.environ["TASKINS_SCHEDULER_INTERVAL"] = "86400"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import taskins.core.engine as engine_module  # noqa: E402
from taskins.core.database import Base, SessionLocal, engine  # noqa: E402
from taskins.core.database import _bootstrap_admin, _seed  # noqa: E402
from taskins.core.ssh_client import SSHExecutionResult  # noqa: E402

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "motdepasse-admin"


class SSHRecorder:
    """Remplace `execute_command`. Enregistre les appels et délègue le résultat
    à `handler`, que chaque test peut redéfinir."""

    def __init__(self):
        self.calls = []
        self.handler = lambda **kw: SSHExecutionResult(return_code=0, stdout="ok", stderr="")

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.handler(**kwargs)

    def reset(self):
        self.calls.clear()
        self.handler = lambda **kw: SSHExecutionResult(return_code=0, stdout="ok", stderr="")

    @property
    def commands(self):
        return [c["command"] for c in self.calls]

    @property
    def hosts(self):
        return [c["host"] for c in self.calls]


ssh = SSHRecorder()
engine_module.execute_command = ssh


@pytest.fixture(scope="session")
def app_client():
    from taskins.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def clean_database():
    """Base remise à zéro avant chaque test : aucun test ne dépend de l'ordre
    d'exécution ni de l'état laissé par un autre."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _seed(SessionLocal())
    _bootstrap_admin(SessionLocal())
    ssh.reset()
    yield


@pytest.fixture
def client(app_client):
    """Client anonyme (session vidée)."""
    app_client.cookies.clear()
    return app_client


@pytest.fixture
def admin(app_client):
    """Client authentifié en tant qu'administrateur."""
    app_client.cookies.clear()
    # follow_redirects=False : sinon httpx enchaîne sur le GET / et renvoie 200,
    # ce qui masquerait un échec d'authentification.
    response = app_client.post(
        "/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 303, "connexion administrateur impossible"
    return app_client


@pytest.fixture
def user(app_client, admin):
    """Client authentifié en tant qu'utilisateur standard."""
    admin.post("/api/v1/users", json={"username": "standard", "password": "motdepasse1"})
    app_client.cookies.clear()
    response = app_client.post(
        "/login",
        data={"username": "standard", "password": "motdepasse1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return app_client


@pytest.fixture
def run_engine():
    """Déclenche un cycle complet du moteur, de façon synchrone."""
    return engine_module.scan_and_process_pending_executions


@pytest.fixture
def ssh_recorder():
    return ssh


# --- Raccourcis ---

def make_workflow(client, name="wf", tasks=None, submit=False):
    tasks = tasks or [{"name": "t1", "command": "echo bonjour", "target": "worker-1"}]
    response = client.post("/api/v1/workflows", json={"name": name, "tasks": tasks})
    assert response.status_code == 201, response.text
    workflow_id = response.json()["id"]
    if submit:
        assert client.post(f"/api/v1/workflows/{workflow_id}/submit").status_code == 200
    return workflow_id
