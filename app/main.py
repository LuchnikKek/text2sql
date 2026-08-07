from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.security import HTTPBearer

from app.agent.service import TextToSqlAgentService
from app.auth import AuthMiddleware
from app.clients import aclose_all
from app.clients.semantic_layer import SemanticLayerClient
from app.config import Settings
from app.db import build_engine, build_sessionmaker
from app.models import Base
from app.routers import chat, debug, enrich, feedback, history


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    engine = build_engine(settings.database_url)
    sessionmaker = build_sessionmaker(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Для учебного проекта хватает create_all;
        # в проде здесь были бы миграции (alembic upgrade head).
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()
        # Клиенты внешних API — модульные синглтоны, закрываем их здесь.
        await aclose_all()

    app = FastAPI(title="text2sql-agent-api", lifespan=lifespan)

    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.agent_service = TextToSqlAgentService()
    app.state.semantic_layer_client = SemanticLayerClient()

    app.add_middleware(
        AuthMiddleware, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    # Документационная security-схема: реальную проверку токена делает
    # AuthMiddleware (он отвечает 401 раньше, чем запрос дойдёт сюда),
    # а HTTPBearer(auto_error=False) лишь объявляет требование в OpenAPI —
    # благодаря ему в Swagger UI (/docs) появляется кнопка Authorize.
    bearer_scheme = HTTPBearer(
        auto_error=False,
        description="JWT (HS256) с клеймом person_id, например eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsInBlcnNvbl9pZCI6ImU4MjZlOTQzLTAyNmItNDJkYS1iYWI1LTE4ZGFjNWUzNDkwYiIsImlhdCI6MTUxNjIzOTAyMn0.LCRUVmG23ZWNWRNTd0EBaWrdM0ahT_fcJto0HckMtcw",
    )

    api = "/api/v1"
    secured = [Depends(bearer_scheme)]
    app.include_router(chat.router, prefix=api, dependencies=secured)
    app.include_router(history.router, prefix=api, dependencies=secured)
    app.include_router(feedback.router, prefix=api, dependencies=secured)
    app.include_router(enrich.router, prefix=api, dependencies=secured)
    app.include_router(debug.router, prefix=api, dependencies=secured)

    @app.get("/health", tags=["ops"])
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
