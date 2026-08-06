import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Публичный идентификатор сообщения — уходит наружу в контрактах API,
    # внутренний автоинкрементный id наружу не светим
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, unique=True, index=True, default=uuid.uuid4
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)  # MessageType: agent | human
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    # Оценка привязана к конкретному сообщению агента по его message_id
    message_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, index=True)
    rating: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
