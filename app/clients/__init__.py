"""Клиенты внешних API.

Клиент = один внешний API. Источник обогащения (app/enrichment) собирает
свой ответ из одного или нескольких клиентов.

В отличие от app/enrichment/__init__.py, импортировать здесь модули
конкретных клиентов не нужно: реестра клиентов нет, клиент попадает в игру
через свой источник.
"""

from app.clients.base import RestClient, RestClientError, RestClientNotFound, aclose_all
from app.clients.settings import RestClientSettings

__all__ = [
    "RestClient",
    "RestClientError",
    "RestClientNotFound",
    "RestClientSettings",
    "aclose_all",
]
