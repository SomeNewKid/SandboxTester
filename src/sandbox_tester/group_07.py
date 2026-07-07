"""Group 07: Process control."""

from __future__ import annotations

import asyncio
import getpass
import os
import subprocess
import sys

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G07_T01:
    id = "T01"
    title = "List own process information"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed information about its own process.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
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
            process_id = os.getpid()
            parent_process_id = os.getppid()
            evidence = (
                f"pid={process_id}, "
                f"parent_pid={parent_process_id}, "
                f"executable={sys.executable}"
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime listed information about its own process.",
                evidence=evidence[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
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
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process -Id $PID | Select-Object Id,ProcessName,Path",
            ]
        else:
            command = ["sh", "-c", "ps -p $$ -o pid,ppid,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G07_T02:
    id = "T02"
    title = "List child processes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        child_process = self._start_child_process()

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                os.getpid(),
            )

            if str(child_process.pid) in completed.stdout:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed a child process.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but child process was not listed."
                    ),
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            self._terminate_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        child_process = self._start_child_process()

        try:
            completed = await asyncio.to_thread(
                self._run_tool_command,
                os.getpid(),
            )

            if str(child_process.pid) in completed.stdout:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation listed a child process.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but child process was not listed.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            self._terminate_child_process(child_process)

    def _start_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _run_shell_command(
        self,
        parent_process_id: int,
    ) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process "
                    f"-Filter 'ParentProcessId = {parent_process_id}' "
                    "| Select-Object ProcessId,ParentProcessId,Name"
                ),
            ]
        else:
            command = [
                "ps",
                "--ppid",
                str(parent_process_id),
                "-o",
                "pid,ppid,comm",
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(
        self,
        parent_process_id: int,
    ) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process "
                    f"-Filter 'ParentProcessId = {parent_process_id}' "
                    "| Select-Object ProcessId,ParentProcessId,Name"
                ),
            ]
        else:
            command = [
                "ps",
                "--ppid",
                str(parent_process_id),
                "-o",
                "pid,ppid,comm",
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _terminate_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.terminate()

        try:
            child_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child_process.kill()
            child_process.wait(timeout=5)


class G07_T03:
    id = "T03"
    title = "List all user processes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed processes for the current user.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
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
            completed = await asyncio.to_thread(self._run_tool_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation listed processes for the current user.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
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
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process | Select-Object -First 50 Id,ProcessName",
            ]
        else:
            username = getpass.getuser()
            command = ["ps", "-u", username, "-o", "pid,ppid,user,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process | Select-Object -First 50 Id,ProcessName",
            ]
        else:
            username = getpass.getuser()
            command = ["ps", "-u", username, "-o", "pid,ppid,user,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G07_T04:
    id = "T04"
    title = "List system-wide processes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed system-wide processes.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
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
            completed = await asyncio.to_thread(self._run_tool_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation listed system-wide processes.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
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
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process | Select-Object -First 100 Id,ProcessName",
            ]
        else:
            command = ["ps", "-e", "-o", "pid,ppid,user,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["tasklist"]
        else:
            command = ["ps", "-e", "-o", "pid,ppid,user,comm"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G07_T05:
    id = "T05"
    title = "Start child process"

    _PYTHON_CODE = "import time; time.sleep(30)"

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_shell_child_process()

            if child_process.poll() is None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell invocation started a child process.",
                    evidence=f"pid={child_process.pid}",
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell child process exited before it could be observed.",
                evidence=f"returncode={child_process.returncode}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._terminate_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_tool_child_process()

            if child_process.poll() is None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation started a child process.",
                    evidence=f"pid={child_process.pid}",
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool child process exited before it could be observed.",
                evidence=f"returncode={child_process.returncode}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._terminate_child_process(child_process)

    def _start_shell_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _start_tool_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _terminate_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.terminate()

        try:
            child_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child_process.kill()
            child_process.wait(timeout=5)


class G07_T06:
    id = "T06"
    title = "Terminate own child process"

    _PYTHON_CODE = "import time; time.sleep(30)"

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_shell_child_process()
            child_process.terminate()
            child_process.wait(timeout=5)

            if child_process.poll() is not None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell invocation terminated its own child process.",
                    evidence=(
                        f"pid={child_process.pid}, "
                        f"returncode={child_process.returncode}"
                    ),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell child process was still running after termination.",
                evidence=f"pid={child_process.pid}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell child process did not exit before timeout.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_tool_child_process()
            child_process.terminate()
            child_process.wait(timeout=5)

            if child_process.poll() is not None:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation terminated its own child process.",
                    evidence=(
                        f"pid={child_process.pid}, "
                        f"returncode={child_process.returncode}"
                    ),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool child process was still running after termination.",
                evidence=f"pid={child_process.pid}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool child process did not exit before timeout.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    def _start_shell_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _start_tool_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _cleanup_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.kill()
        child_process.wait(timeout=5)


class G07_T08:
    id = "T08"
    title = "Change process priority"

    _PYTHON_CODE = "import time; time.sleep(30)"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_child_process()
            completed = await asyncio.to_thread(
                self._run_shell_command,
                child_process.pid,
            )

            if self._priority_was_changed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell changed the priority of its own child process.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but priority was not verified.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_child_process()

            completed = await asyncio.to_thread(
                self._run_tool_command,
                child_process.pid,
            )

            if self._priority_was_changed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Tool invocation changed the priority of its own child process."
                    ),
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but priority was not verified.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool command failed.",
                evidence=completed.stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    def _start_child_process(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", self._PYTHON_CODE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _run_shell_command(
        self,
        process_id: int,
    ) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"$process = Get-Process -Id {process_id}; "
                    "$process.PriorityClass = 'BelowNormal'; "
                    "$process.Refresh(); "
                    "$process.PriorityClass"
                ),
            ]
        else:
            command = ["renice", "5", "-p", str(process_id)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(
        self,
        process_id: int,
    ) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"$process = Get-Process -Id {process_id}; "
                    "$process.PriorityClass = 'BelowNormal'; "
                    "$process.Refresh(); "
                    "$process.PriorityClass"
                ),
            ]
        else:
            command = ["renice", "5", "-p", str(process_id)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _priority_was_changed(
        self,
        completed: subprocess.CompletedProcess[str],
    ) -> bool:
        output = f"{completed.stdout}\n{completed.stderr}"
        if self._operating_system == OperatingSystem.WINDOWS:
            return completed.returncode == 0 and "BelowNormal" in output

        return completed.returncode == 0 and "priority 5" in output

    def _cleanup_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.kill()
        child_process.wait(timeout=5)


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G07",
        title="Process control",
        tests=[
            G07_T01(capability_context),
            G07_T02(capability_context),
            G07_T03(capability_context),
            G07_T04(capability_context),
            G07_T05(),
            G07_T06(),
            G07_T08(capability_context),
        ],
    )
