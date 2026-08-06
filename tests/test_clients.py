"""Слой клиентов внешних API: настройки, запросы, ошибки, закрытие."""

import httpx
import pytest
from pydantic_settings import SettingsConfigDict

from app.clients import (
    RestClient,
    RestClientError,
    RestClientNotFound,
    RestClientSettings,
    aclose_all,
)
from app.clients.courses import CoursesClient, CoursesClientSettings


def make_client(handler, **settings_kwargs) -> CoursesClient:
    """CoursesClient поверх мок-транспорта — без выхода в сеть."""
    settings = CoursesClientSettings(**settings_kwargs)
    return CoursesClient(settings, transport=httpx.MockTransport(handler))


def json_handler(payload: dict, status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return handler


# --- Настройки -------------------------------------------------------------


def test_settings_defaults():
    settings = CoursesClientSettings()
    assert settings.url == "https://api.example.com/courses"
    assert settings.timeout == 5.0


def test_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("COURSES_CLIENT_URL", "https://courses.internal")
    monkeypatch.setenv("COURSES_CLIENT_TIMEOUT", "1.5")
    settings = CoursesClientSettings()
    assert settings.url == "https://courses.internal"
    assert settings.timeout == 1.5


def test_env_prefix_isolates_clients(monkeypatch):
    """Настройки одного клиента не протекают в другой."""

    class OtherClientSettings(RestClientSettings):
        model_config = SettingsConfigDict(env_prefix="OTHER_CLIENT_")

        url: str = "https://other.example.com"

    monkeypatch.setenv("COURSES_CLIENT_URL", "https://courses.internal")
    assert OtherClientSettings().url == "https://other.example.com"


def test_settings_ignore_unknown_env(monkeypatch):
    """extra='ignore' из базового класса не теряется при наследовании."""
    monkeypatch.setenv("COURSES_CLIENT_WHATEVER", "нечто")
    assert CoursesClientSettings().url == "https://api.example.com/courses"


# --- Запросы ---------------------------------------------------------------


async def test_get_returns_json():
    client = make_client(json_handler({"title": "SQL для аналитиков"}))
    assert await client.get_course("c-101") == {"title": "SQL для аналитиков"}
    await client.aclose()


async def test_base_url_and_timeout_are_applied():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={})

    client = make_client(handler, url="https://courses.internal/api", timeout=2.5)
    await client.get_course("c-101")
    assert seen["url"] == "https://courses.internal/api/c-101"
    assert client._get_client().timeout == httpx.Timeout(2.5)
    await client.aclose()


async def test_get_passes_query_params():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json={})

    client = make_client(handler)
    await client.get("/c-101", params={"lang": "ru"})
    assert seen["params"] == {"lang": "ru"}
    await client.aclose()


# --- Ошибки ----------------------------------------------------------------


async def test_404_raises_not_found():
    client = make_client(json_handler({"detail": "no"}, status_code=404))
    with pytest.raises(RestClientNotFound):
        await client.get_course("c-000")
    await client.aclose()


async def test_500_raises_client_error():
    client = make_client(json_handler({"detail": "boom"}, status_code=500))
    with pytest.raises(RestClientError):
        await client.get_course("c-101")
    await client.aclose()


async def test_timeout_raises_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("too slow", request=request)

    client = make_client(handler)
    with pytest.raises(RestClientError):
        await client.get_course("c-101")
    await client.aclose()


async def test_invalid_json_raises_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>не json</html>")

    client = make_client(handler)
    with pytest.raises(RestClientError):
        await client.get_course("c-101")
    await client.aclose()


def test_not_found_is_client_error():
    """Источнику достаточно поймать RestClientError, чтобы не пропустить сбой."""
    assert issubclass(RestClientNotFound, RestClientError)


# --- Жизненный цикл --------------------------------------------------------


async def test_httpx_client_is_created_lazily():
    client = make_client(json_handler({}))
    assert client._client is None  # импорт/создание не открывает соединений
    await client.get_course("c-101")
    assert client._client is not None
    await client.aclose()


async def test_aclose_is_idempotent():
    client = make_client(json_handler({}))
    await client.get_course("c-101")
    await client.aclose()
    await client.aclose()
    assert client._client is None


async def test_aclose_all_closes_created_clients():
    client = make_client(json_handler({}))
    await client.get_course("c-101")
    await aclose_all()
    assert client._client is None
    await aclose_all()  # повторный вызов безопасен


def test_default_settings_class_is_used():
    """Клиент без своего settings_class всё равно получает url/timeout."""
    client = RestClient()
    assert isinstance(client.settings, RestClientSettings)
    assert client.settings.timeout == 10.0
