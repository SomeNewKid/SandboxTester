"""Group 01: Runtime identity and execution context."""

from __future__ import annotations

import asyncio
import getpass
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G01_T01:
    id = "T01"
    title = "Identify current working directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                current_directory = completed.stdout.strip()
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the current working directory.",
                    evidence=current_directory,
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
            current_directory = Path.cwd()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python filesystem API identified the current working directory."
                ),
                evidence=str(current_directory),
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
            command = ["cmd", "/c", "cd"]
        else:
            command = ["pwd"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T02:
    id = "T02"
    title = "Identify current user/account name"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the current user/account name.",
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
            username = getpass.getuser()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the current user/account name.",
                evidence=username,
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
            command = ["whoami"]
        else:
            command = ["id", "-un"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T03:
    id = "T03"
    title = "Identify process ID"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified a process ID for its invocation.",
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

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the current process ID.",
                evidence=str(process_id),
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
            command = ["powershell", "-NoProfile", "-Command", "$PID"]
        else:
            command = ["sh", "-c", "echo $$"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T04:
    id = "T04"
    title = "Identify operating system family"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the operating system family.",
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
            system_name = platform.system()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the operating system family.",
                evidence=system_name,
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
            command = ["cmd", "/c", "ver"]
        else:
            command = ["uname", "-s"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T05:
    id = "T05"
    title = "Identify CPU architecture"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the CPU architecture.",
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
            architecture = platform.machine()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the CPU architecture.",
                evidence=architecture,
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
            command = ["cmd", "/c", "echo", "%PROCESSOR_ARCHITECTURE%"]
        else:
            command = ["uname", "-m"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T06:
    id = "T06"
    title = "Identify hostname or machine name"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell identified the hostname or machine name.",
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
            hostname = socket.gethostname()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime identified the hostname or machine name.",
                evidence=hostname,
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
        command = ["hostname"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T07:
    id = "T07"
    title = "Identify container/VM indicators"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                evidence = completed.stdout.strip()
                if not evidence:
                    evidence = "No common container/VM indicators found."

                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell checked for common container/VM indicators.",
                    evidence=evidence[:500],
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
            indicators: list[str] = []

            if Path("/.dockerenv").exists():
                indicators.append("/.dockerenv exists")
            if os.environ.get("container"):
                indicators.append("container environment variable is set")
            if os.environ.get("KUBERNETES_SERVICE_HOST"):
                indicators.append("KUBERNETES_SERVICE_HOST is set")
            if os.environ.get("WSL_INTEROP"):
                indicators.append("WSL_INTEROP is set")

            evidence = ", ".join(indicators)
            if not evidence:
                evidence = "No common container/VM indicators found."

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime checked for common container/VM indicators.",
                evidence=evidence,
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
                (
                    "$items = @(); "
                    "if ($env:container) { $items += 'container env var is set' }; "
                    "if ($env:KUBERNETES_SERVICE_HOST) { "
                    "$items += 'KUBERNETES_SERVICE_HOST is set' }; "
                    "if ($env:WSL_INTEROP) { $items += 'WSL_INTEROP is set' }; "
                    "$items -join ', '"
                ),
            ]
        else:
            command = [
                "sh",
                "-c",
                (
                    "items=''; "
                    '[ -f /.dockerenv ] && items="$items/.dockerenv exists, "; '
                    '[ -n "$container" ] && '
                    'items="$items container env var is set, "; '
                    '[ -n "$KUBERNETES_SERVICE_HOST" ] && '
                    'items="$items KUBERNETES_SERVICE_HOST is set, "; '
                    "printf '%s' \"$items\""
                ),
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T08:
    id = "T08"
    title = "Read command-line arguments"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read command-line arguments for its invocation.",
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
            command_line_arguments = " ".join(sys.argv)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read its command-line arguments.",
                evidence=command_line_arguments[:500],
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
                "[Environment]::CommandLine",
            ]
        else:
            command = ["sh", "-c", "tr '\\0' ' ' < /proc/$$/cmdline"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G01_T09:
    id = "T09"
    title = "Read process environment summary"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                names = self._summarize_environment_names(completed.stdout)
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read a summary of process environment names.",
                    evidence=names,
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
            environment_names = sorted(os.environ)
            displayed_names = ", ".join(environment_names[:20])
            evidence = f"count={len(environment_names)}; names={displayed_names}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read a summary of process environment names.",
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
                "Get-ChildItem Env: | Select-Object -ExpandProperty Name",
            ]
        else:
            command = ["sh", "-c", "env | cut -d= -f1"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _summarize_environment_names(self, output: str) -> str:
        environment_names = sorted(
            line.strip() for line in output.splitlines() if line.strip()
        )
        displayed_names = ", ".join(environment_names[:20])
        return f"count={len(environment_names)}; names={displayed_names}"[:500]


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G01",
        title="Runtime identity and execution context",
        tests=[
            G01_T01(capability_context),
            G01_T02(capability_context),
            G01_T03(capability_context),
            G01_T04(capability_context),
            G01_T05(capability_context),
            G01_T06(capability_context),
            G01_T07(capability_context),
            G01_T08(capability_context),
            G01_T09(capability_context),
        ],
    )
