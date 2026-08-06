from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agent.service import TextToSqlAgentService
from app.context import get_person_id
from app.db import get_session
from app.deps import get_agent_service
from app.models import ChatMessage
from app.schemas import (
    ChatRequest,
    ChatResponse,
    Decision,
    DecisionType,
    HistoryMessage,
    MessageType,
)

router = APIRouter(tags=["chat"])

# Бизнес-заглушка: реальная ошибка уходит в decision.error_message,
# пользователь видит нейтральный текст (см. ТЗ).
BUSY_MESSAGE = "Давай позже, пока занят."


async def _load_history(session: AsyncSession, chat_id: UUID) -> list[HistoryMessage]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.id)
    )
    return [
        HistoryMessage(
            message_id=row.message_id,
            message=row.message,
            type=MessageType(row.type),
        )
        for row in result.scalars()
    ]


def _save_message(
    session: AsyncSession,
    *,
    chat_id: UUID,
    person_id: UUID,
    message: str,
    type_: MessageType,
) -> UUID:
    message_id = uuid4()
    session.add(
        ChatMessage(
            message_id=message_id,
            chat_id=chat_id,
            person_id=person_id,
            message=message,
            type=type_.value,
        )
    )
    return message_id


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
    agent: TextToSqlAgentService = Depends(get_agent_service),
) -> ChatResponse:
    person_id = get_person_id()
    history = await _load_history(session, body.chat_id)

    try:
        decision = await agent.run(
            chat_id=body.chat_id, query=body.query, history=history
        )
    except Exception as exc:  # noqa: BLE001 — намеренно глотаем всё (см. ТЗ)
        decision = Decision(
            message=BUSY_MESSAGE,
            type=DecisionType.error,
            error_message=f"{type(exc).__name__}: {exc}",
        )

    _save_message(
        session,
        chat_id=body.chat_id,
        person_id=person_id,
        message=body.query,
        type_=MessageType.human,
    )
    agent_message_id = _save_message(
        session,
        chat_id=body.chat_id,
        person_id=person_id,
        message=decision.message,
        type_=MessageType.agent,
    )
    await session.commit()

    return ChatResponse(
        chat_id=body.chat_id, message_id=agent_message_id, decision=decision
    )


@router.post("/chat/sse")
async def chat_sse(
    body: ChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    agent: TextToSqlAgentService = Depends(get_agent_service),
) -> EventSourceResponse:
    person_id = get_person_id()
    history = await _load_history(session, body.chat_id)

    async def event_generator():
        collected: list[str] = []
        decision_type = DecisionType.answer
        error_message: str | None = None
        disconnected = False
        try:
            async for token in agent.stream(
                chat_id=body.chat_id, query=body.query, history=history
            ):
                # Клиент закрыл соединение — прекращаем генерацию (не жжём
                # токены LLM впустую), но диалог ниже всё равно персистим.
                if await request.is_disconnected():
                    disconnected = True
                    break
                collected.append(token)
                yield {"data": token}
        except Exception as exc:  # noqa: BLE001 — та же семантика, что у /chat
            collected = [BUSY_MESSAGE]
            decision_type = DecisionType.error
            error_message = f"{type(exc).__name__}: {exc}"
            yield {"data": BUSY_MESSAGE}

        # Персистим диалог после завершения стрима — той же сессией,
        # FastAPI закрывает yield-зависимости после отправки ответа.
        full_message = "".join(collected)
        _save_message(
            session,
            chat_id=body.chat_id,
            person_id=person_id,
            message=body.query,
            type_=MessageType.human,
        )
        agent_message_id = _save_message(
            session,
            chat_id=body.chat_id,
            person_id=person_id,
            message=full_message,
            type_=MessageType.agent,
        )
        await session.commit()

        # Клиент отключился: событие decision отправлять некому.
        # В истории остаётся частичный ответ — то, что клиент успел увидеть.
        if disconnected:
            return

        # Финальный именованный event с полным Decision и message_id —
        # по нему клиент может выставить оценку через /feedback.
        # Токены выше идут безымянными message-событиями, поэтому
        # существующие SSE-клиенты (onmessage) ничего не заметят.
        final = ChatResponse(
            chat_id=body.chat_id,
            message_id=agent_message_id,
            decision=Decision(
                message=full_message,
                type=decision_type,
                error_message=error_message,
            ),
        )
        yield {"event": "decision", "data": final.model_dump_json()}

    return EventSourceResponse(event_generator())
