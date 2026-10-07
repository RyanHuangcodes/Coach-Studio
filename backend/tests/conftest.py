"""Test harness: runs the app against a throwaway Postgres database
(coach_studio_test), rebuilt fresh for every test. Requires Postgres running
(e.g. `docker compose up -d db`)."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Cookies must be sendable over the TestClient's http origin.
settings.cookie_secure = False

import app.models  # noqa: F401  (ensure all tables are registered on Base)
from app.database import Base, get_db
from app.main import app
from app.rate_limit import limiter

# Rate limits would trip across a test run (signup is 10/hour); disable them.
limiter.enabled = False

_URL = make_url(settings.database_url)
_TEST_DB = (_URL.database or "coach_studio") + "_test"

_admin = create_engine(_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
with _admin.connect() as conn:
    exists = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": _TEST_DB}
    ).scalar()
    if not exists:
        conn.execute(text(f'CREATE DATABASE "{_TEST_DB}"'))
_admin.dispose()

engine = create_engine(_URL.set(database=_TEST_DB))
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    def _override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)
