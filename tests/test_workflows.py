"""Création, validation et cycle de vie des workflows."""

from conftest import make_workflow

TROIS_TACHES = [
    {"name": "verifier", "command": "ping -c 1 storage", "target": "worker-1"},
    {"name": "sauvegarder", "command": "pg_dump base > /tmp/d.sql", "target": "worker-1",
     "condition": {"task": "verifier", "return_code": 0}},
    {"name": "nettoyer", "command": "rm /tmp/d.sql", "target": "worker-1",
     "condition": {"task": "sauvegarder", "return_code": 0}},
]


def test_creation_avec_conditions_en_chaine(admin):
    r = admin.post("/api/v1/workflows", json={"name": "sauvegarde", "tasks": TROIS_TACHES})
    assert r.status_code == 201
    corps = r.json()
    assert corps["status"] == "DRAFT"
    assert [t["order_index"] for t in corps["tasks"]] == [1, 2, 3]
    assert corps["tasks"][1]["condition"] == {"task": "verifier", "return_code": 0}
    assert corps["tasks"][0]["condition"] is None


def test_nom_de_tache_duplique_refuse(admin):
    r = admin.post("/api/v1/workflows", json={"name": "x", "tasks": [
        {"name": "t", "command": "echo a", "target": "worker-1"},
        {"name": "t", "command": "echo b", "target": "worker-1"},
    ]})
    assert r.status_code == 422


def test_condition_vers_tache_ulterieure_refusee(admin):
    r = admin.post("/api/v1/workflows", json={"name": "x", "tasks": [
        {"name": "a", "command": "echo a", "target": "worker-1",
         "condition": {"task": "b", "return_code": 0}},
        {"name": "b", "command": "echo b", "target": "worker-1"},
    ]})
    assert r.status_code == 422


def test_condition_vers_tache_inexistante_refusee(admin):
    r = admin.post("/api/v1/workflows", json={"name": "x", "tasks": [
        {"name": "a", "command": "echo a", "target": "worker-1",
         "condition": {"task": "fantome", "return_code": 0}},
    ]})
    assert r.status_code == 422


def test_machine_cible_inconnue_refusee(admin):
    r = admin.post("/api/v1/workflows", json={"name": "x", "tasks": [
        {"name": "a", "command": "echo a", "target": "inexistante"},
    ]})
    assert r.status_code == 422 and "inconnue" in r.json()["detail"]


def test_liste_de_taches_vide_refusee(admin):
    assert admin.post("/api/v1/workflows", json={"name": "x", "tasks": []}).status_code == 422


def test_timeout_explicite_et_par_defaut(admin):
    r = admin.post("/api/v1/workflows", json={"name": "x", "tasks": [
        {"name": "a", "command": "echo a", "target": "worker-1", "timeout_seconds": 42},
        {"name": "b", "command": "echo b", "target": "worker-1"},
    ]})
    taches = r.json()["tasks"]
    assert taches[0]["timeout_seconds"] == 42
    assert taches[1]["timeout_seconds"] is None


def test_timeout_negatif_refuse(admin):
    r = admin.post("/api/v1/workflows", json={"name": "x", "tasks": [
        {"name": "a", "command": "echo a", "target": "worker-1", "timeout_seconds": 0},
    ]})
    assert r.status_code == 422


def test_soumission_passe_en_pending(admin):
    wid = make_workflow(admin, "wf")
    assert admin.post(f"/api/v1/workflows/{wid}/submit").json()["status"] == "PENDING"


def test_double_soumission_refusee(admin):
    wid = make_workflow(admin, "wf", submit=True)
    assert admin.post(f"/api/v1/workflows/{wid}/submit").status_code == 409


def test_execution_avant_soumission_refusee(admin):
    wid = make_workflow(admin, "wf")
    assert admin.post(f"/api/v1/workflows/{wid}/execute").status_code == 409


def test_executions_multiples(admin):
    """F4 : un workflow approuvé reste PENDING et peut être relancé."""
    wid = make_workflow(admin, "wf", submit=True)
    for _ in range(3):
        assert admin.post(f"/api/v1/workflows/{wid}/execute").status_code == 201
    assert len(admin.get(f"/api/v1/workflows/{wid}/executions").json()) == 3
    assert admin.get(f"/api/v1/workflows/{wid}").json()["status"] == "PENDING"


def test_retargeting(admin):
    admin.post("/api/v1/machines", json={"alias": "worker-2", "host": "10.0.0.2"})
    wid = make_workflow(admin, "wf", submit=True)
    r = admin.post(f"/api/v1/workflows/{wid}/execute", json={"machine": "worker-2"})
    assert r.status_code == 201 and r.json()["target_machine"] == "worker-2"
    sans = admin.post(f"/api/v1/workflows/{wid}/execute")
    assert sans.json()["target_machine"] is None


def test_retargeting_machine_inconnue_refuse(admin):
    wid = make_workflow(admin, "wf", submit=True)
    assert admin.post(f"/api/v1/workflows/{wid}/execute", json={"machine": "?"}).status_code == 422


def test_archivage_conserve_l_historique(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/execute")
    run_engine()
    assert admin.post(f"/api/v1/workflows/{wid}/archive").status_code == 200
    assert wid not in [w["id"] for w in admin.get("/api/v1/workflows").json()]
    assert wid in [w["id"] for w in admin.get("/api/v1/workflows?include_archived=true").json()]
    assert len(admin.get(f"/api/v1/workflows/{wid}/executions").json()) == 1


def test_workflow_archive_non_executable(admin):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/archive")
    assert admin.post(f"/api/v1/workflows/{wid}/execute").status_code == 409


def test_desarchivage(admin):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/archive")
    assert admin.post(f"/api/v1/workflows/{wid}/unarchive").status_code == 200
    assert admin.post(f"/api/v1/workflows/{wid}/execute").status_code == 201


def test_suppression_efface_tout_l_historique(admin, run_engine):
    from taskins.core.database import SessionLocal
    from taskins.models.execution import Execution
    from taskins.models.task import Task
    from taskins.models.task_result import TaskResult

    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/execute")
    run_engine()

    assert admin.delete(f"/api/v1/workflows/{wid}").status_code == 204

    db = SessionLocal()
    assert db.query(Task).filter_by(workflow_id=wid).count() == 0
    assert db.query(Execution).filter_by(workflow_id=wid).count() == 0
    assert db.query(TaskResult).count() == 0
    db.close()
    assert admin.get(f"/api/v1/workflows/{wid}").status_code == 404


def test_standard_ne_peut_supprimer_le_workflow_d_autrui(admin, app_client):
    wid = make_workflow(admin, "wf-admin")
    admin.post("/api/v1/users", json={"username": "zoe", "password": "motdepasse1"})
    app_client.cookies.clear()
    app_client.post("/login", data={"username": "zoe", "password": "motdepasse1"}, follow_redirects=False)
    assert app_client.delete(f"/api/v1/workflows/{wid}").status_code == 403
    assert app_client.post(f"/api/v1/workflows/{wid}/archive").status_code == 403


def test_workflow_inexistant(admin):
    assert admin.get("/api/v1/workflows/9999").status_code == 404
    assert admin.delete("/api/v1/workflows/9999").status_code == 404
