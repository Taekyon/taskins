"""Machines cibles : création, modification, suppression et gardes."""

from conftest import make_workflow


def test_machine_du_seed_presente(admin):
    alias = [m["alias"] for m in admin.get("/api/v1/machines").json()]
    assert "worker-1" in alias


def test_creation(admin):
    r = admin.post("/api/v1/machines", json={"alias": "worker-2", "host": "10.0.0.2"})
    assert r.status_code == 201
    assert r.json()["ssh_user"] == "svc-taskins" and r.json()["ssh_port"] == 22


def test_alias_duplique_refuse(admin):
    admin.post("/api/v1/machines", json={"alias": "dup", "host": "10.0.0.3"})
    r = admin.post("/api/v1/machines", json={"alias": "dup", "host": "10.0.0.4"})
    assert r.status_code == 409


def test_modification_partielle(admin):
    mid = admin.post("/api/v1/machines", json={"alias": "m", "host": "10.0.0.5"}).json()["id"]
    r = admin.patch(f"/api/v1/machines/{mid}", json={"host": "10.0.0.99"})
    assert r.status_code == 200
    assert r.json()["host"] == "10.0.0.99"
    assert r.json()["alias"] == "m", "un champ non fourni ne doit pas être écrasé"


def test_modification_possible_meme_si_referencee(admin):
    """Sans cela, un changement d'adresse IP rendrait un workflow inutilisable :
    la machine ne pourrait être ni modifiée, ni supprimée."""
    make_workflow(admin, "wf")
    mid = [m["id"] for m in admin.get("/api/v1/machines").json() if m["alias"] == "worker-1"][0]
    assert admin.delete(f"/api/v1/machines/{mid}").status_code == 409
    r = admin.patch(f"/api/v1/machines/{mid}", json={"host": "192.168.50.50"})
    assert r.status_code == 200 and r.json()["host"] == "192.168.50.50"


def test_modification_vers_alias_existant_refusee(admin):
    admin.post("/api/v1/machines", json={"alias": "a", "host": "10.0.0.6"})
    bid = admin.post("/api/v1/machines", json={"alias": "b", "host": "10.0.0.7"}).json()["id"]
    assert admin.patch(f"/api/v1/machines/{bid}", json={"alias": "a"}).status_code == 409


def test_port_invalide_refuse(admin):
    mid = admin.post("/api/v1/machines", json={"alias": "p", "host": "10.0.0.8"}).json()["id"]
    assert admin.patch(f"/api/v1/machines/{mid}", json={"ssh_port": 0}).status_code == 422
    assert admin.patch(f"/api/v1/machines/{mid}", json={"ssh_port": 99999}).status_code == 422


def test_suppression_non_referencee(admin):
    mid = admin.post("/api/v1/machines", json={"alias": "jetable", "host": "10.0.0.9"}).json()["id"]
    assert admin.delete(f"/api/v1/machines/{mid}").status_code == 204
    assert "jetable" not in [m["alias"] for m in admin.get("/api/v1/machines").json()]


def test_suppression_referencee_refusee(admin):
    make_workflow(admin, "wf")
    mid = [m["id"] for m in admin.get("/api/v1/machines").json() if m["alias"] == "worker-1"][0]
    r = admin.delete(f"/api/v1/machines/{mid}")
    assert r.status_code == 409 and "référencée" in r.json()["detail"]


def test_machine_inexistante(admin):
    assert admin.patch("/api/v1/machines/9999", json={"host": "x"}).status_code == 404
    assert admin.delete("/api/v1/machines/9999").status_code == 404
