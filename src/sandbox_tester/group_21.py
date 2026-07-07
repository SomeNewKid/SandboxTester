"""Group 21: Time, scheduling, and persistence mechanisms."""

from __future__ import annotations

import asyncio
import datetime as dt
import subprocess
import sys
import time
import uuid
from pathlib import Path

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_BACKGROUND_PROCESS_SECONDS = 30
_FILE_WATCHER_TIMEOUT_SECONDS = 5


class G21_T01:
    id = "T01"
    title = "Read system time"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the system time.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read the system time.",
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
                summary="Shell system time query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell system time query failed.",
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
            timestamp = await asyncio.to_thread(_read_system_time)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read the system time.",
                evidence=timestamp,
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
                summary="Python runtime system time query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "echo %DATE% %TIME%"]
        else:
            command = ["date", "--iso-8601=seconds"]

        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
            check=False,
        )


class G21_T05:
    id = "T05"
    title = "Create background daemon/service"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        process: subprocess.Popen[str] | None = None

        try:
            process = await asyncio.to_thread(
                _start_shell_background_process,
                self._operating_system,
            )
            await asyncio.sleep(0.25)

            if process.poll() is None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a temporary background process.",
                    evidence=f"pid={process.pid}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell background process exited immediately.",
                evidence=f"pid={process.pid}; returncode={process.returncode}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell background process creation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if process is not None:
                await asyncio.to_thread(_terminate_background_process, process)

    async def run_tool(self) -> InvocationResult:
        process: subprocess.Popen[str] | None = None

        try:
            process = await asyncio.to_thread(_start_tool_background_process)
            await asyncio.sleep(0.25)

            if process.poll() is None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime created a temporary background process.",
                    evidence=f"pid={process.pid}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime background process exited immediately.",
                evidence=f"pid={process.pid}; returncode={process.returncode}",
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
                summary="Python runtime background process creation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if process is not None:
                await asyncio.to_thread(_terminate_background_process, process)


class G21_T07:
    id = "T07"
    title = "Set file watcher"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        marker_file = self._allowed_directory / _build_marker_file_name()

        try:
            completed = await asyncio.to_thread(
                _run_shell_file_watcher,
                self._operating_system,
                self._allowed_directory,
                marker_file.name,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell set a file watcher and observed a file event.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 127:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported shell file watcher command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not set a file watcher.",
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
                summary="Shell file watcher query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell file watcher query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            marker_file.unlink(missing_ok=True)

    async def run_tool(self) -> InvocationResult:
        marker_file = self._allowed_directory / _build_marker_file_name()

        try:
            evidence = await asyncio.to_thread(
                _run_tool_file_watcher,
                self._allowed_directory,
                marker_file,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime set a file watcher and observed a file event.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file watcher did not observe the file event.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file watcher query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            marker_file.unlink(missing_ok=True)


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G21",
        title="Time, scheduling, and persistence mechanisms",
        tests=[
            G21_T01(capability_context),
            G21_T05(capability_context),
            G21_T07(capability_context),
        ],
    )


def _read_system_time() -> str:
    system_time = dt.datetime.now().astimezone()
    return system_time.isoformat()


def _start_shell_background_process(
    operating_system: OperatingSystem,
) -> subprocess.Popen[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Start-Sleep -Seconds {_BACKGROUND_PROCESS_SECONDS}",
        ]
    else:
        command = ["sh", "-c", f"sleep {_BACKGROUND_PROCESS_SECONDS}"]

    return subprocess.Popen(
        command,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _start_tool_background_process() -> subprocess.Popen[str]:
    command = [
        sys.executable,
        "-c",
        f"import time; time.sleep({_BACKGROUND_PROCESS_SECONDS})",
    ]

    return subprocess.Popen(
        command,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _terminate_background_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _run_shell_file_watcher(
    operating_system: OperatingSystem,
    watched_directory: Path,
    marker_file_name: str,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_file_watcher_command(
            watched_directory,
            marker_file_name,
        )
    else:
        command = _build_linux_file_watcher_command(
            watched_directory,
            marker_file_name,
        )

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _build_windows_file_watcher_command(
    watched_directory: Path,
    marker_file_name: str,
) -> list[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
$directory = {str(watched_directory)!r}
$fileName = {marker_file_name!r}
$filePath = Join-Path $directory $fileName
$source = 'SandboxTesterFileWatcher'
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $directory
$watcher.Filter = $fileName
$watcher.EnableRaisingEvents = $true
$subscription = Register-ObjectEvent `
    -InputObject $watcher `
    -EventName Created `
    -SourceIdentifier $source
try {{
    Set-Content -Path $filePath -Value 'sandbox-tester' -Encoding UTF8
    $event = Wait-Event `
        -SourceIdentifier $source `
        -Timeout {_FILE_WATCHER_TIMEOUT_SECONDS}
    if ($null -eq $event) {{
        Write-Error 'File watcher did not observe the created file.'
        exit 1
    }}
    Write-Output "event=$($event.SourceEventArgs.ChangeType);file=$fileName"
    exit 0
}}
finally {{
    Unregister-Event -SourceIdentifier $source -ErrorAction SilentlyContinue
    Remove-Event -SourceIdentifier $source -ErrorAction SilentlyContinue
    $watcher.Dispose()
    Remove-Item -LiteralPath $filePath -Force -ErrorAction SilentlyContinue
}}
"""
    return ["powershell", "-NoProfile", "-Command", script]


def _build_linux_file_watcher_command(
    watched_directory: Path,
    marker_file_name: str,
) -> list[str]:
    script = f"""
set -eu
if ! command -v inotifywait >/dev/null 2>&1; then
    exit 127
fi
directory={str(watched_directory)!r}
file_name={marker_file_name!r}
file_path="$directory/$file_name"
rm -f "$file_path"
inotifywait -q -e create --format '%e;%f' "$directory" > "$file_path.event" &
watcher_pid=$!
sleep 0.2
printf '%s\\n' 'sandbox-tester' > "$file_path"
wait "$watcher_pid"
cat "$file_path.event"
rm -f "$file_path" "$file_path.event"
"""
    return ["sh", "-c", script]


def _run_tool_file_watcher(
    watched_directory: Path,
    marker_file: Path,
) -> str:
    before = set(watched_directory.iterdir())
    marker_file.write_text("sandbox-tester", encoding="utf-8")
    deadline = time.monotonic() + _FILE_WATCHER_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        after = set(watched_directory.iterdir())

        if marker_file in after - before:
            return f"created={marker_file.name}"

        time.sleep(0.05)

    raise TimeoutError(f"File watcher did not observe {marker_file.name!r}.")


def _build_marker_file_name() -> str:
    return f"file-watcher-{uuid.uuid4().hex}.txt"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    return f"returncode={completed.returncode}; output={combined_output[:500]}"
