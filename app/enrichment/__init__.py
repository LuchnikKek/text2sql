"""Источники обогащения сущностей данными внешних систем.

Импорт модулей источников здесь обязателен: именно он наполняет реестр.
"""

from app.enrichment import courses  # noqa: F401 — регистрирует CoursesSource
from app.enrichment.base import EnrichmentError, EnrichmentSource, EntityNotFound
from app.enrichment.registry import get_source, register, source_names, unregister

__all__ = [
    "EnrichmentError",
    "EnrichmentSource",
    "EntityNotFound",
    "get_source",
    "register",
    "source_names",
    "unregister",
]
