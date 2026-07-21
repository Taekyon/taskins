from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str
    debug: bool = False
    db_path: str = "/app/data/taskins.db"
    ssh_key_path: str = "/app/secrets/taskins_ed25519"
    scheduler_interval: int = 10
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None

    model_config = {"env_file": ".env", "env_prefix": "TASKINS_"}


settings = Settings()
