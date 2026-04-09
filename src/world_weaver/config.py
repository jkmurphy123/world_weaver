from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "world-weaver"
    app_env: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    api_token: str = "newsroom-dev-token"
    world_db_filename: str = "world.db"

    model_config = SettingsConfigDict(env_prefix="NEWSROOM_", extra="ignore")


def get_settings() -> Settings:
    return Settings()
