# Taskins — Stack technologique

## Composants validés

| Composant | Technologie | Justification |
|---|---|---|
| Langage et framework web | Python 3.x, FastAPI | Adapté au scripting système, lisible pour un profil d'administration infrastructure, gère nativement l'asynchronisme requis par le moteur d'ordonnancement |
| Base de données | SQLite (fichier unique) | Volume cible très faible (quelques workflows par jour) ; évite la sur-ingénierie d'un SGBD réseau (PostgreSQL, MySQL) pour un PoC |
| Client SSH | paramiko | Bibliothèque Python standard pour piloter des sessions SSH de façon programmatique |
| Rendu des pages web | Jinja2 (intégré à FastAPI) | Voir `03-architecture-applicative.md` |
| Conteneurisation | Docker | Obligatoire dès le premier jour — voir `09-environnement-docker.md` |

## Gestion du fichier SQLite dans Docker

Le fichier SQLite doit être placé dans un volume Docker nommé, pour persister entre les redémarrages du conteneur. Le chemin exact est défini par la variable d'environnement `TASKINS_DB_PATH` — voir `07-nommage.md` et `09-environnement-docker.md`.
