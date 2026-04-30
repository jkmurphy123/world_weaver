import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _settings_file_path() -> Path:
    return Path(os.getenv("NEWSROOM_ENV_FILE", ".env"))


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def _serialize_env_value(value: str) -> str:
    if any(char.isspace() for char in value) or "#" in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def update_settings_file(updates: dict[str, str | None], *, path: Path | None = None) -> Path:
    settings_path = path or _settings_file_path()
    values = _parse_env_file(settings_path)

    for key, value in updates.items():
        if value is None:
            values.pop(key, None)
        else:
            values[key] = value

    lines = [f"{key}={_serialize_env_value(values[key])}" for key in sorted(values)]
    settings_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return settings_path


class Settings(BaseSettings):
    app_name: str = "world-weaver"
    app_env: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    api_token: str = "newsroom-dev-token"
    world_db_filename: str = "world.db"
    default_world_id: str = "world-main"
    default_world_name: str = "New Meridian"
    default_story_count: int = 4
    default_story_body_words: int = 500
    worldcodex_world: str = "world-main"
    worldcodex_cli: str = "world"
    worldcodex_timeout_seconds: int = 60
    llm_provider: str = "mock"
    llm_model: str = "mock-world-architect-v1"
    openai_api_key: str | None = None
    openai_timeout_seconds: int = 120

    model_config = SettingsConfigDict(env_prefix="NEWSROOM_", extra="ignore")


def get_settings() -> Settings:
    file_values = _parse_env_file(_settings_file_path())
    field_names = set(Settings.model_fields)

    values: dict[str, str] = {}
    for key, value in file_values.items():
        if not key.startswith("NEWSROOM_"):
            continue
        field_name = key.removeprefix("NEWSROOM_").lower()
        if field_name in field_names:
            values[field_name] = value

    for key, value in os.environ.items():
        if not key.startswith("NEWSROOM_"):
            continue
        field_name = key.removeprefix("NEWSROOM_").lower()
        if field_name in field_names:
            values[field_name] = value

    if "openai_api_key" not in values and os.getenv("OPENAI_API_KEY"):
        values["openai_api_key"] = os.environ["OPENAI_API_KEY"]

    return Settings(**values)
