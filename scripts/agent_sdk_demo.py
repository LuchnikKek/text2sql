"""Демо Claude Agent SDK — агент, чинящий упавшие тесты этого проекта.

Установка и запуск (зависимость в pyproject НЕ добавлена намеренно —
это демо, а не часть приложения):

    uv add --dev claude-agent-sdk
    # аутентификация: подписка claude.ai (claude login) или ANTHROPIC_API_KEY
    uv run python scripts/agent_sdk_demo.py

Карта соответствий для тех, кто пришёл из LangGraph:

    LangGraph                        Agent SDK
    ---------------------------      -----------------------------------
    граф: узлы + рёбра + state       готовый агентный цикл (harness)
    tools у узла-агента              tools + MCP-серверы
    checkpointer / thread_id         сессии: continue_conversation, resume
    astream() по узлам               async for message in query()
    subgraphs                        subagents (agents={...})
    interrupt() / HITL               permission_mode + can_use_tool callback
    guardrail-рёбра                  hooks (PreToolUse/PostToolUse)

Ключевая разница: в LangGraph маршрут задаёшь ты, здесь — модель.
"""

import asyncio
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    query,
    tool,
)


# In-process MCP-инструмент: аналог @tool из LangChain, но по протоколу MCP.
# Такой же сервер можно поднять отдельным процессом — и тогда его увидит
# не только этот скрипт, но и Claude Code, и любой MCP-клиент.
@tool("run_tests", "Запустить тесты проекта и вернуть вывод", {})
async def run_tests(args: dict[str, Any]) -> dict[str, Any]:
    proc = await asyncio.create_subprocess_shell(
        "uv run pytest -q --tb=short",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return {"content": [{"type": "text", "text": out.decode()[-4000:]}]}


test_server = create_sdk_mcp_server(name="testing", tools=[run_tests])


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt=(
            "Ты работаешь в проекте text2sql-api. "
            "Прогони тесты; если есть падения — найди причину и почини "
            "минимальной правкой, затем прогони тесты снова."
        ),
        mcp_servers={"testing": test_server},
        # Права: читать/править код и звать наш инструмент — без вопросов;
        # всё остальное агенту недоступно. Аналог permissions из модуля 2.
        allowed_tools=["Read", "Grep", "Glob", "Edit", "mcp__testing__run_tests"],
        permission_mode="acceptEdits",
        max_turns=25,
    )

    async for message in query(prompt="Проверь тесты проекта.", options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(message, ResultMessage):
            print(f"\n--- готово: {message.subtype} ---")


if __name__ == "__main__":
    asyncio.run(main())
