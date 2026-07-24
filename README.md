# taskins
Taskins est un ordonnanceur simple permettant d'exécuter des workflows (jobs) sur plusieurs machines, avec exécution à distance via SSH, planification et supervision web.

## But
Le but de ce projet est de se former sur le développement d'outils simples, répondant à un besoin spécifique au sein d'une PME.

- **Documentation d'architecture et de décisions** : `docs/`
- **Suite de tests** : `tests/README.md`

---

## Prérequis

- Docker et Docker Compose
- Une clé SSH privée sans passphrase, déposée dans `secrets/`
- Sur chaque machine cible : le compte de service correspondant, sa clé publique
  dans `~/.ssh/authorized_keys`, et **un shell de connexion valide**
  (`/bin/bash`). Avec `/usr/sbin/nologin`, l'authentification réussit mais toute
  commande échoue instantanément.

---

## Installation

```bash
git clone taekyon/taskins && cd taskins

mkdir -p secrets
cp /chemin/vers/cle_privee secrets/taskins_ed25519
chmod 600 secrets/taskins_ed25519

cp .env.example .env.prod
```

Éditer `.env.prod`. Trois valeurs à ne pas laisser par défaut :

| Variable | Remarque |
|---|---|
| `TASKINS_SECRET_KEY` | `openssl rand -hex 32`. Signe les cookies de session : une valeur devinable rend n'importe quelle session falsifiable. |
| `TASKINS_BOOTSTRAP_ADMIN_PASSWORD` | Sert au tout premier démarrage. À changer ensuite depuis `/account`. |
| `TASKINS_SEED_MACHINE_HOST` | Adresse de la première machine cible. Laisser vide pour n'en créer aucune et les ajouter depuis `/admin`. |

Derrière un proxy d'entreprise, ajouter également :

```env
HTTP_PROXY=http://adresse-du-proxy:8080
HTTPS_PROXY=http://adresse-du-proxy:8080
NO_PROXY=localhost,127.0.0.1,192.168.*,10.*
```

Démarrer :

```bash
docker compose --env-file .env.prod up --build -d
```

L'application écoute sur le port 80. Pour en changer, définir
`TASKINS_HTTP_PORT` dans `.env.prod`.

---

## Pourquoi `--env-file` *et* `env_file:`

Deux mécanismes distincts, souvent confondus :

- `env_file: .env.prod` dans le fichier compose → injecte les variables **dans
  le conteneur**. C'est ce que lit l'application.
- `--env-file .env.prod` sur la ligne de commande → rend les variables
  disponibles pour l'**interpolation `${...}` du fichier compose lui-même**
  (port publié, arguments de proxy). Docker ne les transmet pas au conteneur.

Les deux pointent volontairement vers le même fichier : une seule source de
configuration par environnement.

Sans `--env-file`, les valeurs par défaut s'appliquent (port 80, pas de proxy)
et le build échouera sur un réseau filtré.

---

## Développement

```bash
cp .env.example .env.dev          # volume et port distincts de la production
docker compose -f docker-compose.dev.yml --env-file .env.dev up --build
```

Réinitialisé le volume

```bash
docker volume rm taskins-db-dev
```

Différences avec la production :

| | Développement | Production |
|---|---|---|
| Volume de base | `taskins-db-dev` | `taskins-db-prod` |
| Code | monté depuis le disque (`.:/app`) | figé dans l'image au build |
| Rechargement | `--reload` actif | inactif |
| Dépendances de test | installées | absentes |

La séparation des volumes est la protection la plus importante : réinitialiser
la base de développement — opération courante lors d'un changement de schéma —
ne peut jamais atteindre les données de production.

Tests :

```bash
docker compose -f docker-compose.dev.yml exec taskins pytest
```

---

## Exploitation

**Sauvegarde** — toute la base tient dans un fichier. À planifier sur l'hôte :

```bash
docker compose exec -T taskins sqlite3 /app/data/taskins.db \
  ".backup /app/data/backup.db"
docker cp taskins-app:/app/data/backup.db ./taskins-$(date +%F).db
```

**Journaux** : `docker compose logs -f taskins`

**Mise à jour** :

```bash
git pull
docker compose --env-file .env.prod up --build -d
```

**Changement de schéma** — `create_all()` crée les tables manquantes mais
**n'ajoute jamais de colonne** à une table existante. Appliquer le script
correspondant :

```bash
docker compose exec -T taskins sqlite3 /app/data/taskins.db \
  < migrations/00X-nom.sql
```

---

## Limites connues de cette version

- Le conteneur tourne en `root`.
- Pas de HTTPS : le cookie de session n'est pas marqué `Secure`. Convient à un
  réseau interne ; derrière un reverse proxy TLS, passer `https_only=True` au
  `SessionMiddleware` dans `main.py`.
- Aucune récupération de mot de passe en libre-service : seul un administrateur
  peut réinitialiser celui d'un autre utilisateur, depuis `/admin`.
- Approbation administrateur des workflows et exécution parallèle non
  implémentées (voir `docs/ETAT-PROJET.md`).

---

## Dépannage

| Symptôme | Cause probable |
|---|---|
| Build en échec sur `pip install` | Proxy absent : vérifier `HTTP_PROXY` dans le fichier passé à `--env-file`. |
| `curl` local renvoie une page de filtrage | Le proxy intercepte le trafic local : ajouter `--noproxy '*'`. |
| Exécution en échec instantané, sortie « This account is currently not available. » | Le compte de service a `nologin` pour shell sur la machine cible. |
| Exécution bloquée en `PENDING` | Le moteur ne tourne pas : vérifier les journaux au démarrage. |
| `ModuleNotFoundError: No module named 'taskins'` au lancement des tests | Lancer depuis `/app` ; vérifier `pythonpath = .` dans `pytest.ini`. |
| Traceback citant un fichier inexistant, avec `???` | `__pycache__` périmé : `find . -name __pycache__ -type d -exec rm -rf {} +` |

Développement assisté par un LLM ; tout le code est revu et validé par l'auteur avant intégration.