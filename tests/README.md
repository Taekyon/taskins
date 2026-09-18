# Suite de tests

## Lancer les tests

Dans le conteneur de développement (les dépendances de test y sont installées
via `INSTALL_DEV=true`) :

```bash
docker compose -f docker-compose.dev.yml exec taskins pytest
```

Un fichier, un module :

```bash
docker compose -f docker-compose.dev.yml exec taskins pytest tests/test_engine.py
docker compose -f docker-compose.dev.yml exec taskins pytest -k timeout
```

Si `pytest` remonte `ModuleNotFoundError: No module named 'taskins'`, vérifier
que `pythonpath = .` est bien présent dans `pytest.ini` et que la commande est
lancée depuis `/app`. Un traceback mentionnant un chemin de fichier qui n'existe
plus, avec `???` à la place du code source, signale un `__pycache__` périmé :
`find . -name __pycache__ -type d -exec rm -rf {} +`.

## Ce que les tests n'exigent pas

Aucune connexion SSH réelle : `execute_command` est remplacé par un
enregistreur (`SSHRecorder` dans `conftest.py`). La logique interne du client
SSH — boucle de timeout, purge des tampons — est testée séparément dans
`test_ssh_client.py` contre un faux canal paramiko.

La boucle de fond du moteur est neutralisée (`TASKINS_SCHEDULER_INTERVAL` très
élevé) : les tests déclenchent un cycle explicitement via la fixture
`run_engine`. Le comportement est ainsi déterministe et ne dépend pas du temps
qui passe.

La base est recréée avant **chaque** test : aucun test ne dépend de l'ordre
d'exécution. C'est ce qui explique la durée totale (~70 s) — le hachage bcrypt
du compte administrateur est refait à chaque fois. Ce coût est assumé :
l'isolation vaut mieux que la vitesse sur une suite lancée occasionnellement.

## Organisation

| Fichier | Portée |
|---|---|
| `test_auth.py` | Connexion, sessions, cloisonnement des rôles |
| `test_machines.py` | Machines cibles, modification, gardes de suppression |
| `test_users_groups.py` | Utilisateurs, rôles, groupes |
| `test_workflows.py` | Création, validation, cycle de vie, archivage |
| `test_engine.py` | Enchaînement, conditions, timeout, instantané d'historique |
| `test_ssh_client.py` | Boucle de timeout, interblocage sur sortie volumineuse |
| `test_schedules.py` | Différé, cron, fuseau horaire, absence de rattrapage |
| `test_web.py` | Pages, fragments de rafraîchissement, accueil |

## Vérifier que la suite a des dents

Un test qui passe quoi qu'il arrive ne protège de rien. Pour s'en assurer,
casser volontairement une règle et confirmer qu'un test échoue — par exemple,
neutraliser l'évaluation des conditions dans `core/engine.py` doit faire
échouer `test_condition_non_satisfaite_arrete_l_execution`.
