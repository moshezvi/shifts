from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest

from db.bootstrap import init_database


@pytest.fixture(scope="session")
def _test_database_path(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[Path, None, None]:
    """Isolated SQLite file + full bootstrap for API tests."""
    db_dir = tmp_path_factory.mktemp("shifts_test_db")
    path = db_dir / "shifts.db"
    os.environ["DATABASE_PATH"] = str(path)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_database(conn, horizon_days=3)
    conn.close()
    try:
        yield path
    finally:
        os.environ.pop("DATABASE_PATH", None)


@pytest.fixture
def client(_test_database_path: Path):
    """FastAPI app bound to the session test DB (lazy import after env is set)."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
