from __future__ import annotations

import pytest

from app.database import DatabaseNotInitializedError, connect, database_path


def test_connect_raises_when_file_missing(monkeypatch, tmp_path):
    missing = tmp_path / "nope.db"
    monkeypatch.setenv("DATABASE_PATH", str(missing))
    assert not missing.is_file()
    with pytest.raises(DatabaseNotInitializedError) as exc:
        connect()
    assert "python -m db" in str(exc.value).lower() or "python -m db" in str(exc.value)


def test_database_path_respects_env(monkeypatch, tmp_path):
    p = tmp_path / "custom.db"
    monkeypatch.setenv("DATABASE_PATH", str(p))
    assert database_path() == p
