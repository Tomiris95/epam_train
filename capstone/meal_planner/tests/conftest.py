"""
Shared fixtures for all test modules.

Each test gets its own in-memory SQLite database — fully isolated,
no contamination of the real meal_planner.db.

The MCP server subprocess is prevented from starting via a patch on
_port_in_use (returns True → lifespan skips the Popen call).
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend import models
from backend.main import app


# ─── Per-test isolated database ──────────────────────────────────────────────
# StaticPool forces SQLAlchemy to reuse a single connection for the in-memory
# SQLite DB.  Without it, different connections get different empty databases
# → "no such table" errors.

def _make_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, Session


@pytest.fixture()
def db():
    """Fresh in-memory SQLite session per test."""
    engine, Session = _make_test_db()
    session = Session()
    yield session
    session.close()
    engine.dispose()


# ─── Disable rate limiting for all tests ─────────────────────────────────────
# slowapi sets request.state.view_rate_limit inside _check_request_limit,
# then reads it back after the route handler returns.
# Strategy:
#   1. Mock _check_request_limit (AsyncMock) → no actual rate checking
#   2. Patch State.__getattr__ to return [] for view_rate_limit so
#      the post-route read never raises AttributeError, regardless of
#      which internal slowapi method performs that read.

@pytest.fixture(autouse=True)
def disable_rate_limits(monkeypatch):
    """Bypass slowapi rate checks globally for all tests."""
    from starlette.datastructures import State as _State

    _orig = _State.__getattr__

    def _patched(self, key):
        if key == "view_rate_limit":
            return []
        return _orig(self, key)

    monkeypatch.setattr(_State, "__getattr__", _patched)

    with patch("slowapi.Limiter._check_request_limit", return_value=None):
        yield


# ─── TestClient with test DB injected ────────────────────────────────────────

@pytest.fixture()
def client(db):
    """FastAPI TestClient using the isolated test database."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Prevent MCP server subprocess from launching during lifespan
    with patch("backend.main._port_in_use", return_value=True):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.pop(get_db, None)


# ─── Auth helpers ─────────────────────────────────────────────────────────────

@pytest.fixture()
def auth(client):
    """Register a test user and return Authorization headers."""
    client.post("/auth/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "securepass123",
    })
    resp = client.post("/auth/login", data={
        "username": "testuser",
        "password": "securepass123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth2(client):
    """A second, separate user — used to test ownership isolation."""
    client.post("/auth/register", json={
        "username": "otheruser",
        "email": "other@example.com",
        "password": "otherpass123",
    })
    resp = client.post("/auth/login", data={
        "username": "otheruser",
        "password": "otherpass123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Domain helpers ───────────────────────────────────────────────────────────

@pytest.fixture()
def family(client, auth):
    """A family owned by testuser with one member."""
    resp = client.post("/families/", json={
        "name": "Test Family",
        "members": [{
            "name": "Alice",
            "age": 30,
            "calorie_target": 2000,
            "diet_tags": [],
        }],
    }, headers=auth)
    return resp.json()


@pytest.fixture()
def recipes(db):
    """Three minimal recipes (one per meal type) inserted directly into test DB."""
    created = []
    for meal_type in ("breakfast", "lunch", "dinner"):
        r = models.Recipe(
            name=f"Test {meal_type.capitalize()}",
            meal_type=meal_type,
            base_portion_grams=300.0,
            calories_per_100g=100.0,
            protein_per_100g=10.0,
            fat_per_100g=5.0,
            carbs_per_100g=20.0,
            source="local",
        )
        r.ingredients.append(
            models.RecipeIngredient(name="Water", grams_per_base_portion=200.0)
        )
        r.tags.append(models.RecipeTag(tag="stol5"))
        db.add(r)
        created.append(r)
    db.commit()
    for r in created:
        db.refresh(r)
    return created
