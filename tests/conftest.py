import uuid
from collections.abc import AsyncIterator

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
from app.models import Base
from app.schemas import Decision, DecisionType

# >=32 байт — иначе PyJWT ругается InsecureKeyLengthWarning (RFC 7518)
TEST_SECRET = "test-secret-0123456789abcdef-0123456789abcdef"


# --- Фейковые агенты для подмены слоя TextToSqlAgentService ---------------


class EchoAgent:
    """Предсказуемый агент: отвечает фиксированным SQL-подобным текстом."""

    async def run(self, *, chat_id, query, history) -> Decision:
        return Decision(
            message=f"SELECT * FROM employees -- for: {query}",
            type=DecisionType.answer,
        )

    async def stream(self, *, chat_id, query, history) -> AsyncIterator[str]:
        decision = await self.run(chat_id=chat_id, query=query, history=history)
        for i in range(0, len(decision.message), 7):
            yield decision.message[i : i + 7]


class FailingAgent:
    """Агент, падающий с исключением — для проверки проглатывания ошибок."""

    async def run(self, *, chat_id, query, history) -> Decision:
        raise RuntimeError("LLM provider exploded")

    async def stream(self, *, chat_id, query, history) -> AsyncIterator[str]:
        raise RuntimeError("LLM provider exploded")
        yield  # pragma: no cover — делает функцию генератором


# --- Фикстуры --------------------------------------------------------------


@pytest_asyncio.fixture
async def app():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret=TEST_SECRET,
    )
    application = create_app(settings)
    # ASGITransport не запускает lifespan — создаём схему вручную
    async with application.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield application
    await application.state.engine.dispose()


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def person_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def auth_headers(person_id) -> dict[str, str]:
    token = jwt.encode({"person_id": str(person_id)}, TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def chat_id() -> str:
    return str(uuid.uuid4())
