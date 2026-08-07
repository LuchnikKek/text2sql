"""Тесты MCP-клиента семантического слоя и debug-роутов."""

import pytest

from app.clients.semantic_layer import McpClientError, SemanticLayerClient
from servers.semantic_layer import mcp


@pytest.fixture
def mcp_client() -> SemanticLayerClient:
    # in-process цель: те же тулзы, но без поднятия процесса по stdio
    return SemanticLayerClient(target=mcp)


@pytest.fixture
def debug_client(app, client, mcp_client):
    """HTTP-клиент приложения с подменённым MCP-клиентом в app.state."""
    app.state.semantic_layer_client = mcp_client
    return client


# --- Клиент ----------------------------------------------------------------


async def test_client_lookup_term(mcp_client):
    entry = await mcp_client.lookup_term("финблок")
    assert entry["term"] == "блок Финансы"
    assert entry["mapping"]["source"] == "clickhouse"
    assert entry["mapping"]["table"] == "hr.employees"


async def test_client_list_terms(mcp_client):
    text = await mcp_client.list_terms()
    assert "блок Финансы" in text


async def test_client_list_tools(mcp_client):
    names = {tool["name"] for tool in await mcp_client.list_tools()}
    assert {"lookup_term", "list_terms"} <= names


async def test_client_unknown_tool_raises(mcp_client):
    with pytest.raises(McpClientError):
        await mcp_client.call_tool("no_such_tool")


def test_client_resolves_relative_server_path():
    """Относительный путь из настроек не должен зависеть от cwd."""
    target = SemanticLayerClient()._connection_target()
    assert target.endswith("semantic_layer.py")
    assert "servers" in target


# --- Debug-роуты -----------------------------------------------------------


async def test_debug_tools_route(debug_client, auth_headers):
    resp = await debug_client.get("/api/v1/debug/mcp/tools", headers=auth_headers)
    assert resp.status_code == 200
    assert {"lookup_term", "list_terms"} <= {t["name"] for t in resp.json()}


async def test_debug_call_route(debug_client, auth_headers):
    resp = await debug_client.post(
        "/api/v1/debug/mcp/call",
        json={"tool": "lookup_term", "args": {"term": "финблок"}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["term"] == "блок Финансы"


async def test_debug_lookup_term_route(debug_client, auth_headers):
    resp = await debug_client.get(
        "/api/v1/debug/mcp/lookup_term",
        params={"term": "закончил обучение"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["term"] == "прошёл курс"


async def test_debug_call_unknown_tool_is_502(debug_client, auth_headers):
    resp = await debug_client.post(
        "/api/v1/debug/mcp/call",
        json={"tool": "no_such_tool"},
        headers=auth_headers,
    )
    assert resp.status_code == 502


async def test_debug_routes_require_auth(debug_client):
    resp = await debug_client.get("/api/v1/debug/mcp/tools")
    assert resp.status_code == 401
