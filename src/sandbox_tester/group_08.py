"""Group 08: Resource limits."""

from __future__ import annotations

import asyncio
import os
import subprocess

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G08_T01:
    id = "T01"
    title = "Query CPU count"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the CPU count.",
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
            cpu_count = os.cpu_count()

            if cpu_count is None:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Python runtime could not determine CPU count.",
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the CPU count.",
                evidence=str(cpu_count),
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
                "[Environment]::ProcessorCount",
            ]
        else:
            command = ["nproc"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G08",
        title="Resource limits",
        tests=[
            G08_T01(capability_context),
        ],
    )
