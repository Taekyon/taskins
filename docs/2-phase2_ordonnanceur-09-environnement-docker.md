# Taskins — Environnement Docker et pratiques de travail

## Configuration applicative via `.env`

Les paramètres qui changent selon l'environnement mais ne sont pas des données métier vivent dans un fichier `.env` par environnement, lu via `pydantic-settings` :

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    debug: bool = False
    db_path: str = "/app/data/taskins.db"
    ssh_key_path: str = "/app/secrets/taskins_ed25519"
    scheduler_interval: int = 10

    class Config:
        env_file = ".env"
        env_prefix = "TASKINS_"
```

Docker Compose charge le fichier explicitement :

```yaml
services:
  taskins:
    build: .
    env_file: .env.dev   # ou .env.prod
    volumes:
      - db-data:/app/data
      - ./secrets:/app/secrets:ro
```

## Machines cibles : gestion via l'interface web (approche retenue)

Les machines cibles sont des données, pas de la configuration — elles vivent dans la table `machines`, gérées depuis l'interface d'administration. Aucune machine n'est codée en dur ni définie dans un fichier de seed. Au premier démarrage d'un nouvel environnement, l'administrateur ajoute manuellement les machines pertinentes via l'interface.

## Isolation des environnements par volume Docker

Chaque environnement (développement, test, production) utilise un volume Docker nommé distinct, ce qui isole à la fois la base de données et la liste des machines qu'elle contient :

```yaml
# docker-compose.dev.yml
volumes:
  db-data:
    name: taskins-db-dev

# docker-compose.prod.yml
volumes:
  db-data:
    name: taskins-db-prod
```

Travailler sur un environnement ne risque jamais d'altérer la configuration d'un autre.

## Pratiques DevOps retenues

Développement principal via Notepad++ et WinSCP, en éditant directement les fichiers sur les VMs Proxmox d'entreprise. Débogage avancé via VS Code et l'extension Remote-SSH, réservé aux deux VMs de test dédiées. Gestion de version avec Git, synchronisation régulière vers un dépôt distant (GitHub/GitLab) servant de sauvegarde. Aucun outil CI/CD : la mise en place d'une chaîne d'intégration continue est jugée superflue pour un développeur unique sur un labo sans contrainte de disponibilité. Conteneurisation Docker obligatoire dès le premier jour, pour garantir la portabilité du code entre le laptop, les VMs de test et les VMs d'entreprise.
