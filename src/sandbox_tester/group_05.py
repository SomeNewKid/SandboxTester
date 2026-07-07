"""Group 05: Environment variables and secrets exposure."""

from __future__ import annotations

import asyncio
import os
import subprocess

from .group_29 import G29_T01
from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G05_T01:
    id = "T01"
    title = "List environment variable names"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                names = self._summarize_environment_names(completed.stdout)
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed environment variable names.",
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
                summary="Python runtime listed environment variable names.",
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


class G05_T04:
    id = "T04"
    title = "Read path/search-path variable"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the path/search-path environment variable.",
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
            path_variable_name = "Path"
            if self._operating_system == OperatingSystem.LINUX:
                path_variable_name = "PATH"

            path_variable = os.environ.get(path_variable_name)
            if path_variable is None:
                return InvocationResult(
                    outcome=Outcome.DENIED,
                    summary="Path/search-path environment variable was not present.",
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read the path/search-path variable.",
                evidence=path_variable[:500],
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
                "[Environment]::GetEnvironmentVariable('Path', 'Process')",
            ]
        else:
            command = ["sh", "-c", "printf '%s' \"$PATH\""]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G05",
        title="Environment variables and secrets exposure",
        tests=[
            G05_T01(capability_context),
            G05_T04(capability_context),
            G29_T01(capability_context),
        ],
    )
