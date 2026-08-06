"""Контракт источника обогащения.

Источник — это тонкий клиент к внешней системе: по идентификатору
сущности отдаёт словарь с данными. Протокол (а не абстрактный класс)
выбран сознательно: источнику достаточно совпасть по форме, наследование
от нашего типа ему не нужно.
"""

from typing import Protocol, runtime_checkable


class EnrichmentError(Exception):
    """Базовая ошибка источника обогащения."""


class EntityNotFound(EnrichmentError):
    """Сущность с таким идентификатором отсутствует в источнике."""


@runtime_checkable
class EnrichmentSource(Protocol):
    #: Имя источника в реестре, оно же — сегмент пути в /enrich/{source}/...
    name: str

    async def fetch(self, entity_id: str) -> dict:
        """Вернуть данные сущности.

        Поднимает EntityNotFound, если сущности нет, и любую другую
        EnrichmentError при проблемах с внешней системой.
        """
        ...
