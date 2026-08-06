from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    error = "error"
    answer = "answer"
    request = "request"  # агент запрашивает уточнение у пользователя


class MessageType(str, Enum):
    agent = "agent"
    human = "human"


class Decision(BaseModel):
    message: str
    type: DecisionType
    error_message: str | None = None


class ChatRequest(BaseModel):
    chat_id: UUID
    query: str = Field(min_length=1)


class ChatResponse(BaseModel):
    chat_id: UUID
    # ID сообщения-ответа агента — по нему выставляется оценка в /feedback
    message_id: UUID
    decision: Decision


class HistoryRequest(BaseModel):
    chat_id: UUID


class HistoryMessage(BaseModel):
    message_id: UUID
    message: str
    type: MessageType


class HistoryResponse(BaseModel):
    chat_id: UUID
    chat_history: list[HistoryMessage]


class FeedbackRequest(BaseModel):
    message_id: UUID
    rating: int = Field(ge=1, le=5)


class RatedMessage(BaseModel):
    message_id: UUID
    rating: int


class FeedbackListResponse(BaseModel):
    chat_history: list[RatedMessage]


class EnrichResponse(BaseModel):
    source: str
    entity_id: str
    # Форму data определяет конкретный источник, поэтому она нетипизирована
    data: dict
