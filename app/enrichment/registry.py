"""Реестр источников обогащения.

Модуль-синглтон: источники регистрируются при импорте своего модуля
(см. app/enrichment/__init__.py), роутер достаёт их по имени.
"""

from app.enrichment.base import EnrichmentSource

_SOURCES: dict[str, EnrichmentSource] = {}


def register(source: EnrichmentSource) -> EnrichmentSource:
    """Зарегистрировать источник. Имя должно быть уникальным."""
    if source.name in _SOURCES:
        raise ValueError(f"Enrichment source already registered: {source.name}")
    _SOURCES[source.name] = source
    return source


def unregister(name: str) -> None:
    """Убрать источник из реестра (нужно для изоляции тестов)."""
    _SOURCES.pop(name, None)


def get_source(name: str) -> EnrichmentSource | None:
    return _SOURCES.get(name)


def source_names() -> list[str]:
    return sorted(_SOURCES)
