"""Group 04: Filesystem persistence."""

from __future__ import annotations

import asyncio
import shutil
import subprocess

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G04_T08:
    id = "T08"
    title = "Detect available disk space"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._working_directory = capability_context.working_directory

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected available disk space.",
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
            disk_usage = shutil.disk_usage(self._working_directory)
            evidence = (
                f"total={disk_usage.total}, "
                f"used={disk_usage.used}, "
                f"free={disk_usage.free}"
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected available disk space.",
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
            drive_name = self._working_directory.drive.rstrip(":")
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"Get-PSDrive -Name '{drive_name}' | "
                    "Select-Object Name,Used,Free | Format-List"
                ),
            ]
        else:
            command = ["df", "-k", str(self._working_directory)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G04",
        title="Filesystem persistence",
        tests=[
            G04_T08(capability_context),
        ],
    )
