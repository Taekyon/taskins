"""Authentification, sessions et cloisonnement des rôles."""


def test_connexion_reussie_redirige(client):
    r = client.post("/login", data={"username": "admin", "password": "motdepasse-admin"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_mot_de_passe_invalide_refuse(client):
    r = client.post("/login", data={"username": "admin", "password": "faux"})
    assert r.status_code == 401


def test_utilisateur_inconnu_refuse(client):
    r = client.post("/login", data={"username": "personne", "password": "motdepasse1"})
    assert r.status_code == 401


def test_api_refuse_anonyme(client):
    assert client.get("/api/v1/workflows").status_code == 401


def test_web_redirige_anonyme(client):
    r = client.get("/workflows", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_deconnexion_invalide_la_session(admin):
    assert admin.get("/api/v1/workflows").status_code == 200
    admin.post("/logout")
    assert admin.get("/api/v1/workflows").status_code == 401


def test_standard_refuse_sur_endpoints_admin(user):
    assert user.get("/api/v1/users").status_code == 403
    assert user.post("/api/v1/machines", json={"alias": "x", "host": "1.2.3.4"}).status_code == 403


def test_page_admin_redirige_un_standard(user):
    r = user.get("/admin", follow_redirects=False)
    assert r.status_code == 303


def test_mot_de_passe_jamais_renvoye(admin):
    corps = admin.get("/api/v1/users").json()
    assert corps and all("password" not in c and "password_hash" not in c for c in corps)
