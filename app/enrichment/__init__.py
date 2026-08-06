"""Источники обогащения сущностей данными внешних систем.

Реестр наполняется импортом модулей источников, и делается это здесь
автоматически: положил модуль в пакет — источник доступен. Ручной список
импортов не ведём, потому что забытая строчка молча лишала бы приложение
источника (эндпоинт просто отвечал бы 404 «unknown source»).
"""

import pkgutil
from importlib import import_module

from app.enrichment.base import EnrichmentError, EnrichmentSource, EntityNotFound
from app.enrichment.registry import get_source, register, source_names, unregister

#: Модули пакета, которые источниками не являются.
_INTERNAL_MODULES = {"base", "registry"}


def _source_module_names() -> set[str]:
    """Модули пакета, считающиеся источниками.

    Всё, кроме служебных и начинающихся с подчёркивания, — значит
    вспомогательные модули внутри пакета называем с префиксом `_`.
    Используется и при автоимпорте, и в тесте-стороже.
    """
    return {
        module.name
        for module in pkgutil.iter_modules(__path__)
        if not module.name.startswith("_") and module.name not in _INTERNAL_MODULES
    }


# Ограничение, которое накладывает автоимпорт: модуль источника может
# импортировать `app.enrichment.base` / `.registry`, но не сам пакет
# `app.enrichment` — иначе получим циклический импорт.
for _module_name in sorted(_source_module_names()):
    import_module(f"{__name__}.{_module_name}")

__all__ = [
    "EnrichmentError",
    "EnrichmentSource",
    "EntityNotFound",
    "get_source",
    "register",
    "source_names",
    "unregister",
]
