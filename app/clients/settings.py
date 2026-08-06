"""Настройки REST-клиентов.

Каждый клиент объявляет свой подкласс с `env_prefix` и дефолтами —
так настройки клиента живут рядом с ним, а app/config.py не разрастается
по мере появления новых внешних систем.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class RestClientSettings(BaseSettings):
    """Базовые настройки REST-клиента: куда ходить и сколько ждать."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    #: base_url внешнего API
    url: str = ""
    #: общий таймаут запроса, секунды
    timeout: float = 10.0
