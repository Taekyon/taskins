# Guide du contributeur

Comment mettre en place un environnement de développement, ajouter une
fonctionnalité et vérifier qu'on n'a rien cassé. Le fonctionnement technique est
décrit dans [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Environnement de développement

```bash
cp .env.example .env.dev
# renseigner au minimum TASKINS_SECRET_KEY et TASKINS_SEED_MACHINE_HOST
# derrière un proxy, renseigner aussi HTTP_PROXY / HTTPS_PROXY / NO_PROXY

docker compose -f docker-compose.dev.yml --env-file .env.dev build
docker compose -f docker-compose.dev.yml --env-file .env.dev up
```

Différences avec la production, toutes délibérées :

| | Développement | Production |
|---|---|---|
| Volume de base | `taskins-db-dev` | `taskins-db-prod` |
| Code | monté depuis le disque (`.:/app`) | figé dans l'image au build |
| Rechargement | `--reload` actif | inactif |
| Dépendances de test | installées (`INSTALL_DEV=true`) | absentes |
| Port | 8000 | 80 |

La séparation des volumes est la protection la plus importante : réinitialiser
la base de développement — opération courante lors d'un changement de schéma —
ne peut jamais atteindre les données de production.

**Réinitialiser la base de développement :**

```bash
docker compose -f docker-compose.dev.yml down
docker volume rm taskins-db-dev
docker compose -f docker-compose.dev.yml --env-file .env.dev up
```

---

## Tests

```bash
docker compose -f docker-compose.dev.yml exec taskins pytest
docker compose -f docker-compose.dev.yml exec taskins pytest tests/test_engine.py
docker compose -f docker-compose.dev.yml exec taskins pytest -k timeout
```

**Aucune connexion SSH réelle n'est requise.** `execute_command` est remplacé
par un enregistreur (`SSHRecorder` dans `conftest.py`) que chaque test
paramètre. La logique interne du client SSH — boucle de timeout, purge des
tampons — est testée séparément dans `test_ssh_client.py`, contre un faux canal
paramiko.

**La boucle du moteur est neutralisée** (`TASKINS_SCHEDULER_INTERVAL` à 24 h) :
les tests déclenchent un cycle explicitement via la fixture `run_engine`. Aucun
test ne dépend d'un `sleep` ni du temps qui passe.

**La base est recréée avant chaque test.** Aucun test ne dépend de l'ordre
d'exécution. C'est ce qui explique la durée totale (~90 s), essentiellement du
bcrypt. Ce coût est assumé : l'isolation vaut mieux que la vitesse sur une suite
lancée occasionnellement.

### Écrire un test

Les fixtures disponibles :

| Fixture | Rôle |
|---|---|
| `client` | Client HTTP anonyme |
| `admin` | Client authentifié comme administrateur |
| `user` | Client authentifié comme utilisateur standard |
| `run_engine` | Déclenche un cycle du moteur, de façon synchrone |
| `ssh_recorder` | Accès aux appels SSH simulés (`.calls`, `.commands`, `.hosts`) et au comportement (`.handler`) |

Le raccourci `make_workflow(client, nom, tasks=..., submit=True)` évite de
répéter la création d'un workflow.

```python
def test_exemple(admin, run_engine, ssh_recorder):
    ssh_recorder.handler = lambda **kw: SSHExecutionResult(
        return_code=1, stdout="", stderr=""
    )
    wid = make_workflow(admin, "wf", submit=True)
    admin.post(f"/api/v1/workflows/{wid}/execute")
    run_engine()
    assert ssh_recorder.commands == ["echo bonjour"]
```

### Vérifier qu'un test a des dents

Un test qui passe quoi qu'il arrive ne protège de rien. Après avoir écrit un
test, **casser volontairement la règle qu'il vérifie** et confirmer qu'il
échoue. Exemple : neutraliser l'évaluation des conditions dans `core/engine.py`
doit faire échouer `test_condition_non_satisfaite_arrete_l_execution`.

Cette vérification n'est pas théorique. Un défaut réel a franchi 108 tests pour
n'apparaître qu'en production : les tests interrogeaient une route de fragment
isolément, jamais la page complète qui rend le même gabarit.

---

## Ajouter une fonctionnalité

L'ordre suivant limite les allers-retours. Chaque étape ne dépend que des
précédentes.

**1. Le modèle** (`models/`) — si la fonctionnalité stocke quelque chose.
Ajouter les colonnes ou la table.

**2. La migration** (`migrations/`) — obligatoire dès qu'une colonne est
ajoutée. `create_all()` de SQLAlchemy crée les tables manquantes mais **n'ajoute
jamais de colonne** à une table existante : sans script, la modification ne
s'appliquera à aucune base déjà déployée. Numérotation continue, un fichier par
changement :

```sql
-- migrations/004-description-courte.sql
-- Alternative au reset de volume, pour conserver une base existante.
ALTER TABLE workflows ADD COLUMN nouvelle_colonne TEXT;
```

**3. Le schéma** (`schemas/`) — validation de l'entrée et forme de la sortie.

**4. Le service** (`services/`) — la règle métier. Lever une exception dédiée
(`WorkflowValidationError`, `UserValidationError`…) plutôt que de renvoyer un
code HTTP : le service ne connaît pas HTTP.

**5. La route** (`routes/api/` ou `routes/web/`) — valider, appeler le service,
traduire l'exception en code HTTP.

**6. Le gabarit** (`templates/`) — si l'interface web est concernée.

**7. Le test** — au minimum le cas nominal et un cas d'erreur.

---

## Conventions

**Aucune logique métier dans `routes/`.** Une route valide l'entrée, appelle un
service, formate la sortie. Si une condition métier apparaît dans un fichier de
`routes/`, elle est au mauvais endroit.

**Un service par domaine**, nommé `<domaine>_service.py`. Les services ne
s'appellent entre eux que dans un sens clair (`workflow_service` peut appeler
`machine_service`, l'inverse serait un signal d'alerte).

**Une exception par domaine**, levée par le service, traduite par la route :

| Situation | Code HTTP |
|---|---|
| Donnée invalide, référence inconnue | 422 |
| Transition d'état impossible, conflit | 409 |
| Objet inexistant | 404 |
| Non authentifié (API) | 401 |
| Authentifié mais non autorisé | 403 |
| Non authentifié (web) | 303 vers `/login` |

**Routes littérales avant routes paramétrées.** `/workflows/new` doit être
déclarée avant `/workflows/{workflow_id}`, sinon FastAPI tente de convertir
`"new"` en entier. Même chose pour `/users/me/password` avant `/users/{id}`.

**Un seul calcul par état partagé.** Quand une page complète et une route de
fragment rendent le même gabarit, l'état qu'il consomme est calculé par une
fonction unique appelée par les deux.

**Commentaires** — expliquer *pourquoi*, pas *quoi*. Un commentaire qui
paraphrase le code est du bruit ; un commentaire qui explique une contrainte non
évidente (« sans cette purge, le processus distant bloque en écriture ») est ce
qui évite qu'on défasse la correction six mois plus tard.

---

## Pièges d'environnement

Tous rencontrés en conditions réelles.

| Piège | Détail |
|---|---|
| **Proxy d'entreprise** | Deux effets distincts. Construction d'image : renseigner `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` dans le fichier passé à `--env-file`. Requêtes locales : `curl` respecte les variables de proxy du shell, y compris vers `localhost` — ajouter `--noproxy '*'`. |
| **`create_all()` ne migre pas** | N'ajoute jamais de colonne à une table existante. Voir [Ajouter une fonctionnalité](#ajouter-une-fonctionnalité). |
| **`bcrypt==4.0.1`** | Pin obligatoire : `passlib` 1.7.4 est incompatible avec `bcrypt >= 4.1`. |
| **`pytest` ≠ `python -m pytest`** | La seconde forme ajoute le répertoire courant à `sys.path`, la première non. `pythonpath = .` dans `pytest.ini` rend les deux équivalentes. |
| **`__pycache__` périmé** | Un traceback citant un fichier qui n'existe plus, avec `???` au lieu du code, en est la signature. Le bind mount `.:/app` expose le cache de l'hôte au conteneur : `find . -name __pycache__ -type d -exec rm -rf {} +` |
| **`TestClient` suit les redirections** | Un `POST /login` renvoie 200 (page finale) et non 303. Utiliser `follow_redirects=False` pour vérifier un statut de redirection. |
| **Fixtures `admin` et `user`** | Elles partagent un client de scope session : les demander toutes deux dans un test ne donne pas deux sessions simultanées, seule la dernière connexion est active. Pour tester deux rôles, se reconnecter explicitement via `app_client`. |
| **Variable Jinja absente = fausse** | Aucune erreur levée. Un gabarit qui attend une variable non transmise se rend silencieusement avec la valeur fausse. |
| **`TemplateResponse`** | Signature récente : `(request, "page.html", contexte)`. L'ancien style `("page.html", {"request": ...})` est cassé. |
| **Shell du compte de service** | `svc-taskins` doit avoir un shell valide sur les machines cibles. Avec `/usr/sbin/nologin`, SSH s'authentifie mais toute commande retourne « This account is currently not available. », code 1, en moins d'une seconde — symptôme trompeur, sans rapport apparent avec la cause. |

---

## Contribuer avec l'assistance d'une IA

Le projet a été développé de cette façon. Ce qui a fonctionné :

**Décider soi-même de la conception.** Les arbitrages structurants — modèle de
données, stratégie d'exécution, format d'échange — se posent en amont et se
tiennent. Une IA propose volontiers une solution plausible qui ne tient pas
compte d'une contrainte non exprimée.

**Relire et comprendre le code produit** avant de l'intégrer, plutôt que de
l'accepter parce qu'il fonctionne.

**Faire signaler les écarts.** Demander explicitement que toute divergence entre
le code produit et ce qui était prévu soit annoncée et justifiée.

**Fournir le contexte à chaque session.** Aucun modèle ne conserve l'historique
d'un projet d'une conversation à l'autre. [ARCHITECTURE.md](ARCHITECTURE.md),
ce fichier et la suite de tests sont ce qui permet de reprendre le travail sans
disposer des échanges qui ont produit le code.

**Se méfier de ce que l'IA ne peut pas vérifier.** Elle n'exécute ni JavaScript
dans un navigateur, ni connexion SSH réelle. Tout ce qui touche au comportement
côté client ou à l'infrastructure demande une vérification humaine sur
l'environnement réel — c'est précisément là que ce projet a rencontré ses seuls
vrais défauts.
