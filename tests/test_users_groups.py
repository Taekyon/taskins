"""Utilisateurs, rôles et groupes."""

from conftest import make_workflow


def test_creation_utilisateur(admin):
    r = admin.post("/api/v1/users", json={"username": "alice", "password": "motdepasse1"})
    assert r.status_code == 201 and r.json()["is_admin"] is False


def test_mot_de_passe_trop_court_refuse(admin):
    assert admin.post("/api/v1/users", json={"username": "b", "password": "court"}).status_code == 422


def test_nom_duplique_refuse(admin):
    admin.post("/api/v1/users", json={"username": "carl", "password": "motdepasse1"})
    assert admin.post("/api/v1/users", json={"username": "carl", "password": "motdepasse2"}).status_code == 409


def test_attribution_et_retrait_du_role_admin(admin):
    uid = admin.post("/api/v1/users", json={"username": "dana", "password": "motdepasse1"}).json()["id"]
    assert admin.patch(f"/api/v1/users/{uid}", json={"is_admin": True}).json()["is_admin"] is True
    assert admin.patch(f"/api/v1/users/{uid}", json={"is_admin": False}).json()["is_admin"] is False


def test_suppression_simple(admin):
    uid = admin.post("/api/v1/users", json={"username": "eric", "password": "motdepasse1"}).json()["id"]
    assert admin.delete(f"/api/v1/users/{uid}").status_code == 204


def test_auto_suppression_refusee(admin):
    aid = [u["id"] for u in admin.get("/api/v1/users").json() if u["username"] == "admin"][0]
    r = admin.delete(f"/api/v1/users/{aid}")
    assert r.status_code == 409 and "propre compte" in r.json()["detail"]


def test_suppression_refusee_si_proprietaire_de_workflows(admin, app_client):
    uid = admin.post("/api/v1/users", json={"username": "fred", "password": "motdepasse1"}).json()["id"]
    app_client.cookies.clear()
    app_client.post("/login", data={"username": "fred", "password": "motdepasse1"}, follow_redirects=False)
    make_workflow(app_client, "wf-de-fred")
    app_client.cookies.clear()
    app_client.post("/login", data={"username": "admin", "password": "motdepasse-admin"}, follow_redirects=False)
    r = app_client.delete(f"/api/v1/users/{uid}")
    assert r.status_code == 409 and "workflow" in r.json()["detail"]


def test_garde_dernier_administrateur():
    """Vérifiée au niveau du service : elle est inatteignable par l'API, car
    supprimer le dernier administrateur suppose d'être cet administrateur, et
    l'auto-suppression est bloquée en amont."""
    import pytest

    from taskins.core.database import SessionLocal
    from taskins.models.user import User
    from taskins.services.user_service import UserValidationError, create_user, delete_user
    from taskins.schemas.user import UserCreate

    db = SessionLocal()
    autre = create_user(db, UserCreate(username="temoin", password="motdepasse1"))
    seul_admin = db.query(User).filter_by(username="admin").first()
    assert db.query(User).filter(User.is_admin == 1).count() == 1

    with pytest.raises(UserValidationError, match="dernier administrateur"):
        delete_user(db, seul_admin, current_user=autre)
    db.rollback()
    db.close()


def test_groupe_par_defaut_present(admin):
    assert "all" in [g["name"] for g in admin.get("/api/v1/groups").json()]


def test_creation_et_suppression_groupe(admin):
    gid = admin.post("/api/v1/groups", json={"name": "ops"}).json()["id"]
    assert admin.post("/api/v1/groups", json={"name": "ops"}).status_code == 409
    assert admin.delete(f"/api/v1/groups/{gid}").status_code == 204


def test_groupe_all_protege(admin):
    gid = [g["id"] for g in admin.get("/api/v1/groups").json() if g["name"] == "all"][0]
    r = admin.delete(f"/api/v1/groups/{gid}")
    assert r.status_code == 409 and "structurant" in r.json()["detail"]


def test_groupe_non_vide_protege(admin):
    make_workflow(admin, "wf")
    gid = [g["id"] for g in admin.get("/api/v1/groups").json() if g["name"] == "all"][0]
    assert admin.delete(f"/api/v1/groups/{gid}").status_code == 409


# ---------------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------------


def test_changement_de_son_propre_mot_de_passe(admin, app_client):
    r = admin.post("/api/v1/users/me/password",
                   json={"current_password": "motdepasse-admin", "new_password": "nouveau-mdp-1"})
    assert r.status_code == 204

    app_client.cookies.clear()
    ancien = app_client.post("/login", data={"username": "admin", "password": "motdepasse-admin"})
    assert ancien.status_code == 401, "l'ancien mot de passe ne doit plus fonctionner"

    nouveau = app_client.post("/login",
                              data={"username": "admin", "password": "nouveau-mdp-1"},
                              follow_redirects=False)
    assert nouveau.status_code == 303


def test_mot_de_passe_actuel_errone_refuse(admin):
    r = admin.post("/api/v1/users/me/password",
                   json={"current_password": "faux", "new_password": "nouveau-mdp-1"})
    assert r.status_code == 422 and "incorrect" in r.json()["detail"]


def test_nouveau_mot_de_passe_identique_refuse(admin):
    r = admin.post("/api/v1/users/me/password",
                   json={"current_password": "motdepasse-admin", "new_password": "motdepasse-admin"})
    assert r.status_code == 422


def test_nouveau_mot_de_passe_trop_court_refuse(admin):
    r = admin.post("/api/v1/users/me/password",
                   json={"current_password": "motdepasse-admin", "new_password": "court"})
    assert r.status_code == 422


def test_changement_de_mot_de_passe_refuse_aux_anonymes(client):
    r = client.post("/api/v1/users/me/password",
                    json={"current_password": "x", "new_password": "motdepasse1"})
    assert r.status_code == 401


def test_route_me_non_capturee_par_l_identifiant(admin):
    """/me/password est déclarée avant /{user_id} : sans cela, FastAPI
    tenterait de convertir 'me' en entier."""
    r = admin.post("/api/v1/users/me/password",
                   json={"current_password": "motdepasse-admin", "new_password": "nouveau-mdp-1"})
    assert r.status_code == 204, "la route ne doit pas être interceptée par /{user_id}"


def test_un_standard_peut_changer_son_mot_de_passe(user):
    r = user.post("/api/v1/users/me/password",
                  json={"current_password": "motdepasse1", "new_password": "nouveau-mdp-1"})
    assert r.status_code == 204


def test_reinitialisation_par_un_administrateur(admin, app_client):
    """Seul recours pour un utilisateur ayant oublié son mot de passe."""
    uid = admin.post("/api/v1/users",
                     json={"username": "oublieux", "password": "motdepasse1"}).json()["id"]
    assert admin.patch(f"/api/v1/users/{uid}", json={"password": "remis-a-zero-1"}).status_code == 200

    app_client.cookies.clear()
    r = app_client.post("/login",
                        data={"username": "oublieux", "password": "remis-a-zero-1"},
                        follow_redirects=False)
    assert r.status_code == 303


def test_patch_admin_seul_sans_toucher_au_mot_de_passe(admin, app_client):
    uid = admin.post("/api/v1/users",
                     json={"username": "promu", "password": "motdepasse1"}).json()["id"]
    assert admin.patch(f"/api/v1/users/{uid}", json={"is_admin": True}).json()["is_admin"] is True

    app_client.cookies.clear()
    r = app_client.post("/login",
                        data={"username": "promu", "password": "motdepasse1"},
                        follow_redirects=False)
    assert r.status_code == 303, "le mot de passe ne doit pas avoir changé"


def test_reinitialisation_refusee_a_un_standard(admin, app_client):
    """Ne pas demander les fixtures `admin` et `user` dans le même test : elles
    partagent un client de scope session, seule la dernière connexion est
    active."""
    cible = admin.post("/api/v1/users",
                       json={"username": "cible", "password": "motdepasse1"}).json()["id"]
    admin.post("/api/v1/users", json={"username": "curieux", "password": "motdepasse1"})

    app_client.cookies.clear()
    app_client.post("/login",
                    data={"username": "curieux", "password": "motdepasse1"},
                    follow_redirects=False)
    r = app_client.patch(f"/api/v1/users/{cible}", json={"password": "tentative-1"})
    assert r.status_code == 403


def test_page_mon_compte(admin):
    r = admin.get("/account")
    assert r.status_code == 200 and "Changer mon mot de passe" in r.text


def test_page_mon_compte_protegee(client):
    assert client.get("/account", follow_redirects=False).status_code == 303
