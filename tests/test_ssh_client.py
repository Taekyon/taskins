"""Client SSH : boucle de timeout et purge des tampons.

Testé contre un faux canal paramiko — aucun serveur SSH n'est requis. C'est la
partie qui ne pouvait pas être validée par les tests d'API, puisque le moteur
utilise un `execute_command` simulé.
"""

import time

import pytest

import taskins.core.ssh_client as ssh_client
from taskins.core.ssh_client import SSHInfrastructureError, SSHTimeoutError, execute_command


class FauxCanal:
    def __init__(self, pret_apres=0.0, sortie=b"", erreur=b"", code=0):
        self.debut = time.monotonic()
        self.pret_apres = pret_apres
        self.sortie, self.erreur, self.code = sortie, erreur, code
        self.ferme = False

    def settimeout(self, _):
        pass

    def exec_command(self, commande):
        self.commande = commande

    def recv_ready(self):
        return bool(self.sortie)

    def recv_stderr_ready(self):
        return bool(self.erreur)

    def recv(self, n):
        bloc, self.sortie = self.sortie[:n], self.sortie[n:]
        return bloc

    def recv_stderr(self, n):
        bloc, self.erreur = self.erreur[:n], self.erreur[n:]
        return bloc

    def exit_status_ready(self):
        return time.monotonic() - self.debut >= self.pret_apres

    def recv_exit_status(self):
        return self.code

    def close(self):
        self.ferme = True


class FauxClient:
    canal = None
    echec_connexion = False

    def set_missing_host_key_policy(self, _):
        pass

    def connect(self, **kwargs):
        if FauxClient.echec_connexion:
            raise OSError("hôte injoignable")

    def get_transport(self):
        canal = FauxClient.canal
        return type("T", (), {"open_session": lambda self: canal})()

    def close(self):
        pass


@pytest.fixture(autouse=True)
def paramiko_simule(monkeypatch):
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", FauxClient)
    monkeypatch.setattr(ssh_client.paramiko, "AutoAddPolicy", lambda: None)
    FauxClient.echec_connexion = False
    yield


def _executer(canal, timeout=5):
    FauxClient.canal = canal
    return execute_command("h", 22, "u", "/cle", "commande", timeout_seconds=timeout)


def test_commande_rapide():
    canal = FauxCanal(sortie=b"bonjour", erreur=b"attention", code=7)
    resultat = _executer(canal)
    assert resultat.return_code == 7
    assert resultat.stdout == "bonjour" and resultat.stderr == "attention"
    assert canal.ferme


def test_timeout_declenche_dans_le_delai():
    canal = FauxCanal(pret_apres=60)
    debut = time.monotonic()
    with pytest.raises(SSHTimeoutError, match="1s"):
        _executer(canal, timeout=1)
    ecoule = time.monotonic() - debut
    assert 0.9 < ecoule < 3, f"timeout déclenché en {ecoule:.2f}s"
    assert canal.ferme, "le canal doit être fermé même en cas de timeout"


def test_timeout_est_un_echec_d_infrastructure():
    """Le moteur n'intercepte que SSHInfrastructureError : sans cet héritage,
    un timeout remonterait comme exception non gérée."""
    assert issubclass(SSHTimeoutError, SSHInfrastructureError)


def test_commande_lente_mais_dans_le_delai():
    resultat = _executer(FauxCanal(pret_apres=0.5, sortie=b"lent"), timeout=5)
    assert resultat.return_code == 0 and resultat.stdout == "lent"


def test_sortie_volumineuse_drainee_sans_interblocage():
    """Sans purge des tampons pendant l'attente, le processus distant bloque en
    écriture et la commande ne se termine jamais."""
    resultat = _executer(FauxCanal(pret_apres=0.3, sortie=b"x" * 500_000), timeout=5)
    assert len(resultat.stdout) == 500_000


def test_echec_de_connexion_non_classe_en_timeout():
    FauxClient.echec_connexion = True
    with pytest.raises(SSHInfrastructureError, match="Connexion SSH impossible"):
        _executer(FauxCanal(), timeout=5)


def test_sortie_binaire_non_decodable_toleree():
    resultat = _executer(FauxCanal(sortie=b"\xff\xfe invalide"), timeout=5)
    assert "invalide" in resultat.stdout
