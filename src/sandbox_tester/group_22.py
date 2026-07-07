"""Group 22: Logging, telemetry, and audit visibility."""

from __future__ import annotations

import asyncio
import datetime as dt
import subprocess
import uuid
from pathlib import Path

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_NO_SHELL_CANDIDATE_EXIT_CODE = 127
_APPLICATION_LOG_FILE_NAME = "sandbox-tester.log"
_WINDOWS_EVENT_LOG_DIRECTORY = Path("C:/Windows/System32/winevt/Logs")
_LINUX_SYSTEM_LOG_CANDIDATES = [
    Path("/var/log/syslog"),
    Path("/var/log/messages"),
]
_LINUX_SECURITY_LOG_CANDIDATES = [
    Path("/var/log/auth.log"),
    Path("/var/log/secure"),
]


class G22_T01:
    id = "T01"
    title = "Write application log entry"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        log_file = self._allowed_directory / _APPLICATION_LOG_FILE_NAME

        try:
            completed = await asyncio.to_thread(
                _write_application_log_entry_with_shell,
                self._operating_system,
                log_file,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and log_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell wrote an application log entry.",
                    evidence=f"path={log_file}; size={log_file.stat().st_size}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not write an application log entry.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell application log write timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell application log write failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        log_file = self._allowed_directory / _APPLICATION_LOG_FILE_NAME

        try:
            evidence = await asyncio.to_thread(
                _write_application_log_entry_with_tool,
                log_file,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime wrote an application log entry.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime application log write failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G22_T03:
    id = "T03"
    title = "Read system logs"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _read_system_logs_with_shell,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read system logs.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported shell system log source was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read system logs.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell system log query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell system log query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _read_system_logs_with_tool,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read system logs.",
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No supported system log file was available.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime system log query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G22_T04:
    id = "T04"
    title = "Read security logs"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _read_security_logs_with_shell,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read security logs.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported shell security log source was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read security logs.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell security log query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell security log query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _read_security_logs_with_tool,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read security logs.",
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No supported security log file was available.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime security log query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G22",
        title="Logging, telemetry, and audit visibility",
        tests=[
            G22_T01(capability_context),
            G22_T03(capability_context),
            G22_T04(capability_context),
        ],
    )


def _write_application_log_entry_with_shell(
    operating_system: OperatingSystem,
    log_file: Path,
) -> subprocess.CompletedProcess[str]:
    line = _build_log_line("shell")

    if operating_system == OperatingSystem.WINDOWS:
        path = _quote_powershell_string(str(log_file))
        value = _quote_powershell_string(line)
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Add-Content -LiteralPath {path} -Value {value} -Encoding UTF8",
        ]
    else:
        command = [
            "sh",
            "-c",
            'printf \'%s\\n\' "$1" >> "$2"',
            "sandbox-tester",
            line,
            str(log_file),
        ]

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _write_application_log_entry_with_tool(log_file: Path) -> str:
    line = _build_log_line("tool")

    with log_file.open("a", encoding="utf-8") as file:
        file.write(f"{line}\n")

    return f"path={log_file}; size={log_file.stat().st_size}"


def _read_system_logs_with_shell(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = ["wevtutil", "qe", "System", "/c:1", "/f:text", "/rd:true"]
    else:
        command = _build_linux_system_log_command()

    return _run_log_command(command)


def _read_security_logs_with_shell(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = ["wevtutil", "qe", "Security", "/c:1", "/f:text", "/rd:true"]
    else:
        command = _build_linux_security_log_command()

    return _run_log_command(command)


def _run_log_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_linux_system_log_command() -> list[str]:
    script = """
set -u
if command -v journalctl >/dev/null 2>&1; then
    journalctl -n 1 --no-pager
    exit $?
fi
if [ -r /var/log/syslog ]; then
    tail -n 1 /var/log/syslog
    exit $?
fi
if [ -r /var/log/messages ]; then
    tail -n 1 /var/log/messages
    exit $?
fi
exit 127
"""
    return ["sh", "-c", script]


def _build_linux_security_log_command() -> list[str]:
    script = """
set -u
if [ -e /var/log/auth.log ]; then
    tail -n 1 /var/log/auth.log
    exit $?
fi
if [ -e /var/log/secure ]; then
    tail -n 1 /var/log/secure
    exit $?
fi
if command -v journalctl >/dev/null 2>&1; then
    journalctl -n 1 --no-pager SYSLOG_FACILITY=10
    exit $?
fi
exit 127
"""
    return ["sh", "-c", script]


def _read_system_logs_with_tool(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        path = _WINDOWS_EVENT_LOG_DIRECTORY / "System.evtx"
        return _read_binary_log_header(path)

    return _read_text_log_sample(_LINUX_SYSTEM_LOG_CANDIDATES)


def _read_security_logs_with_tool(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        path = _WINDOWS_EVENT_LOG_DIRECTORY / "Security.evtx"
        return _read_binary_log_header(path)

    return _read_text_log_sample(_LINUX_SECURITY_LOG_CANDIDATES)


def _read_binary_log_header(path: Path) -> str:
    with path.open("rb") as file:
        sample = file.read(512)

    return f"path={path}; bytes_read={len(sample)}; size={path.stat().st_size}"


def _read_text_log_sample(paths: list[Path]) -> str:
    for path in paths:
        if path.exists():
            with path.open("r", encoding="utf-8", errors="replace") as file:
                sample = file.readline().strip()

            return f"path={path}; sample={sample[:400]}"

    path_list = ", ".join(str(path) for path in paths)
    raise FileNotFoundError(f"No supported log files found: {path_list}")


def _build_log_line(invocation_kind: str) -> str:
    timestamp = dt.datetime.now().astimezone().isoformat()
    entry_id = uuid.uuid4().hex
    return f"{timestamp} sandbox-tester {invocation_kind} {entry_id}"


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    return f"returncode={completed.returncode}; output={combined_output[:500]}"
