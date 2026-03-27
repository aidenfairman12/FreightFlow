"""API test infrastructure — TestClient with mocked DB session."""

import pytest
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from api.routes import flows, economics, tracking, supply_chain
from db.session import get_db


def _create_test_app() -> FastAPI:
    """Build a clean test app with just the routers — no lifespan/scheduler."""
    app = FastAPI()
    app.include_router(supply_chain.router, prefix="/supply-chain")
    app.include_router(flows.router, prefix="/flows")
    app.include_router(economics.router, prefix="/economics")
    app.include_router(tracking.router, prefix="/tracking")
    return app


test_app = _create_test_app()


class MockMappingResult:
    """Simulates SQLAlchemy result.mappings() for mock DB queries."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def one(self):
        if len(self._rows) != 1:
            raise Exception(f"Expected 1 row, got {len(self._rows)}")
        return self._rows[0]

    def all(self):
        return self._rows


class MockResult:
    """Simulates SQLAlchemy execute() result."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def mappings(self):
        return MockMappingResult(self._rows)

    def scalar(self):
        if self._rows:
            return list(self._rows[0].values())[0]
        return None

    def one(self):
        if len(self._rows) != 1:
            raise Exception(f"Expected 1 row, got {len(self._rows)}")
        return tuple(self._rows[0].values())

    def first(self):
        return tuple(self._rows[0].values()) if self._rows else None


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession with configurable query results."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MockResult([]))
    session.commit = AsyncMock()
    return session


@pytest.fixture
def client(mock_db):
    """AsyncClient pointing at the test app with DB dependency overridden."""
    async def _override_db():
        return mock_db

    test_app.dependency_overrides[get_db] = _override_db
    yield AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")
    test_app.dependency_overrides.clear()
