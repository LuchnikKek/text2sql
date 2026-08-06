from fastapi import APIRouter
from sqlalchemy import select

from app.deps import SessionDep
from app.models import ChatMessage
from app.schemas import HistoryMessage, HistoryRequest, HistoryResponse, MessageType

router = APIRouter(tags=["history"])


@router.post("/history", response_model=HistoryResponse)
async def get_history(
    body: HistoryRequest,
    session: SessionDep,
) -> HistoryResponse:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == body.chat_id)
        .order_by(ChatMessage.id)
    )
    return HistoryResponse(
        chat_id=body.chat_id,
        chat_history=[
            HistoryMessage(
                message_id=row.message_id,
                message=row.message,
                type=MessageType(row.type),
            )
            for row in result.scalars()
        ],
    )
