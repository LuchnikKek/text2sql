"""Debug-роуты: ручной прогон MCP-вызовов через живой сервер приложения.

Позволяют дебажить семантический слой из Swagger (/docs) или curl, не
собирая MCP-клиент руками. В публичный контракт API не входят.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.clients.semantic_layer import McpClientError, SemanticLayerClient

router = APIRouter(tags=["debug"])


class McpCallRequest(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


def _client(request: Request) -> SemanticLayerClient:
    return request.app.state.semantic_layer_client


@router.get("/debug/mcp/tools")
async def mcp_tools(request: Request) -> list[dict[str, str | None]]:
    try:
        return await _client(request).list_tools()
    except McpClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/debug/mcp/call")
async def mcp_call(request: Request, body: McpCallRequest) -> dict[str, Any]:
    try:
        result = await _client(request).call_tool(body.tool, body.args)
    except McpClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result


@router.get("/debug/mcp/lookup_term")
async def mcp_lookup_term(request: Request, term: str) -> dict[str, Any]:
    try:
        result = await _client(request).lookup_term(term)
    except McpClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result


@router.get("/debug/mcp/list_terms")
async def mcp_list_terms(request: Request) -> str:
    try:
        result = await _client(request).list_terms()
    except McpClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result
