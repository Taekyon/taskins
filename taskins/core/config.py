from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str
    debug: bool = False
    db_path: str = "/app/data/taskins.db"
    ssh_key_path: str = "/app/secrets/taskins_ed25519"
    scheduler_interval: int = 10
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None

    # Timeout appliqué à une tâche qui n'en définit pas (tasks.timeout_seconds NULL).
    default_task_timeout: int = 300

    # Fuseau dans lequel les expressions cron et les dates saisies sont
    # interprétées. Le stockage reste en UTC.
    timezone: str = "Europe/Bern"

    # Tolérance avant de considérer une occurrence comme manquée. Au-delà,
    # elle est ignorée sans rattrapage (décision validée) et la planification
    # repart à l'occurrence suivante.
    schedule_grace_seconds: int = 60

    model_config = {"env_file": ".env", "env_prefix": "TASKINS_"}


settings = Settings()
