"""Planifications : différé, récurrence cron, absence de rattrapage."""

from datetime import timedelta

from conftest import make_workflow
from taskins.core import scheduling
from taskins.core.database import SessionLocal
from taskins.models.execution import Execution
from taskins.models.schedule import Schedule


def _decaler(schedule_id, secondes):
    """Place la prochaine occurrence dans le passé, sans attendre réellement."""
    db = SessionLocal()
    schedule = db.get(Schedule, schedule_id)
    schedule.next_run_at = scheduling.to_sql(scheduling.now_utc() - timedelta(seconds=secondes))
    db.commit()
    db.close()


def _executions(schedule_id):
    db = SessionLocal()
    try:
        return db.query(Execution).filter_by(schedule_id=schedule_id).count()
    finally:
        db.close()


def _schedule(schedule_id):
    db = SessionLocal()
    try:
        return db.get(Schedule, schedule_id)
    finally:
        db.close()


def _date_future(jours=1):
    futur = scheduling.now_utc() + timedelta(days=jours)
    return futur.astimezone(scheduling.local_tz()).strftime("%Y-%m-%dT%H:%M")


def test_cron_invalide_refuse(admin):
    wid = make_workflow(admin, "wf", submit=True)
    r = admin.post(f"/api/v1/workflows/{wid}/schedules",
                   json={"kind": "CRON", "cron_expression": "n'importe quoi"})
    assert r.status_code == 422


def test_date_passee_refusee(admin):
    wid = make_workflow(admin, "wf", submit=True)
    r = admin.post(f"/api/v1/workflows/{wid}/schedules",
                   json={"kind": "ONCE", "run_at": "2020-01-01T10:00"})
    assert r.status_code == 422 and "futur" in r.json()["detail"]


def test_workflow_non_soumis_non_planifiable(admin):
    wid = make_workflow(admin, "wf")
    r = admin.post(f"/api/v1/workflows/{wid}/schedules",
                   json={"kind": "CRON", "cron_expression": "0 2 * * *"})
    assert r.status_code == 422 and "approuvé" in r.json()["detail"]


def test_workflow_archive_non_planifiable(admin):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/archive")
    r = admin.post(f"/api/v1/workflows/{wid}/schedules",
                   json={"kind": "CRON", "cron_expression": "0 2 * * *"})
    assert r.status_code == 422 and "archivé" in r.json()["detail"]


def test_cron_calcule_en_heure_locale(admin):
    wid = make_workflow(admin, "wf", submit=True)
    r = admin.post(f"/api/v1/workflows/{wid}/schedules",
                   json={"kind": "CRON", "cron_expression": "0 2 * * *"})
    assert r.status_code == 201
    assert r.json()["next_run_at"].endswith("02:00:00"), "affiché en heure locale"


def test_cron_tient_compte_du_changement_d_heure():
    """'0 2 * * *' vaut 2 h locales toute l'année : 00 h UTC en été (UTC+2),
    01 h UTC en hiver (UTC+1)."""
    from datetime import datetime, timezone

    ete = scheduling.next_cron_occurrence("0 2 * * *", datetime(2026, 7, 22, 10, tzinfo=timezone.utc))
    hiver = scheduling.next_cron_occurrence("0 2 * * *", datetime(2026, 1, 15, 10, tzinfo=timezone.utc))
    assert ete.endswith("00:00:00")
    assert hiver.endswith("01:00:00")


def test_occurrence_echue_produit_une_execution(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    sid = admin.post(f"/api/v1/workflows/{wid}/schedules",
                     json={"kind": "CRON", "cron_expression": "0 2 * * *"}).json()["id"]
    _decaler(sid, 5)
    run_engine()
    assert _executions(sid) == 1
    schedule = _schedule(sid)
    assert schedule.last_run_at
    assert schedule.next_run_at > scheduling.now_sql(), "prochaine occurrence recalculée"


def test_machine_de_la_planification_heritee(admin, run_engine, ssh_recorder):
    admin.post("/api/v1/machines", json={"alias": "worker-2", "host": "10.0.0.2"})
    wid = make_workflow(admin, "wf", submit=True)
    sid = admin.post(f"/api/v1/workflows/{wid}/schedules",
                     json={"kind": "CRON", "cron_expression": "0 2 * * *",
                           "machine": "worker-2"}).json()["id"]
    _decaler(sid, 5)
    run_engine()
    assert ssh_recorder.hosts == ["10.0.0.2"]


def test_aucun_rattrapage_apres_un_arret(admin, run_engine):
    """Décision validée : une occurrence trop en retard est ignorée, la
    planification repart à la suivante."""
    wid = make_workflow(admin, "wf", submit=True)
    sid = admin.post(f"/api/v1/workflows/{wid}/schedules",
                     json={"kind": "CRON", "cron_expression": "0 2 * * *"}).json()["id"]
    _decaler(sid, 3 * 3600)
    run_engine()
    assert _executions(sid) == 0, "aucune exécution ne doit être rattrapée"
    schedule = _schedule(sid)
    assert schedule.next_run_at > scheduling.now_sql()
    assert schedule.is_active == 1


def test_ponctuelle_declenchee_une_seule_fois(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    sid = admin.post(f"/api/v1/workflows/{wid}/schedules",
                     json={"kind": "ONCE", "run_at": _date_future()}).json()["id"]
    _decaler(sid, 5)
    run_engine()
    assert _executions(sid) == 1
    schedule = _schedule(sid)
    assert schedule.is_active == 0 and schedule.next_run_at is None
    run_engine()
    assert _executions(sid) == 1, "aucun second déclenchement"


def test_reactivation_d_une_ponctuelle_deja_declenchee_refusee(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    sid = admin.post(f"/api/v1/workflows/{wid}/schedules",
                     json={"kind": "ONCE", "run_at": _date_future()}).json()["id"]
    _decaler(sid, 5)
    run_engine()
    assert admin.patch(f"/api/v1/schedules/{sid}", json={"is_active": True}).status_code == 409


def test_planification_inactive_non_declenchee(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    sid = admin.post(f"/api/v1/workflows/{wid}/schedules",
                     json={"kind": "CRON", "cron_expression": "0 2 * * *"}).json()["id"]
    admin.patch(f"/api/v1/schedules/{sid}", json={"is_active": False})
    _decaler(sid, 5)
    run_engine()
    assert _executions(sid) == 0


def test_suppression_preserve_l_historique_produit(admin, run_engine):
    """Supprimer une planification ne doit pas effacer les exécutions qu'elle a
    déclenchées : `schedule_id` passe simplement à NULL."""
    wid = make_workflow(admin, "wf", submit=True)
    sid = admin.post(f"/api/v1/workflows/{wid}/schedules",
                     json={"kind": "CRON", "cron_expression": "0 2 * * *"}).json()["id"]
    _decaler(sid, 5)
    run_engine()

    db = SessionLocal()
    eid = db.query(Execution).filter_by(schedule_id=sid).first().id
    total = db.query(Execution).count()
    db.close()

    assert admin.delete(f"/api/v1/schedules/{sid}").status_code == 204

    db = SessionLocal()
    execution = db.get(Execution, eid)
    assert execution is not None, "l'historique ne doit pas disparaître"
    assert execution.schedule_id is None
    assert db.query(Execution).count() == total
    db.close()


def test_suppression_du_workflow_supprime_ses_planifications(admin):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/schedules",
               json={"kind": "CRON", "cron_expression": "0 2 * * *"})
    admin.delete(f"/api/v1/workflows/{wid}")
    db = SessionLocal()
    assert db.query(Schedule).filter_by(workflow_id=wid).count() == 0
    db.close()


def test_standard_ne_peut_supprimer_la_planification_d_autrui(admin, app_client):
    wid = make_workflow(admin, "wf", submit=True)
    sid = admin.post(f"/api/v1/workflows/{wid}/schedules",
                     json={"kind": "CRON", "cron_expression": "0 2 * * *"}).json()["id"]
    admin.post("/api/v1/users", json={"username": "zoe", "password": "motdepasse1"})
    app_client.cookies.clear()
    app_client.post("/login", data={"username": "zoe", "password": "motdepasse1"}, follow_redirects=False)
    assert app_client.delete(f"/api/v1/schedules/{sid}").status_code == 403
