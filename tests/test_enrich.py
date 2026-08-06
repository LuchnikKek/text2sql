import pytest

from app.enrichment import (
    EnrichmentError,
    EnrichmentSource,
    EntityNotFound,
    _source_module_names,
    get_source,
    register,
    source_names,
    unregister,
)
from app.enrichment.courses import CoursesSource
from app.enrichment.events import EventsSource


class BrokenSource:
    """Источник, у которого «отвалилась» внешняя система."""

    name = "broken"

    async def fetch(self, entity_id: str) -> dict:
        raise EnrichmentError("upstream is down")


@pytest.fixture
def broken_source():
    register(BrokenSource())
    yield
    unregister("broken")


# --- Реестр и протокол -----------------------------------------------------


def test_courses_source_matches_protocol():
    assert isinstance(CoursesSource(), EnrichmentSource)


def test_courses_registered_on_import():
    assert "courses" in source_names()
    assert isinstance(get_source("courses"), CoursesSource)


def test_every_source_module_registers_a_source():
    """Сторож автоимпорта: модуль в пакете есть, а register() внизу забыт.

    Автоимпорт сам по себе этого не ловит — модуль импортируется, но реестр
    остаётся пустым, и источник молча отсутствует.
    """
    registering_modules = {
        type(get_source(name)).__module__.rsplit(".", 1)[-1] for name in source_names()
    }
    missing = _source_module_names() - registering_modules
    assert not missing, f"модули без зарегистрированного источника: {missing}"


def test_get_unknown_source_returns_none():
    assert get_source("nope") is None


def test_duplicate_registration_rejected():
    with pytest.raises(ValueError):
        register(CoursesSource())


def test_register_and_unregister(broken_source):
    assert "broken" in source_names()
    unregister("broken")
    assert get_source("broken") is None


# --- Источник courses ------------------------------------------------------


async def test_courses_fetch_returns_data():
    data = await CoursesSource().fetch("c-101")
    assert data["title"] == "SQL для аналитиков"
    assert data["hours"] == 16


async def test_courses_fetch_unknown_entity_raises():
    with pytest.raises(EntityNotFound):
        await CoursesSource().fetch("c-000")


async def test_courses_fetch_returns_copy():
    """Мутация ответа не должна портить мок-данные источника."""
    source = CoursesSource()
    data = await source.fetch("c-101")
    data["title"] = "испорчено"
    assert (await source.fetch("c-101"))["title"] == "SQL для аналитиков"


# --- Источник events -------------------------------------------------------


def test_events_source_matches_protocol():
    assert isinstance(EventsSource(), EnrichmentSource)


def test_events_registered_on_import():
    assert "events" in source_names()
    assert isinstance(get_source("events"), EventsSource)


async def test_events_fetch_returns_data():
    data = await EventsSource().fetch("e-101")
    assert data["title"] == "Летний тимбилдинг"
    assert data["participants"] == 120


async def test_events_fetch_unknown_entity_raises():
    with pytest.raises(EntityNotFound):
        await EventsSource().fetch("e-000")


async def test_events_fetch_returns_copy():
    source = EventsSource()
    data = await source.fetch("e-101")
    data["title"] = "испорчено"
    assert (await source.fetch("e-101"))["title"] == "Летний тимбилдинг"


# --- Эндпоинт --------------------------------------------------------------


async def test_enrich_endpoint_returns_source_data(client, auth_headers):
    resp = await client.get("/api/v1/enrich/courses/c-202", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "source": "courses",
        "entity_id": "c-202",
        "data": {
            "title": "Оконные функции на практике",
            "hours": 8,
            "level": "advanced",
            "tags": ["sql", "window-functions"],
        },
    }


async def test_enrich_endpoint_returns_event_data(client, auth_headers):
    resp = await client.get("/api/v1/enrich/events/e-202", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "source": "events",
        "entity_id": "e-202",
        "data": {
            "title": "Внутренний митап по данным",
            "date": "2026-09-24",
            "location": "Zoom",
            "format": "online",
            "participants": 45,
        },
    }


async def test_enrich_unknown_event_returns_404(client, auth_headers):
    resp = await client.get("/api/v1/enrich/events/e-000", headers=auth_headers)
    assert resp.status_code == 404


async def test_enrich_unknown_source_returns_404(client, auth_headers):
    resp = await client.get("/api/v1/enrich/unknown/c-101", headers=auth_headers)
    assert resp.status_code == 404
    assert "courses" in resp.json()["detail"]


async def test_enrich_unknown_entity_returns_404(client, auth_headers):
    resp = await client.get("/api/v1/enrich/courses/c-000", headers=auth_headers)
    assert resp.status_code == 404


async def test_enrich_source_failure_returns_502(client, auth_headers, broken_source):
    resp = await client.get("/api/v1/enrich/broken/whatever", headers=auth_headers)
    assert resp.status_code == 502


async def test_enrich_requires_auth(client):
    resp = await client.get("/api/v1/enrich/courses/c-101")
    assert resp.status_code == 401
