import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_active_user, get_db
from app.main import app
from app.models.auth import UserInToken

TEST_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TEST_USER = UserInToken(id=TEST_USER_ID, email="tester@example.com")


@pytest.fixture
def mock_user() -> UserInToken:
    return TEST_USER


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    return db


@pytest.fixture
async def client(mock_db, mock_user):
    """Async test client with overridden auth and db dependencies."""
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def unauthenticated_client():
    """Async test client without mocked auth for testing public endpoints."""
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
