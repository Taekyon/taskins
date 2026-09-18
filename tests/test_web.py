"""Interface web : pages, fragments de rafraîchissement et accueil."""

from conftest import make_workflow


def test_accueil_agrege(admin):
    r = admin.get("/")
    assert r.status_code == 200 and "Vue d'ensemble" in r.text


def test_accueil_liste_brouillons_et_planifications(admin):
    make_workflow(admin, "mon-brouillon")
    wid = make_workflow(admin, "actif", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/schedules",
               json={"kind": "CRON", "cron_expression": "0 3 * * *"})
    r = admin.get("/")
    assert "mon-brouillon" in r.text and "0 3 * * *" in r.text


def test_accueil_signale_les_echecs(admin, run_engine, ssh_recorder):
    from taskins.core.ssh_client import SSHInfrastructureError

    def panne(**kw):
        raise SSHInfrastructureError("injoignable")

    ssh_recorder.handler = panne
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/execute")
    run_engine()
    r = admin.get("/")
    assert "Échecs récents" in r.text and "tile-alert" in r.text


def test_liste_des_workflows(admin):
    make_workflow(admin, "visible")
    assert "visible" in admin.get("/workflows").text


def test_bascule_des_archives(admin):
    wid = make_workflow(admin, "cache", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/archive")
    assert "cache" not in admin.get("/workflows").text
    assert "cache" in admin.get("/workflows?archived=1").text


def test_formulaire_de_creation(admin):
    r = admin.get("/workflows/new")
    assert r.status_code == 200 and "worker-1" in r.text


def test_route_new_non_capturee_par_l_identifiant(admin):
    """/workflows/new est déclarée avant /workflows/{id} : sans cela, FastAPI
    tenterait de convertir 'new' en entier."""
    assert admin.get("/workflows/new").status_code == 200


def test_page_de_detail(admin):
    wid = make_workflow(admin, "wf")
    r = admin.get(f"/workflows/{wid}")
    assert r.status_code == 200 and "echo bonjour" in r.text


def test_boutons_conditionnes_au_statut(admin):
    wid = make_workflow(admin, "wf")
    brouillon = admin.get(f"/workflows/{wid}").text
    assert 'id="submit-btn"' in brouillon and 'id="execute-btn"' not in brouillon

    admin.post(f"/api/v1/workflows/{wid}/submit")
    approuve = admin.get(f"/workflows/{wid}").text
    assert 'id="execute-btn"' in approuve and 'id="submit-btn"' not in approuve


def test_page_d_execution_affiche_l_instantane(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    eid = admin.post(f"/api/v1/workflows/{wid}/execute").json()["id"]
    run_engine()
    r = admin.get(f"/workflows/{wid}/executions/{eid}")
    assert r.status_code == 200 and "echo bonjour" in r.text and "worker-1" in r.text


def test_execution_d_un_autre_workflow_introuvable(admin):
    wid_a = make_workflow(admin, "a", submit=True)
    wid_b = make_workflow(admin, "b", submit=True)
    eid = admin.post(f"/api/v1/workflows/{wid_a}/execute").json()["id"]
    assert admin.get(f"/workflows/{wid_b}/executions/{eid}").status_code == 404


def test_fragment_executions(admin):
    wid = make_workflow(admin, "wf", submit=True)
    r = admin.get(f"/workflows/{wid}/fragments/executions")
    assert r.status_code == 200
    assert r.text.strip().startswith("<tbody") and 'id="executions-body"' in r.text


def test_interrogation_active_tant_qu_une_execution_est_en_cours(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/execute")
    assert 'data-poll="true"' in admin.get(f"/workflows/{wid}/fragments/executions").text
    run_engine()
    assert 'data-poll="false"' in admin.get(f"/workflows/{wid}/fragments/executions").text


def test_interrogation_active_par_une_planification(admin):
    """Sans cela, une exécution déclenchée par le cron n'apparaîtrait jamais
    sans rechargement manuel de la page."""
    wid = make_workflow(admin, "wf", submit=True)
    assert 'data-poll="false"' in admin.get(f"/workflows/{wid}/fragments/executions").text
    admin.post(f"/api/v1/workflows/{wid}/schedules",
               json={"kind": "CRON", "cron_expression": "0 2 * * *"})
    assert 'data-poll="true"' in admin.get(f"/workflows/{wid}/fragments/executions").text


def test_fragment_resultats(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    eid = admin.post(f"/api/v1/workflows/{wid}/execute").json()["id"]
    avant = admin.get(f"/workflows/{wid}/executions/{eid}/fragments/results").text
    assert 'data-poll="true"' in avant and "En attente de traitement" in avant
    run_engine()
    apres = admin.get(f"/workflows/{wid}/executions/{eid}/fragments/results").text
    assert 'data-poll="false"' in apres and 'data-status="DONE"' in apres


def test_plus_de_rechargement_periodique_complet(admin):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/execute")
    page = admin.get(f"/workflows/{wid}").text
    assert "setInterval(() => location.reload" not in page
    assert "refreshExecutions" in page


def test_fragments_proteges(client):
    assert client.get("/workflows/1/fragments/executions", follow_redirects=False).status_code == 303


def test_fragments_sur_objets_inexistants(admin):
    assert admin.get("/workflows/9999/fragments/executions").status_code == 404


def test_page_admin(admin):
    r = admin.get("/admin")
    assert r.status_code == 200
    assert "Administration" in r.text and "worker-1" in r.text and "all" in r.text


def test_lien_admin_masque_pour_un_standard(user):
    assert "Administration" not in user.get("/workflows").text


# ---------------------------------------------------------------------------
# Non-régression : le rafraîchissement ne démarrait jamais
#
# La page complète et la route de fragment rendent le MÊME gabarit, qui attend
# une variable `poll`. Elle n'était passée que par la route de fragment : au
# chargement de la page, Jinja évaluait la variable absente comme fausse — sans
# erreur — et le JS, qui lit l'attribut une seule fois, n'armait jamais son
# intervalle. Les tests d'origine interrogeaient le fragment isolément et ne
# voyaient donc rien.
# ---------------------------------------------------------------------------


def test_page_complete_arme_l_interrogation_si_execution_en_cours(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/execute")
    assert 'data-poll="true"' in admin.get(f"/workflows/{wid}").text
    run_engine()
    assert 'data-poll="false"' in admin.get(f"/workflows/{wid}").text


def test_page_complete_arme_l_interrogation_si_planification_active(admin):
    wid = make_workflow(admin, "wf", submit=True)
    assert 'data-poll="false"' in admin.get(f"/workflows/{wid}").text
    admin.post(f"/api/v1/workflows/{wid}/schedules",
               json={"kind": "CRON", "cron_expression": "0 2 * * *"})
    assert 'data-poll="true"' in admin.get(f"/workflows/{wid}").text


def test_page_complete_et_fragment_donnent_le_meme_etat(admin, run_engine):
    """Deux routes rendent le même gabarit : elles doivent s'accorder."""
    import re

    def etat(html):
        trouve = re.search(r'id="executions-body" data-poll="(\w+)"', html)
        assert trouve, "attribut data-poll introuvable"
        return trouve.group(1)

    wid = make_workflow(admin, "wf", submit=True)

    # État inactif : les deux doivent dire "false".
    assert etat(admin.get(f"/workflows/{wid}").text) == "false"
    assert etat(admin.get(f"/workflows/{wid}/fragments/executions").text) == "false"

    # Exécution en attente : les deux doivent dire "true". C'est ce cas-là que
    # le bug d'origine cassait, uniquement du côté de la page complète.
    admin.post(f"/api/v1/workflows/{wid}/execute")
    page = etat(admin.get(f"/workflows/{wid}").text)
    fragment = etat(admin.get(f"/workflows/{wid}/fragments/executions").text)
    assert page == fragment == "true", f"page={page} fragment={fragment}"

    # Une fois traitée : retour à "false" des deux côtés.
    run_engine()
    assert etat(admin.get(f"/workflows/{wid}").text) == "false"
    assert etat(admin.get(f"/workflows/{wid}/fragments/executions").text) == "false"


def test_page_d_execution_arme_l_interrogation(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    eid = admin.post(f"/api/v1/workflows/{wid}/execute").json()["id"]
    assert 'data-poll="true"' in admin.get(f"/workflows/{wid}/executions/{eid}").text
    run_engine()
    assert 'data-poll="false"' in admin.get(f"/workflows/{wid}/executions/{eid}").text


# ---------------------------------------------------------------------------
# Rafraîchissement de la vue d'ensemble — absent de la livraison initiale
# ---------------------------------------------------------------------------


def test_accueil_arme_l_interrogation(admin, run_engine):
    wid = make_workflow(admin, "wf", submit=True)
    assert 'data-poll="false"' in admin.get("/").text
    admin.post(f"/api/v1/workflows/{wid}/execute")
    assert 'data-poll="true"' in admin.get("/").text
    run_engine()
    assert 'data-poll="false"' in admin.get("/").text


def test_accueil_interroge_si_planification_active(admin):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/schedules",
               json={"kind": "CRON", "cron_expression": "0 2 * * *"})
    assert 'data-poll="true"' in admin.get("/").text


def test_fragment_accueil(admin):
    make_workflow(admin, "visible")
    r = admin.get("/fragments/home")
    assert r.status_code == 200
    assert r.text.strip().startswith("<div") and 'id="home-body"' in r.text
    assert "visible" in r.text and "tile-value" in r.text


def test_fragment_accueil_et_page_donnent_le_meme_etat(admin):
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/execute")
    assert 'data-poll="true"' in admin.get("/").text
    assert 'data-poll="true"' in admin.get("/fragments/home").text


def test_fragment_accueil_protege(client):
    assert client.get("/fragments/home", follow_redirects=False).status_code == 303


def test_nouvelle_execution_planifiee_apparait_dans_le_fragment(admin, run_engine):
    """Une occurrence de cron doit apparaître au rafraîchissement suivant, sans
    rechargement manuel : le fragment relit la base à chaque appel."""
    from datetime import timedelta

    from taskins.core import scheduling
    from taskins.core.database import SessionLocal
    from taskins.models.schedule import Schedule

    wid = make_workflow(admin, "wf", submit=True)
    sid = admin.post(f"/api/v1/workflows/{wid}/schedules",
                     json={"kind": "CRON", "cron_expression": "0 2 * * *"}).json()["id"]

    avant = admin.get(f"/workflows/{wid}/fragments/executions").text
    assert "#1" not in avant

    db = SessionLocal()
    schedule = db.get(Schedule, sid)
    schedule.next_run_at = scheduling.to_sql(scheduling.now_utc() - timedelta(seconds=5))
    db.commit()
    db.close()
    run_engine()

    apres = admin.get(f"/workflows/{wid}/fragments/executions").text
    assert "#1" in apres and "planifiée" in apres
