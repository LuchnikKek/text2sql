"""Stdio-прокси над MCP-сервером warehouse (mcp-clickhouse).

Оригинальный сервер поднимается как дочерний процесс, его тулзы монтируются
в namespace `wh`, а всё лишнее скрывается через visibility-транформы FastMCP.
Наружу (в Claude Code) торчат только тулзы, которых нет в BLOCKED_TOOLS.
"""

from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP
from fastmcp.server import create_proxy

NAMESPACE = "wh"

#: Тулзы оригинального сервера, которые прокси не выпускает наружу.
BLOCKED_TOOLS: set[str] = {"list_databases"}


def _target_config() -> dict[str, Any]:
    """Конфиг дочернего mcp-clickhouse (то же, что раньше было в .mcp.json)."""
    return {
        "mcpServers": {
            "default": {
                "command": "uvx",
                "args": ["--python", "3.13", "mcp-clickhouse"],
                "env": {
                    "CLICKHOUSE_HOST": os.getenv("CLICKHOUSE_HOST", "localhost"),
                    "CLICKHOUSE_PORT": os.getenv("CLICKHOUSE_HTTP_PORT", "8123"),
                    "CLICKHOUSE_USER": os.getenv("CLICKHOUSE_USER", "text2sql"),
                    "CLICKHOUSE_PASSWORD": os.getenv("CLICKHOUSE_PASSWORD", "text2sql"),
                    "CLICKHOUSE_DATABASE": os.getenv("CLICKHOUSE_DB", "text2sql"),
                    "CLICKHOUSE_SECURE": "false",
                    "CLICKHOUSE_VERIFY": "false",
                    "CLICKHOUSE_CONNECT_TIMEOUT": "30",
                    "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": "300",
                    "CHDB_ENABLED": "false",
                },
            }
        }
    }


def build_server() -> FastMCP:
    proxy = create_proxy(_target_config())
    # disable на самом прокси (provider-level) — имена ещё без префикса namespace
    proxy.disable(names=BLOCKED_TOOLS)

    mcp: FastMCP = FastMCP("warehouse-proxy")
    mcp.mount(proxy, namespace=NAMESPACE)
    return mcp


mcp = build_server()


if __name__ == "__main__":
    mcp.run()
