import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.main import app
from app.db.base import Base
from app.db.session import get_db

from app.models.entities import (
    ConversationQuestion,
    GapAnalysisJob,
    GapEvidence,
    KnowledgeGap,
    KnowledgeSuggestion,
)

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres"
    "@localhost:5433/knowledge_gap_miner_test"
)


@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    TestSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()
