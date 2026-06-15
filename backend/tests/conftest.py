import pytest
import os
import kuzu
from backend import database
from backend.main import app
from backend.services.db_janitor import temp_db_dir, sweep_stale_tmp
from fastapi.testclient import TestClient


def pytest_configure(config):
    """Register custom markers used by Phase 5 tests."""
    config.addinivalue_line(
        "markers",
        "live: marks tests that hit a real network or Selenium; "
        "opt-in via RUN_LIVE_AGENT_TESTS=1",
    )


def pytest_sessionfinish(session, exitstatus):
    """§R.9 — retention sweep at session end: collect stale one-off DB
    dirs from earlier runs (canonical + legacy prefixes, >24h old)."""
    try:
        sweep_stale_tmp(max_age_hours=24.0)
    except Exception:
        pass


class _LiveConnProxy:
    """Delegates to the CURRENT ``backend.database`` connection, reopening
    it lazily if something closed it mid-session.

    Test-isolation fix: the FastAPI app lifespan's ``finally`` calls
    ``close_db()`` when a ``TestClient`` context exits (test_api_endpoints),
    which closed the session-scoped connection object earlier fixtures had
    already handed to tests — every later DB test then failed with a
    closed-connection RuntimeError, but only under full-suite ordering.
    Yielding this proxy instead of the raw connection makes every consumer
    track the live handle transparently.
    """

    def __getattr__(self, name):
        if database.conn is None:
            database.db = kuzu.Database(database.DB_PATH)
            database.conn = kuzu.Connection(database.db)
        return getattr(database.conn, name)


@pytest.fixture(scope="session")
def temp_kuzu_db():
    # §R.9 — the janitor owns the throwaway dir's full lifetime (the old
    # bare mkdtemp removed only the `db` subdir and leaked its parent).
    with temp_db_dir("conftest_session") as temp_dir:
        test_db_path = os.path.abspath(os.path.join(temp_dir, "db"))

        # Overwrite the global path in backend.database
        database.DB_PATH = test_db_path
        database.db = kuzu.Database(test_db_path)
        database.conn = kuzu.Connection(database.db)

        # Initialize schema
        database.init_db()

        yield _LiveConnProxy()

        # Teardown — drop handles so the janitor's rmtree wins first try.
        database.conn = None
        database.db = None

@pytest.fixture
def clean_db(temp_kuzu_db):
    """Ensure DB is clean before a test by wiping existing DomNodes"""
    try:
        temp_kuzu_db.execute("MATCH (n:DomNode) DETACH DELETE n;")
    except RuntimeError:
        pass
    yield temp_kuzu_db

@pytest.fixture(scope="module")
def client():
    # We yield the TestClient for API endpoints testing
    with TestClient(app) as c:
        yield c
