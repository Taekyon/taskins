# taskins

Taskins est un ordonnanceur simple permettant d'exécuter des workflows (jobs) sur plusieurs machines, avec exécution à distance via SSH, planification et supervision web.

> **Statut : alpha.** Fonctionnel et testé, mais le contrôle d'accès est
> incomplet — voir [Limites connues](#limites-connues) avant tout déploiement.

- [Architecture technique](ARCHITECTURE.md)
- [Guide du contributeur](MAINTENANCE.md)
- [Évolutions prévues](ROADMAP.md)

---

## À propos

Taskins est né d'un atelier de formation dont l'objectif était de concevoir un
outil interne exploitable en entreprise, en s'appuyant sur l'assistance de l'IA
tout au long du cycle de développement. Le cahier des charges demandait un
ordonnanceur capable d'enchaîner des tâches sur plusieurs machines via SSH, avec
une interface de supervision et une gestion des utilisateurs.

Le besoin couvert est courant : automatiser des traitements récurrents —
sauvegardes, maintenance, déploiements — sans disperser des tâches `cron` sur
chaque serveur, et sans perdre la trace de ce qui s'est réellement exécuté. Les
codes de retour, les sorties et l'historique complet sont conservés et
consultables depuis une interface unique.

---

## Fonctionnalités

**Workflows** — définition d'une suite ordonnée de tâches, chacune associée à
une commande shell et à une machine cible. Une tâche peut être conditionnée au
code de retour d'une tâche antérieure. Chaque tâche dispose d'un délai maximal
au-delà duquel elle est interrompue.

**Exécution** — lancement manuel ou planifié. Un workflow validé est immuable et
peut être relancé autant de fois que nécessaire. Une exécution peut être
redirigée vers une autre machine que celle prévue dans la définition, sans
modifier cette définition.

**Planification** — exécution différée à une date donnée, ou récurrente au
format `cron`. Les heures sont saisies et affichées dans le fuseau configuré ;
le stockage reste en UTC. Les occurrences manquées pendant un arrêt du service
ne sont pas rattrapées.

**Supervision** — vue d'ensemble (exécutions récentes, échecs, prochaines
planifications), détail par workflow et par exécution avec la commande
réellement exécutée, la machine utilisée, le code de retour et les sorties. Les
pages se rafraîchissent d'elles-mêmes tant qu'une exécution est en cours.

**Administration** — gestion des comptes, des machines cibles et des groupes ;
attribution du rôle administrateur ; réinitialisation de mot de passe.

---

## Prérequis

- Docker et Docker Compose
- Une clé SSH privée **sans phrase de passe**, placée dans `secrets/`
- Sur chaque machine cible : le compte de service (`svc-taskins` par défaut)
  avec la clé publique correspondante et **un shell de connexion valide**
  (`/bin/bash`). Avec `/usr/sbin/nologin`, l'authentification réussit mais toute
  commande échoue instantanément.

---

## Installation

```bash
git clone <dépôt> && cd taskins

mkdir -p secrets
cp /chemin/vers/cle_privee secrets/taskins_ed25519
chmod 600 secrets/taskins_ed25519

cp .env.example .env.prod
```

Éditer `.env.prod` — voir [Configuration](#configuration). Puis :

```bash
docker compose --env-file .env.prod build
docker compose --env-file .env.prod up -d
```

L'interface écoute sur le port 80. Se connecter avec le compte d'amorçage défini
dans `.env.prod`, puis **changer immédiatement son mot de passe** depuis la page
« Mon compte ».

---

## Configuration

Toute la configuration tient dans un fichier `.env`, non versionné.

| Variable | Rôle |
|---|---|
| `TASKINS_SECRET_KEY` | Signe les cookies de session. Générer une valeur unique : `openssl rand -hex 32`. Une valeur devinable rend toute session falsifiable. |
| `TASKINS_DEBUG` | Journalisation détaillée. `false` en production. |
| `TASKINS_DB_PATH` | Emplacement du fichier SQLite dans le conteneur. |
| `TASKINS_SSH_KEY_PATH` | Clé privée dans le conteneur. |
| `TASKINS_SCHEDULER_INTERVAL` | Fréquence du cycle du moteur, en secondes (10). |
| `TASKINS_DEFAULT_TASK_TIMEOUT` | Délai maximal d'une tâche qui n'en définit pas (300 s). |
| `TASKINS_TIMEZONE` | Fuseau d'interprétation des planifications (`Europe/Paris`). |
| `TASKINS_SCHEDULE_GRACE_SECONDS` | Retard au-delà duquel une occurrence est considérée manquée et ignorée (60 s). |
| `TASKINS_BOOTSTRAP_ADMIN_USERNAME` | Compte administrateur créé **uniquement** si la table des utilisateurs est vide. |
| `TASKINS_BOOTSTRAP_ADMIN_PASSWORD` | Idem. À changer depuis l'interface après la première connexion. |
| `TASKINS_SEED_MACHINE_HOST` | Première machine cible créée au démarrage initial. Si vide, aucune machine n'est créée. |
| `TASKINS_HTTP_PORT` | Port publié sur l'hôte (80 en production, 8000 en développement). |
| `HTTP_PROXY` `HTTPS_PROXY` `NO_PROXY` | Proxy sortant, nécessaire à la construction de l'image sur un réseau filtré. |

### Pourquoi `--env-file` *et* `env_file:`

Deux mécanismes distincts, souvent confondus :

- `env_file:` dans le fichier Compose injecte les variables **dans le
  conteneur**. C'est ce que lit l'application.
- `--env-file` sur la ligne de commande alimente l'**interpolation `${...}` du
  fichier Compose lui-même** — port publié, arguments de proxy. Docker ne
  transmet pas ces valeurs au conteneur.

Les deux pointent volontairement vers le même fichier : une seule source de
configuration par environnement. Sans `--env-file`, les valeurs par défaut
s'appliquent et la construction échoue derrière un proxy.

---

## Exploitation

| Opération | Commande |
|---|---|
| Démarrer | `docker compose --env-file .env.prod up -d` |
| Arrêter | `docker compose --env-file .env.prod down` |
| Journaux | `docker compose logs -f taskins` |
| État | `docker compose ps` |

### Mise à jour

```bash
git pull
docker compose --env-file .env.prod build
docker compose --env-file .env.prod up -d
```

Si la mise à jour ajoute des colonnes en base, elles **ne sont pas créées
automatiquement**. Appliquer le script correspondant :

```bash
docker compose exec -T taskins \
  sqlite3 /app/data/taskins.db < migrations/00X-nom.sql
```

### Sauvegarde

Toutes les données tiennent dans un fichier SQLite. Sauvegarde à chaud,
cohérente même si le service écrit pendant l'opération :

```bash
docker compose exec -T taskins python -c "
import sqlite3
src = sqlite3.connect('/app/data/taskins.db')
dst = sqlite3.connect('/app/data/backup.db')
src.backup(dst); dst.close(); src.close()"

docker cp taskins-app:/app/data/backup.db ./taskins-$(date +%F).db
```

Cette sauvegarde n'est pas automatisée. La planifier sur l'hôte est la première
chose à faire après une mise en service.

La clé privée dans `secrets/` doit être sauvegardée séparément : sans elle,
aucune tâche ne s'exécute plus.

---

## Limites connues

**CONTRÔLE D'ACCÈS INCOMPLET** Tout utilisateur authentifié peut consulter,
**exécuter** et **planifier** n'importe quel workflow, y compris ceux d'un autre
utilisateur, et rediriger son exécution vers n'importe quelle machine
enregistrée. Concrètement, tout compte permet de déclencher des commandes shell
arbitraires sur l'ensemble du parc. À ne déployer que sur un périmètre où tous
les comptes sont de confiance. Correction prévue — voir [ROADMAP](ROADMAP.md).

**Validation administrateur inopérante.** Soumettre un workflow le rend
immédiatement exécutable, sans intervention d'un administrateur.

**Pas de HTTPS.** Le cookie de session n'est pas marqué `Secure`. Convient à un
réseau interne ; derrière un reverse proxy TLS, passer `https_only=True` au
`SessionMiddleware` dans `main.py`.

**Conteneur exécuté en `root`.**

**Pas de récupération de mot de passe en libre-service** : seul un
administrateur peut réinitialiser celui d'un autre utilisateur. Conserver au
moins deux comptes administrateurs.

**Exécutions séquentielles.** Les tâches d'un workflow s'exécutent en série, et
le moteur traite une exécution à la fois.

---

## Dépannage

| Symptôme | Cause probable |
|---|---|
| La construction échoue à l'installation des dépendances | Proxy non renseigné dans le fichier passé à `--env-file`. |
| Exécution en échec instantané, sortie « This account is currently not available. » | Le compte de service n'a pas de shell valide sur la machine cible : `usermod -s /bin/bash svc-taskins`. |
| Exécution bloquée en attente | Le moteur ne tourne pas. Vérifier les journaux au démarrage. |
| Échec de connexion SSH | Vérifier la clé dans `secrets/`, ses permissions (600), et la clé publique sur la machine cible. |
| Une requête locale renvoie une page de filtrage | Le proxy intercepte le trafic local : ajouter `--noproxy '*'`. |
| Une planification ne se déclenche pas | Vérifier qu'elle est active, que le workflow n'est pas archivé, et le fuseau configuré. |
| `ModuleNotFoundError: No module named 'taskins'` au lancement des tests | Lancer depuis `/app` ; vérifier `pythonpath = .` dans `pytest.ini`. |

---

## Développement

Voir [MAINTENANCE.md](MAINTENANCE.md) pour l'installation d'un environnement de
développement, les conventions de code et l'exécution des tests.
