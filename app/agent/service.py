"""Слой агента.

Внутренняя реализация text2sql-агента (LangGraph-граф) сознательно
оставлена за скобками: этот класс — граница между API и агентом.
Сейчас здесь заглушка; при подключении реального агента меняется
только тело run()/stream(), контракт остаётся прежним.
"""

import re
from collections.abc import AsyncIterator
from uuid import UUID

from app.schemas import Decision, DecisionType, HistoryMessage


class TextToSqlAgentService:
    async def run(
        self, *, chat_id: UUID, query: str, history: list[HistoryMessage]
    ) -> Decision:
        """Один вызов агента: запрос пользователя -> решение агента."""
        return Decision(
            message=(
                f"[stub] Принял запрос: «{query}». Здесь будет ответ text2sql-агента."
            ),
            type=DecisionType.answer,
        )

    async def stream(
        self, *, chat_id: UUID, query: str, history: list[HistoryMessage]
    ) -> AsyncIterator[str]:
        """Стриминговая версия run(): отдаёт decision.message по токенам.

        Примечание к спеке: отдельный метод в интерфейсе необходим —
        из обычного run() поток токенов не получить. У реального
        LangGraph-агента здесь будет astream_events / astream.
        """
        decision = await self.run(chat_id=chat_id, query=query, history=history)
        # Режем так, чтобы конкатенация токенов давала исходную строку
        for token in re.findall(r"\S+\s*", decision.message):
            yield token
