from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.context import get_person_id
from app.deps import SessionDep
from app.models import ChatMessage, Feedback
from app.schemas import (
    FeedbackListResponse,
    FeedbackRequest,
    MessageType,
    RatedMessage,
)

router = APIRouter(tags=["feedback"])


@router.post("/feedback")
async def set_feedback(
    body: FeedbackRequest,
    session: SessionDep,
) -> dict:
    # Оценивать можно только существующее сообщение, и только ответ агента
    chat_message = await session.scalar(
        select(ChatMessage).where(ChatMessage.message_id == body.message_id).limit(1)
    )
    if chat_message is None or chat_message.type != MessageType.agent.value:
        raise HTTPException(status_code=404, detail="Agent message not found")

    # Повторная оценка того же сообщения перезаписывает рейтинг
    feedback = await session.scalar(
        select(Feedback).where(Feedback.message_id == body.message_id).limit(1)
    )
    if feedback is None:
        feedback = Feedback(
            chat_id=chat_message.chat_id,
            person_id=get_person_id(),
            message_id=body.message_id,
            rating=body.rating,
        )
        session.add(feedback)
    else:
        feedback.rating = body.rating
    await session.commit()

    return {"status": "ok"}


@router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedback(
    chat_id: UUID,
    session: SessionDep,
) -> FeedbackListResponse:
    result = await session.execute(
        select(Feedback).where(Feedback.chat_id == chat_id).order_by(Feedback.id)
    )
    return FeedbackListResponse(
        chat_history=[
            RatedMessage(message_id=row.message_id, rating=row.rating)
            for row in result.scalars()
        ]
    )
