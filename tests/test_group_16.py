"""Tests for database capability probes."""

from pathlib import Path

import pytest

from sandbox_tester.group_16 import _delete_temporary_sqlite_database


def test_sqlite_cleanup_ignores_read_only_filesystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SQLite probe cleanup should not turn denied access into a fatal error."""

    def raise_read_only_error(self: Path, missing_ok: bool = False) -> None:
        raise OSError(30, "Read-only file system", str(self))

    monkeypatch.setattr(Path, "unlink", raise_read_only_error)

    _delete_temporary_sqlite_database(Path("/sandbox-denied/test.db"))
