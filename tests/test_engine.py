"""Moteur d'ordonnancement : enchaînement, conditions, timeout, instantané.

Partie la plus délicate du système d'après l'analyse de risque de la phase 1 ;
c'est aussi la plus couverte ici.
"""

from conftest import make_workflow
from taskins.core.database import SessionLocal
from taskins.core.ssh_client import SSHExecutionResult, SSHInfrastructureError, SSHTimeoutError
from taskins.models.execution import Execution
from taskins.models.task_result import TaskResult

DEUX_TACHES = [
    {"name": "t1", "command": "echo un", "target": "worker-1"},
    {"name": "t2", "command": "echo deux", "target": "worker-1"},
]


def _executer(client, run_engine, tasks=None, machine=None):
    wid = make_workflow(client, "wf", tasks=tasks or DEUX_TACHES, submit=True)
    corps = {"machine": machine} if machine else None
    eid = client.post(f"/api/v1/workflows/{wid}/execute", json=corps).json()["id"]
    run_engine()
    return wid, eid


def _resultats(execution_id):
    db = SessionLocal()
    try:
        return sorted(
            db.query(TaskResult).filter_by(execution_id=execution_id).all(),
            key=lambda r: r.id,
        )
    finally:
        db.close()


def _execution(execution_id):
    db = SessionLocal()
    try:
        return db.get(Execution, execution_id)
    finally:
        db.close()


def test_enchainement_serie_dans_l_ordre(admin, run_engine, ssh_recorder):
    _, eid = _executer(admin, run_engine)
    assert ssh_recorder.commands == ["echo un", "echo deux"]
    assert _execution(eid).status == "DONE"
    assert all(r.status == "DONE" for r in _resultats(eid))


def test_dates_de_debut_et_de_fin_renseignees(admin, run_engine):
    _, eid = _executer(admin, run_engine)
    execution = _execution(eid)
    assert execution.started_at and execution.finished_at


def test_code_retour_non_nul_sans_condition_reste_done(admin, run_engine, ssh_recorder):
    """Distinction structurante : un code non nul est un résultat, pas une panne."""
    ssh_recorder.handler = lambda **kw: SSHExecutionResult(
        return_code=1 if kw["command"] == "echo un" else 0, stdout="", stderr=""
    )
    _, eid = _executer(admin, run_engine)
    assert _execution(eid).status == "DONE"
    assert _resultats(eid)[0].return_code == 1
    assert len(ssh_recorder.calls) == 2, "la tâche suivante doit quand même s'exécuter"


def test_condition_satisfaite_poursuit(admin, run_engine, ssh_recorder):
    taches = [
        {"name": "t1", "command": "echo un", "target": "worker-1"},
        {"name": "t2", "command": "echo deux", "target": "worker-1",
         "condition": {"task": "t1", "return_code": 0}},
    ]
    _, eid = _executer(admin, run_engine, tasks=taches)
    assert _execution(eid).status == "DONE"
    assert len(ssh_recorder.calls) == 2


def test_condition_non_satisfaite_arrete_l_execution(admin, run_engine, ssh_recorder):
    ssh_recorder.handler = lambda **kw: SSHExecutionResult(return_code=1, stdout="", stderr="")
    taches = [
        {"name": "t1", "command": "echo un", "target": "worker-1"},
        {"name": "t2", "command": "echo deux", "target": "worker-1",
         "condition": {"task": "t1", "return_code": 0}},
        {"name": "t3", "command": "echo trois", "target": "worker-1"},
    ]
    _, eid = _executer(admin, run_engine, tasks=taches)
    assert _execution(eid).status == "FAILED"
    assert len(ssh_recorder.calls) == 1, "seule t1 doit avoir tourné"

    resultats = _resultats(eid)
    assert len(resultats) == 2, "t3 ne doit pas produire de résultat"
    assert resultats[1].status == "FAILED"
    assert resultats[1].return_code is None, "une tâche non lancée n'a pas de code retour"


def test_echec_infrastructure(admin, run_engine, ssh_recorder):
    def injoignable(**kw):
        raise SSHInfrastructureError("machine injoignable")

    ssh_recorder.handler = injoignable
    _, eid = _executer(admin, run_engine)
    assert _execution(eid).status == "FAILED"
    resultats = _resultats(eid)
    assert len(resultats) == 1
    assert resultats[0].status == "FAILED"
    assert resultats[0].return_code is None
    assert "injoignable" in resultats[0].stderr


def test_timeout_marque_la_tache_en_echec(admin, run_engine, ssh_recorder):
    def trop_long(**kw):
        raise SSHTimeoutError(f"Timeout : {kw['timeout_seconds']}s dépassées")

    ssh_recorder.handler = trop_long
    taches = [{"name": "t1", "command": "sleep 30", "target": "worker-1", "timeout_seconds": 5}]
    _, eid = _executer(admin, run_engine, tasks=taches)
    assert _execution(eid).status == "FAILED"
    assert "Timeout" in _resultats(eid)[0].stderr


def test_timeout_transmis_au_client_ssh(admin, run_engine, ssh_recorder):
    taches = [
        {"name": "t1", "command": "echo un", "target": "worker-1", "timeout_seconds": 42},
        {"name": "t2", "command": "echo deux", "target": "worker-1"},
    ]
    _executer(admin, run_engine, tasks=taches)
    assert ssh_recorder.calls[0]["timeout_seconds"] == 42
    assert ssh_recorder.calls[1]["timeout_seconds"] == 300, "repli sur la valeur par défaut"


def test_instantane_de_commande_et_de_machine(admin, run_engine):
    _, eid = _executer(admin, run_engine)
    resultat = _resultats(eid)[0]
    assert resultat.command == "echo un"
    assert resultat.machine_alias == "worker-1"
    assert resultat.machine_host


def test_instantane_survit_a_la_modification_de_la_definition(admin, run_engine):
    """Objectif de l'étape 9 : l'historique doit rester fidèle même si la
    définition change par la suite."""
    from taskins.models.task import Task

    wid, eid = _executer(admin, run_engine)
    db = SessionLocal()
    tache = db.query(Task).filter_by(workflow_id=wid, name="t1").first()
    tache.command = "commande modifiee apres coup"
    db.commit()
    db.close()
    assert _resultats(eid)[0].command == "echo un"


def test_retargeting_redirige_toutes_les_taches(admin, run_engine, ssh_recorder):
    admin.post("/api/v1/machines", json={"alias": "worker-2", "host": "10.0.0.2"})
    _, eid = _executer(admin, run_engine, machine="worker-2")
    assert set(ssh_recorder.hosts) == {"10.0.0.2"}
    assert {r.machine_alias for r in _resultats(eid)} == {"worker-2"}


def test_deux_executions_du_meme_workflow_sont_independantes(admin, run_engine, ssh_recorder):
    admin.post("/api/v1/machines", json={"alias": "worker-2", "host": "10.0.0.2"})
    wid = make_workflow(admin, "wf", tasks=DEUX_TACHES, submit=True)
    e1 = admin.post(f"/api/v1/workflows/{wid}/execute").json()["id"]
    e2 = admin.post(f"/api/v1/workflows/{wid}/execute", json={"machine": "worker-2"}).json()["id"]
    run_engine()
    assert {r.machine_alias for r in _resultats(e1)} == {"worker-1"}
    assert {r.machine_alias for r in _resultats(e2)} == {"worker-2"}


def test_execution_deja_traitee_non_rejouee(admin, run_engine, ssh_recorder):
    _executer(admin, run_engine)
    appels = len(ssh_recorder.calls)
    run_engine()
    assert len(ssh_recorder.calls) == appels


def test_une_execution_en_echec_ne_bloque_pas_les_suivantes(admin, run_engine, ssh_recorder):
    """Un cycle traite plusieurs exécutions ; l'échec de l'une ne doit pas
    empêcher le traitement des autres."""
    wid_ko = make_workflow(admin, "ko", tasks=[
        {"name": "t", "command": "casse", "target": "worker-1"}], submit=True)
    wid_ok = make_workflow(admin, "ok", tasks=[
        {"name": "t", "command": "marche", "target": "worker-1"}], submit=True)

    def selectif(**kw):
        if kw["command"] == "casse":
            raise SSHInfrastructureError("panne")
        return SSHExecutionResult(return_code=0, stdout="ok", stderr="")

    ssh_recorder.handler = selectif
    e_ko = admin.post(f"/api/v1/workflows/{wid_ko}/execute").json()["id"]
    e_ok = admin.post(f"/api/v1/workflows/{wid_ok}/execute").json()["id"]
    run_engine()
    assert _execution(e_ko).status == "FAILED"
    assert _execution(e_ok).status == "DONE"


def test_sorties_capturees(admin, run_engine, ssh_recorder):
    ssh_recorder.handler = lambda **kw: SSHExecutionResult(
        return_code=3, stdout="sortie standard", stderr="sortie erreur"
    )
    _, eid = _executer(admin, run_engine, tasks=[
        {"name": "t", "command": "echo", "target": "worker-1"}])
    resultat = _resultats(eid)[0]
    assert resultat.stdout == "sortie standard"
    assert resultat.stderr == "sortie erreur"
    assert resultat.return_code == 3
