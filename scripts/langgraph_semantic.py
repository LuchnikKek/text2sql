"""Демо: агент LangChain поверх MCP-серверов проекта (warehouse + semantic-layer).

Тулзы не пишутся руками: `MultiServerMCPClient` поднимает те же stdio-серверы,
что описаны в `.mcp.json`, и отдаёт их тулзы как обычные LangChain-инструменты.
Дальше `create_agent` собирает граф ReAct-агента, модель — GigaChat.

Запуск:
    uv run python scripts/langgraph_semantic.py "что такое блок Финансы в наших данных?"
    uv run python scripts/langgraph_semantic.py "верни список баз данных для warehouse"


Полезные переменные окружения:

    GIGACHAT_CREDENTIALS      — обязательна, авторизационные данные
    GIGACHAT_SCOPE            — GIGACHAT_API_PERS (по умолчанию) / _B2B / _CORP
    GIGACHAT_MODEL            — имя модели, по умолчанию GigaChat-2-Max
    GIGACHAT_VERIFY_SSL_CERTS — false, если нет сертификатов НУЦ Минцифры
"""

from __future__ import annotations


import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain_gigachat import GigaChat
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StdioConnection


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv()

SYSTEM_PROMPT = """Ты аналитик по данным проекта text2sql.

Порядок работы:
1. Значение бизнес-терминов уточняй тулзами semantic-layer
   (lookup_term / list_terms) — это единственный источник правды о том,
   какие поля и таблицы за термин отвечают.
2. Структуру и данные смотри тулзами warehouse (wh_list_tables, wh_run_query).
3. Отвечай по-русски, коротко, и показывай SQL, которым получил ответ.
"""

ALLOWED = {"wh_list_tables", "wh_run_query", "lookup_term", "list_terms"}

def mcp_servers() -> dict[str, StdioConnection]:
    """Те же stdio-серверы, что в .mcp.json, но запускаемые из скрипта."""

    def stdio(script: str) -> StdioConnection:
        return {
            "transport": "stdio",
            "command": "uv",
            "args": ["run", "python", f"servers/{script}"],
            "cwd": str(PROJECT_ROOT),
            # Пробрасываем окружение целиком: warehouse_proxy читает из него
            # CLICKHOUSE_*, а uv — PATH и свои переменные.
            "env": dict(os.environ),
        }

    return {
        "warehouse": stdio("warehouse_proxy.py"),
        "semantic-layer": stdio("semantic_layer.py"),
    }


def collapse_optionals(node: Any) -> Any:
    """Схлопывает `anyOf: [X, null]` в `X` в JSON-схеме тулза.

    GigaChat не поддерживает union-типы и падает с IncorrectSchemaException,
    а MCP-тулзы (например wh_list_tables) описывают необязательные аргументы
    как Optional[...]. Значение всё равно необязательное — оно не в `required`.
    """
    if isinstance(node, list):
        return [collapse_optionals(item) for item in node]
    if not isinstance(node, dict):
        return node

    variants = node.get("anyOf")
    if variants:
        non_null = [v for v in variants if v.get("type") != "null"]
        chosen = collapse_optionals(non_null[0]) if non_null else {"type": "string"}
        rest = {k: v for k, v in node.items() if k != "anyOf"}
        node = {**chosen, **rest}

    return {k: collapse_optionals(v) for k, v in node.items()}


def build_model() -> GigaChat:
    credentials = os.getenv("GIGACHAT_CREDENTIALS")
    if not credentials:
        raise SystemExit("Нужна переменная окружения GIGACHAT_CREDENTIALS")

    return GigaChat(
        credentials=credentials,
        scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
        model=os.getenv("GIGACHAT_MODEL", "GigaChat-2-Max"),
        verify_ssl_certs=False,
        temperature=0.1,
        timeout=120,
    )


async def main() -> None:
    question = " ".join(sys.argv[1:])

    # Клиент не контекстный менеджер: сессия к серверу открывается на каждый
    # вызов тулзы, поэтому список тулз можно получить один раз и жить дальше.
    client = MultiServerMCPClient(mcp_servers())
    tools = await client.get_tools()
    tools = [t for t in tools if t.name in ALLOWED]

    for tool in tools:
        if isinstance(tool.args_schema, dict):
            tool.args_schema = collapse_optionals(tool.args_schema)
    print(f"тулзы из MCP: {', '.join(t.name for t in tools)}\n")

    agent = create_agent(model=build_model(), tools=tools, system_prompt=SYSTEM_PROMPT)

    result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
    for message in result["messages"]:
        for call in getattr(message, "tool_calls", []):
            print(f"-> {call['name']}({call['args']})")
    print(f"\n{result['messages'][-1].content}")


if __name__ == "__main__":
    asyncio.run(main())
