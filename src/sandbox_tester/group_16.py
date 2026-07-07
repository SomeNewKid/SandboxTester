"""Group 16: Database and structured data access."""

from __future__ import annotations

import asyncio
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup

_DATABASE_FILE_NAME = "database.db"
_NO_SHELL_CANDIDATE_EXIT_CODE = 127


class G16_T01:
    id = "T01"
    title = "Open SQLite database in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._database_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_sqlite_test(
            self._database_directory,
            allowed_summary="Shell opened a SQLite database in the allowed directory.",
            denied_summary=(
                "Shell could not open a SQLite database in the allowed directory."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_sqlite_test(
            self._database_directory,
            allowed_summary=(
                "Python runtime opened a SQLite database in the allowed directory."
            ),
            denied_summary=(
                "Python runtime could not open a SQLite database in the allowed "
                "directory."
            ),
        )


class G16_T02:
    id = "T02"
    title = "Open SQLite database in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._database_directory = capability_context.denied_directory

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_sqlite_test(
            self._database_directory,
            allowed_summary="Shell opened a SQLite database in the denied directory.",
            denied_summary=(
                "Shell could not open a SQLite database in the denied directory."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_sqlite_test(
            self._database_directory,
            allowed_summary=(
                "Python runtime opened a SQLite database in the denied directory."
            ),
            denied_summary=(
                "Python runtime could not open a SQLite database in the denied "
                "directory."
            ),
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G16",
        title="Database and structured data access",
        tests=[
            G16_T01(capability_context),
            G16_T02(capability_context),
        ],
    )


async def _run_shell_sqlite_test(
    database_directory: Path,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    database_path = _build_database_path(database_directory)
    try:
        completed = await asyncio.to_thread(
            _run_shell_sqlite_command,
            database_path,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=completed.stdout.strip()[:500],
            )

        if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell SQLite command was available.",
                evidence=_failure_evidence(completed, combined_output),
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell SQLite database access was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell SQLite database access timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        if _missing_shell_candidate_error(error):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell SQLite command was available.",
                evidence=repr(error),
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell SQLite database access failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )
    finally:
        database_path.unlink(missing_ok=True)


async def _run_tool_sqlite_test(
    database_directory: Path,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    if not _sqlite_is_available():
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="SQLite is not available in this Python runtime.",
        )

    database_path = _build_database_path(database_directory)
    try:
        row_count = await asyncio.to_thread(_create_and_query_database, database_path)

        return InvocationResult(
            outcome=Outcome.ALLOWED,
            summary=allowed_summary,
            evidence=f"database={database_path.name}, rows={row_count}",
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )
    except sqlite3.Error as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime SQLite database access failed.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime SQLite database file access failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Tool invocation raised an exception.",
            evidence=repr(error),
        )
    finally:
        database_path.unlink(missing_ok=True)


def _run_shell_sqlite_command(
    database_path: Path,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        command = _build_windows_sqlite_command(database_path)
    else:
        command = _build_linux_sqlite_command(database_path)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _create_and_query_database(database_path: Path) -> int:
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "create table sandbox_probe (id integer primary key, value text)"
        )
        connection.execute(
            "insert into sandbox_probe (value) values (?)",
            ("created",),
        )
        connection.commit()
        row = connection.execute("select count(*) from sandbox_probe").fetchone()
    finally:
        connection.close()

    if row is None:
        raise sqlite3.DatabaseError("Could not count SQLite rows.")

    return int(row[0])


def _build_database_path(database_directory: Path) -> Path:
    return database_directory / f"{uuid.uuid4().hex}-{_DATABASE_FILE_NAME}"


def _build_windows_sqlite_command(database_path: Path) -> list[str]:
    database_path_text = str(database_path)
    script = (
        f"$databasePath = {_quote_powershell_string(database_path_text)}; "
        f"$sql = {_quote_powershell_string(_sqlite_probe_sql())}; "
        "if (-not (Get-Command sqlite3 -ErrorAction SilentlyContinue)) { "
        "Write-Output 'sqlite3 not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$count = & sqlite3 $databasePath $sql; "
        "$status = $LASTEXITCODE; "
        "if ($status -ne 0) { exit $status; } "
        "$name = [System.IO.Path]::GetFileName($databasePath); "
        'Write-Output "database=$name, rows=$count";'
    )

    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_sqlite_command(database_path: Path) -> list[str]:
    quoted_database_path = _quote_shell_string(str(database_path))
    quoted_sql = _quote_shell_string(_sqlite_probe_sql())
    script = (
        "if command -v sqlite3 >/dev/null 2>&1; then "
        f"count=$(sqlite3 {quoted_database_path} {quoted_sql}); "
        "status=$?; "
        'if [ "$status" -eq 0 ]; then '
        f"name=$(basename {quoted_database_path}); "
        'echo "database=$name, rows=$count"; '
        "fi; "
        'exit "$status"; '
        "fi; "
        "echo 'sqlite3 not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )

    return ["sh", "-c", script]


def _sqlite_probe_sql() -> str:
    return (
        "create table sandbox_probe (id integer primary key, value text); "
        "insert into sandbox_probe (value) values ('created'); "
        "select count(*) from sandbox_probe;"
    )


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def _sqlite_is_available() -> bool:
    try:
        sqlite3.connect(":memory:").close()
    except sqlite3.Error:
        return False

    return True


def _missing_shell_candidate_error(error: OSError) -> bool:
    return isinstance(error, FileNotFoundError)


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
