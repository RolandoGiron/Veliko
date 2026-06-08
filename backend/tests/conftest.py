import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base, get_session
from app.main import app


def _load_models() -> None:
    """Import every model module that exists so Base.metadata is fully populated
    before create_all. Done lazily (inside the db fixture) so pure-logic unit
    tests collect before these modules exist; modules not yet created in earlier
    plan tasks are skipped (find_spec), while real import errors still surface."""
    import importlib
    import importlib.util

    for mod in ("app.auth.models", "app.constructor.models", "app.coherence.models"):
        try:
            found = importlib.util.find_spec(mod) is not None
        except ModuleNotFoundError:
            found = False  # parent package not created yet (earlier plan task)
        if found:
            importlib.import_module(mod)


@pytest_asyncio.fixture
async def db_session():
    _load_models()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
