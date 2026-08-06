from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Читаются из переменных окружения / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_secret: str = "dev-secret-change-me-min-20-bytes-long"
    jwt_algorithm: str = "HS256"
    database_url: str = "sqlite+aiosqlite:///./text2sql.db"
