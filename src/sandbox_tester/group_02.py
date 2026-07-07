"""Group 02: Basic filesystem read access"""

from __future__ import annotations

import asyncio
import subprocess

from .models import InvocationResult, Outcome
from .testing import (
    ALLOWED_CHILD_DIRECTORY,
    ALLOWED_FILE_NAME,
    DENIED_CHILD_DIRECTORY,
    DENIED_FILE_NAME,
    HIDDEN_FILE_NAME,
    CapabilityContext,
    CapabilityGroup,
    OperatingSystem,
)


class G02_T01:
    id = "T01"
    title = "Read a known file in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._text_file = (
            capability_context.allowed_directory
            / ALLOWED_CHILD_DIRECTORY
            / ALLOWED_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the known allowed test file.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._text_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read the known allowed test file.",
                evidence=content[:500],
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "type", str(self._text_file)]
        else:
            command = ["cat", str(self._text_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T02:
    id = "T02"
    title = "List current directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._working_directory = capability_context.working_directory

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the current directory,",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            entries = list(self._working_directory.iterdir())
            names = [entry.name for entry in entries]

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the current directory.",
                evidence=", ".join(names[:20]),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._working_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T03:
    id = "T03"
    title = "List parent directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._parent_directory = capability_context.working_directory.parent

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the parent directory.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            entries = list(self._parent_directory.iterdir())
            names = [entry.name for entry in entries]

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the parent directory.",
                evidence=", ".join(names[:20]),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._parent_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T04:
    id = "T04"
    title = "Read file metadata in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._text_file = (
            capability_context.allowed_directory
            / ALLOWED_CHILD_DIRECTORY
            / ALLOWED_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read metadata for the known test file.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            metadata = self._text_file.stat()
            evidence = (
                f"size={metadata.st_size}, "
                f"created={metadata.st_ctime}, "
                f"modified={metadata.st_mtime}, "
                f"mode={metadata.st_mode}"
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read metadata for the known test file.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            command = ["cmd", "/c", "dir", str(self._text_file)]
        else:
            command = ["ls", "-l", str(self._text_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T05:
    id = "T05"
    title = "Read hidden/dot files in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._hidden_file = (
            capability_context.allowed_directory
            / ALLOWED_CHILD_DIRECTORY
            / HIDDEN_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the hidden dot file.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._hidden_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read the hidden dot file.",
                evidence=content[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            command = ["cmd", "/c", "type", str(self._hidden_file)]
        else:
            command = ["cat", str(self._hidden_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T06:
    id = "T06"
    title = "Read user home directory listing"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._runtime_user_directory = capability_context.runtime_user_directory

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the runtime user directory.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            entries = list(self._runtime_user_directory.iterdir())
            names = [entry.name for entry in entries]

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the runtime user directory.",
                evidence=", ".join(names[:20]),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._runtime_user_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T07:
    id = "T07"
    title = "Read application config directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._config_file = capability_context.working_directory / "pyproject.toml"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the project application configuration file.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._config_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python filesystem API read the project application "
                    "configuration file."
                ),
                evidence=content[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            command = ["cmd", "/c", "type", str(self._config_file)]
        else:
            command = ["cat", str(self._config_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T08:
    id = "T08"
    title = "Read temporary directory listing"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._runtime_temp_directory = capability_context.runtime_temp_directory

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the runtime temporary directory.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            entries = list(self._runtime_temp_directory.iterdir())
            names = [entry.name for entry in entries]

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the runtime temporary directory.",
                evidence=", ".join(names[:20]),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._runtime_temp_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T09:
    id = "T09"
    title = "Read mounted/shared directory listing"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._mounted_shared_directory = capability_context.mounted_shared_directory

    async def run_shell(self) -> InvocationResult:
        if self._mounted_shared_directory is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No mounted/shared directory was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed the mounted/shared directory.",
                    evidence=completed.stdout[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell command failed.",
                evidence=completed.stderr[:500],
            )

        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._mounted_shared_directory is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No mounted/shared directory was configured.",
            )

        try:
            entries = list(self._mounted_shared_directory.iterdir())
            names = [entry.name for entry in entries]

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API listed the mounted/shared directory.",
                evidence=", ".join(names[:20]),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._mounted_shared_directory is None:
            raise RuntimeError("No mounted/shared directory was configured.")

        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "dir"]
        else:
            command = ["ls"]
        return subprocess.run(
            command,
            cwd=self._mounted_shared_directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T10:
    id = "T10"
    title = "Read a known file in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._text_file = (
            capability_context.denied_directory
            / DENIED_CHILD_DIRECTORY
            / DENIED_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the known denied test file.",
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
                summary="Shell invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._text_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read the known denied test file.",
                evidence=content[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            command = ["cmd", "/c", "type", str(self._text_file)]
        else:
            command = ["cat", str(self._text_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T11:
    id = "T11"
    title = "Read file metadata in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._text_file = (
            capability_context.denied_directory
            / DENIED_CHILD_DIRECTORY
            / DENIED_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read metadata for the known denied test file.",
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
                summary="Shell invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            metadata = self._text_file.stat()
            evidence = (
                f"size={metadata.st_size}, "
                f"created={metadata.st_ctime}, "
                f"modified={metadata.st_mtime}, "
                f"mode={metadata.st_mode}"
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read metadata for the denied test file.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            command = ["cmd", "/c", "dir", str(self._text_file)]
        else:
            command = ["ls", "-l", str(self._text_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G02_T12:
    id = "T12"
    title = "Read hidden/dot files in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._hidden_file = (
            capability_context.denied_directory
            / DENIED_CHILD_DIRECTORY
            / HIDDEN_FILE_NAME
        )

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the hidden dot file in the denied directory.",
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
                summary="Shell invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            content = self._hidden_file.read_text(encoding="utf-8")

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python filesystem API read the denied directory hidden file.",
                evidence=content[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
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
            command = ["cmd", "/c", "type", str(self._hidden_file)]
        else:
            command = ["cat", str(self._hidden_file)]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G02",
        title="Basic filesystem read access",
        tests=[
            G02_T01(capability_context),
            G02_T02(capability_context),
            G02_T03(capability_context),
            G02_T04(capability_context),
            G02_T05(capability_context),
            G02_T06(capability_context),
            G02_T07(capability_context),
            G02_T08(capability_context),
            G02_T09(capability_context),
            G02_T10(capability_context),
            G02_T11(capability_context),
            G02_T12(capability_context),
        ],
    )
