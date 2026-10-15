import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = str(Path(__file__).parent.parent.resolve())
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set testing environment variables before importing app
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["JWT_SECRET"] = "test-secret-key-for-unit-tests-12345"
os.environ["OPENAI_API_KEY"] = "sk-test"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash

# Create test in-memory SQLite engine
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

import app.core.database as core_db
core_db.engine = test_engine
core_db.async_session_maker = TestingSessionLocal

@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(autouse=True)
async def override_get_db(db_session):
    async def _get_test_db():
        yield db_session
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        email="regular_user@example.com",
        name="Regular User",
        password_hash=get_password_hash("Password123!"),
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession):
    admin = User(
        email="admin_user@example.com",
        name="Admin User",
        password_hash=get_password_hash("AdminPassword123!"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin

@pytest_asyncio.fixture
async def test_user_2(db_session: AsyncSession):
    user2 = User(
        email="other_user@example.com",
        name="Other User",
        password_hash=get_password_hash("OtherPassword123!"),
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    return user2
