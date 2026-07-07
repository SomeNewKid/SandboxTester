"""Group 03: Filesystem write and modification access."""

from __future__ import annotations

import asyncio
import stat
import subprocess
from pathlib import Path

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G03_T01:
    id = "T01"
    title = "Create temporary file in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t01_shell.tmp"
        self._tool_file = capability_context.allowed_directory / "g03_t01_tool.tmp"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a temporary file.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the temporary file was not "
                        "created."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.touch(exist_ok=False)

            if self._tool_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API created a temporary file.",
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the temporary file was not created."
                ),
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
            command = ["cmd", "/c", "type", "nul", ">", str(self._shell_file)]
        else:
            command = ["touch", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._allowed_parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    @property
    def _allowed_parent(self) -> Path:
        return self._shell_file.parent


class G03_T02:
    id = "T02"
    title = "Write content to temporary file in allowed directory"

    _CONTENT = "This content was written by the sandbox tester."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t02_shell.txt"
        self._tool_file = capability_context.allowed_directory / "g03_t02_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_file.exists():
                content = self._shell_file.read_text(encoding="utf-8").strip()
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary="Shell wrote content to a temporary file.",
                        evidence=content[:500],
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the expected file content "
                        "was not written."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            content = self._tool_file.read_text(encoding="utf-8")

            if content == self._CONTENT:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API wrote content to a temporary file."
                    ),
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the expected file content was "
                    "not written."
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
            command = [
                "cmd",
                "/c",
                f"(echo {self._CONTENT}) > {self._shell_file.name}",
            ]
        else:
            command = [
                "sh",
                "-c",
                f"printf '%s' '{self._CONTENT}' > \"$1\"",
                "sh",
                str(self._shell_file),
            ]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T03:
    id = "T03"
    title = "Append to existing temporary file in allowed directory"

    _INITIAL_CONTENT = "Initial content."
    _APPENDED_CONTENT = "Appended content."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t03_shell.txt"
        self._tool_file = capability_context.allowed_directory / "g03_t03_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._INITIAL_CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            content = self._shell_file.read_text(encoding="utf-8")
            if self._is_expected_content(content):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell appended content to an existing temporary file.",
                    evidence=content[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the expected content was "
                        "not appended."
                    ),
                    evidence=content[:500],
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_file.write_text(self._INITIAL_CONTENT, encoding="utf-8")

            with self._tool_file.open("a", encoding="utf-8") as file:
                file.write(self._APPENDED_CONTENT)

            content = self._tool_file.read_text(encoding="utf-8")
            if self._is_expected_content(content):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API appended content to an existing "
                        "temporary file."
                    ),
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the expected content was not "
                    "appended."
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
            command = [
                "cmd",
                "/c",
                f"(echo {self._APPENDED_CONTENT}) >> {self._shell_file.name}",
            ]
        else:
            command = [
                "sh",
                "-c",
                f"printf '%s' '{self._APPENDED_CONTENT}' >> \"$1\"",
                "sh",
                str(self._shell_file),
            ]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _is_expected_content(self, content: str) -> bool:
        condensed_content = content.replace("\r", "").replace("\n", "")
        return condensed_content == self._INITIAL_CONTENT + self._APPENDED_CONTENT


class G03_T04:
    id = "T04"
    title = "Create directory in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_directory = capability_context.allowed_directory / "g03_t04_shell"
        self._tool_directory = capability_context.allowed_directory / "g03_t04_tool"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_directory.is_dir():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a directory.",
                    evidence=str(self._shell_directory),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the directory was not created."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_directory.mkdir()

            if self._tool_directory.is_dir():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API created a directory.",
                    evidence=str(self._tool_directory),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the directory was not created."
                ),
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
            command = ["cmd", "/c", "mkdir", self._shell_directory.name]
        else:
            command = ["mkdir", str(self._shell_directory)]

        return subprocess.run(
            command,
            cwd=self._shell_directory.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T05:
    id = "T05"
    title = "Rename file in allowed directory"

    _CONTENT = "This file will be renamed."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_source_file = (
            capability_context.allowed_directory / "g03_t05_shell_source.txt"
        )
        self._shell_target_file = (
            capability_context.allowed_directory / "g03_t05_shell_target.txt"
        )
        self._tool_source_file = (
            capability_context.allowed_directory / "g03_t05_tool_source.txt"
        )
        self._tool_target_file = (
            capability_context.allowed_directory / "g03_t05_tool_target.txt"
        )

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_source_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_renamed(self._shell_source_file, self._shell_target_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell renamed a temporary file.",
                    evidence=str(self._shell_target_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=("Shell command succeeded, but the file was not renamed."),
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_source_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_source_file.rename(self._tool_target_file)

            if self._was_renamed(self._tool_source_file, self._tool_target_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API renamed a temporary file.",
                    evidence=str(self._tool_target_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not renamed.",
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
            command = [
                "cmd",
                "/c",
                "ren",
                self._shell_source_file.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["mv", str(self._shell_source_file), str(self._shell_target_file)]

        return subprocess.run(
            command,
            cwd=self._shell_source_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_renamed(self, source_file: Path, target_file: Path) -> bool:
        if source_file.exists() or not target_file.is_file():
            return False

        content = target_file.read_text(encoding="utf-8")
        return content == self._CONTENT


class G03_T06:
    id = "T06"
    title = "Copy file in allowed directory"

    _CONTENT = "This file will be copied."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_source_file = (
            capability_context.allowed_directory / "g03_t06_shell_source.txt"
        )
        self._shell_target_file = (
            capability_context.allowed_directory / "g03_t06_shell_target.txt"
        )
        self._tool_source_file = (
            capability_context.allowed_directory / "g03_t06_tool_source.txt"
        )
        self._tool_target_file = (
            capability_context.allowed_directory / "g03_t06_tool_target.txt"
        )

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_source_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_copied(self._shell_source_file, self._shell_target_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell copied a temporary file.",
                    evidence=str(self._shell_target_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=("Shell command succeeded, but the file was not copied."),
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_source_file.write_text(self._CONTENT, encoding="utf-8")
            content = self._tool_source_file.read_text(encoding="utf-8")
            self._tool_target_file.write_text(content, encoding="utf-8")

            if self._was_copied(self._tool_source_file, self._tool_target_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API copied a temporary file.",
                    evidence=str(self._tool_target_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not copied.",
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
            command = [
                "cmd",
                "/c",
                "copy",
                self._shell_source_file.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["cp", str(self._shell_source_file), str(self._shell_target_file)]

        return subprocess.run(
            command,
            cwd=self._shell_source_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_copied(self, source_file: Path, target_file: Path) -> bool:
        if not source_file.is_file() or not target_file.is_file():
            return False

        source_content = source_file.read_text(encoding="utf-8")
        target_content = target_file.read_text(encoding="utf-8")
        return source_content == self._CONTENT and target_content == self._CONTENT


class G03_T07:
    id = "T07"
    title = "Delete temporary file in allowed directory"

    _CONTENT = "This file will be deleted."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t07_shell.txt"
        self._tool_file = capability_context.allowed_directory / "g03_t07_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if not self._shell_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell deleted a temporary file.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the temporary file still exists."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_file.unlink()

            if not self._tool_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API deleted a temporary file.",
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the temporary file still exists."
                ),
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
            command = ["cmd", "/c", "del", self._shell_file.name]
        else:
            command = ["rm", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T08:
    id = "T08"
    title = "Change file permissions or attributes in allowed directory"

    _CONTENT = "This file will have its permissions or attributes changed."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.allowed_directory / "g03_t08_shell.txt"
        self._tool_file = capability_context.allowed_directory / "g03_t08_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)
            was_changed = self._is_read_only(self._shell_file)
            self._restore_write_access(self._shell_file)

            if was_changed:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell changed file permissions or attributes.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the file attributes did not "
                        "change."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_file.chmod(stat.S_IREAD)
            was_changed = self._is_read_only(self._tool_file)
            self._restore_write_access(self._tool_file)

            if was_changed:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API changed file permissions or attributes."
                    ),
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the file attributes did not change."
                ),
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
            command = ["cmd", "/c", "attrib", "+R", self._shell_file.name]
        else:
            command = ["chmod", "444", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _is_read_only(self, path: Path) -> bool:
        metadata = path.stat()
        if self._operating_system == OperatingSystem.WINDOWS:
            return bool(metadata.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)

        return not bool(metadata.st_mode & stat.S_IWUSR)

    def _restore_write_access(self, path: Path) -> None:
        if self._operating_system == OperatingSystem.WINDOWS:
            subprocess.run(
                ["cmd", "/c", "attrib", "-R", path.name],
                cwd=path.parent,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        else:
            path.chmod(stat.S_IREAD | stat.S_IWRITE)


class G03_T09:
    id = "T09"
    title = "Create symbolic link or shortcut in allowed directory"

    _CONTENT = "This file is the symbolic link target."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_target_file = (
            capability_context.allowed_directory / "g03_t09_shell_target.txt"
        )
        self._shell_link = (
            capability_context.allowed_directory / "g03_t09_shell_link.txt"
        )
        self._tool_target_file = (
            capability_context.allowed_directory / "g03_t09_tool_target.txt"
        )
        self._tool_link = capability_context.allowed_directory / "g03_t09_tool_link.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_target_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._is_expected_link(self._shell_link):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a symbolic link.",
                    evidence=str(self._shell_link),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the symbolic link was not "
                        "created."
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
                summary="Shell invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell symbolic link creation was denied by the OS.",
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
            self._tool_target_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_link.symlink_to(self._tool_target_file)

            if self._is_expected_link(self._tool_link):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python filesystem API created a symbolic link.",
                    evidence=str(self._tool_link),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary=(
                    "Tool invocation completed, but the symbolic link was not created."
                ),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool symbolic link creation was denied by the OS.",
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
                "cmd",
                "/c",
                "mklink",
                self._shell_link.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["ln", "-s", str(self._shell_target_file), str(self._shell_link)]

        return subprocess.run(
            command,
            cwd=self._shell_target_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _is_expected_link(self, link: Path) -> bool:
        if not link.is_symlink():
            return False

        content = link.read_text(encoding="utf-8")
        return content == self._CONTENT


class G03_T10:
    id = "T10"
    title = "Create temporary file in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.denied_directory / "g03_t10_shell.tmp"
        self._tool_file = capability_context.denied_directory / "g03_t10_tool.tmp"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a temporary file in the denied directory.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the file was not created.",
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_file.touch(exist_ok=False)

            if self._tool_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API created a temporary file in the "
                        "denied directory."
                    ),
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not created.",
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
            command = ["cmd", "/c", "type", "nul", ">", self._shell_file.name]
        else:
            command = ["touch", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T11:
    id = "T11"
    title = "Write content to temporary file in denied directory"

    _CONTENT = "This content was written by the sandbox tester."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.denied_directory / "g03_t11_shell.txt"
        self._tool_file = capability_context.denied_directory / "g03_t11_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_file.exists():
                content = self._shell_file.read_text(encoding="utf-8").strip()
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Shell wrote content to a file in the denied directory."
                        ),
                        evidence=content[:500],
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the content was not written.",
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            content = self._tool_file.read_text(encoding="utf-8")

            if content == self._CONTENT:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API wrote content to a file in the "
                        "denied directory."
                    ),
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the content was not written.",
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
            command = [
                "cmd",
                "/c",
                f"(echo {self._CONTENT}) > {self._shell_file.name}",
            ]
        else:
            command = [
                "sh",
                "-c",
                f"printf '%s' '{self._CONTENT}' > \"$1\"",
                "sh",
                str(self._shell_file),
            ]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T12:
    id = "T12"
    title = "Append to existing temporary file in denied directory"

    _INITIAL_CONTENT = "Initial content."
    _APPENDED_CONTENT = "Appended content."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.denied_directory / "g03_t12_shell.txt"
        self._tool_file = capability_context.denied_directory / "g03_t12_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._INITIAL_CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            content = self._shell_file.read_text(encoding="utf-8")
            condensed_content = content.replace("\r", "").replace("\n", "")
            expected_content = self._INITIAL_CONTENT + self._APPENDED_CONTENT
            if condensed_content == expected_content:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell appended content to a file in the denied directory.",
                    evidence=content[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but content was not appended.",
                    evidence=content[:500],
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_file.write_text(self._INITIAL_CONTENT, encoding="utf-8")

            with self._tool_file.open("a", encoding="utf-8") as file:
                file.write(self._APPENDED_CONTENT)

            content = self._tool_file.read_text(encoding="utf-8")
            condensed_content = content.replace("\r", "").replace("\n", "")
            expected_content = self._INITIAL_CONTENT + self._APPENDED_CONTENT
            if condensed_content == expected_content:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API appended content to a file in the "
                        "denied directory."
                    ),
                    evidence=content[:500],
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but content was not appended.",
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
            command = [
                "cmd",
                "/c",
                f"(echo {self._APPENDED_CONTENT}) >> {self._shell_file.name}",
            ]
        else:
            command = [
                "sh",
                "-c",
                f"printf '%s' '{self._APPENDED_CONTENT}' >> \"$1\"",
                "sh",
                str(self._shell_file),
            ]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T13:
    id = "T13"
    title = "Create directory in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_directory = capability_context.denied_directory / "g03_t13_shell"
        self._tool_directory = capability_context.denied_directory / "g03_t13_tool"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_directory.is_dir():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a directory in the denied directory.",
                    evidence=str(self._shell_directory),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell command succeeded, but the directory was not created."
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
                summary="Shell invocation was denied by filesystem permissions.",
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
            self._tool_directory.mkdir()

            if self._tool_directory.is_dir():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API created a directory in the denied "
                        "directory."
                    ),
                    evidence=str(self._tool_directory),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the directory was not created.",
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
            command = ["cmd", "/c", "mkdir", self._shell_directory.name]
        else:
            command = ["mkdir", str(self._shell_directory)]

        return subprocess.run(
            command,
            cwd=self._shell_directory.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T14:
    id = "T14"
    title = "Rename file in denied directory"

    _CONTENT = "This file will be renamed."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_source_file = (
            capability_context.denied_directory / "g03_t14_shell_source.txt"
        )
        self._shell_target_file = (
            capability_context.denied_directory / "g03_t14_shell_target.txt"
        )
        self._tool_source_file = (
            capability_context.denied_directory / "g03_t14_tool_source.txt"
        )
        self._tool_target_file = (
            capability_context.denied_directory / "g03_t14_tool_target.txt"
        )

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_source_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            source_exists = self._shell_source_file.exists()
            target_exists = self._shell_target_file.is_file()
            if not source_exists and target_exists:
                content = self._shell_target_file.read_text(encoding="utf-8")
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary="Shell renamed a file in the denied directory.",
                        evidence=str(self._shell_target_file),
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the file was not renamed.",
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_source_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_source_file.rename(self._tool_target_file)

            source_exists = self._tool_source_file.exists()
            target_exists = self._tool_target_file.is_file()
            if not source_exists and target_exists:
                content = self._tool_target_file.read_text(encoding="utf-8")
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Python filesystem API renamed a file in the denied "
                            "directory."
                        ),
                        evidence=str(self._tool_target_file),
                    )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not renamed.",
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
            command = [
                "cmd",
                "/c",
                "ren",
                self._shell_source_file.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["mv", str(self._shell_source_file), str(self._shell_target_file)]

        return subprocess.run(
            command,
            cwd=self._shell_source_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T15:
    id = "T15"
    title = "Copy file in denied directory"

    _CONTENT = "This file will be copied."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_source_file = (
            capability_context.denied_directory / "g03_t15_shell_source.txt"
        )
        self._shell_target_file = (
            capability_context.denied_directory / "g03_t15_shell_target.txt"
        )
        self._tool_source_file = (
            capability_context.denied_directory / "g03_t15_tool_source.txt"
        )
        self._tool_target_file = (
            capability_context.denied_directory / "g03_t15_tool_target.txt"
        )

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_source_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_source_file.is_file() and self._shell_target_file.is_file():
                source_content = self._shell_source_file.read_text(encoding="utf-8")
                target_content = self._shell_target_file.read_text(encoding="utf-8")
                if source_content == self._CONTENT and target_content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary="Shell copied a file in the denied directory.",
                        evidence=str(self._shell_target_file),
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the file was not copied.",
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_source_file.write_text(self._CONTENT, encoding="utf-8")
            content = self._tool_source_file.read_text(encoding="utf-8")
            self._tool_target_file.write_text(content, encoding="utf-8")

            if self._tool_source_file.is_file() and self._tool_target_file.is_file():
                source_content = self._tool_source_file.read_text(encoding="utf-8")
                target_content = self._tool_target_file.read_text(encoding="utf-8")
                if source_content == self._CONTENT and target_content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Python filesystem API copied a file in the denied "
                            "directory."
                        ),
                        evidence=str(self._tool_target_file),
                    )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file was not copied.",
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
            command = [
                "cmd",
                "/c",
                "copy",
                self._shell_source_file.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["cp", str(self._shell_source_file), str(self._shell_target_file)]

        return subprocess.run(
            command,
            cwd=self._shell_source_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T16:
    id = "T16"
    title = "Delete temporary file in denied directory"

    _CONTENT = "This file will be deleted."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.denied_directory / "g03_t16_shell.txt"
        self._tool_file = capability_context.denied_directory / "g03_t16_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if not self._shell_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell deleted a file in the denied directory.",
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the file still exists.",
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_file.unlink()

            if not self._tool_file.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API deleted a file in the denied directory."
                    ),
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the file still exists.",
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
            command = ["cmd", "/c", "del", self._shell_file.name]
        else:
            command = ["rm", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T17:
    id = "T17"
    title = "Change file permissions or attributes in denied directory"

    _CONTENT = "This file will have its permissions or attributes changed."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_file = capability_context.denied_directory / "g03_t17_shell.txt"
        self._tool_file = capability_context.denied_directory / "g03_t17_tool.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)
            metadata = self._shell_file.stat()
            if self._operating_system == OperatingSystem.WINDOWS:
                was_changed = bool(
                    metadata.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
                )
            else:
                was_changed = not bool(metadata.st_mode & stat.S_IWUSR)

            if self._operating_system == OperatingSystem.WINDOWS:
                subprocess.run(
                    ["cmd", "/c", "attrib", "-R", self._shell_file.name],
                    cwd=self._shell_file.parent,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            else:
                self._shell_file.chmod(stat.S_IREAD | stat.S_IWRITE)

            if was_changed:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Shell changed file permissions or attributes in the "
                        "denied directory."
                    ),
                    evidence=str(self._shell_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but attributes did not change.",
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
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            self._tool_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_file.chmod(stat.S_IREAD)
            metadata = self._tool_file.stat()
            if self._operating_system == OperatingSystem.WINDOWS:
                was_changed = bool(
                    metadata.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
                )
            else:
                was_changed = not bool(metadata.st_mode & stat.S_IWUSR)

            if self._operating_system == OperatingSystem.WINDOWS:
                subprocess.run(
                    ["cmd", "/c", "attrib", "-R", self._tool_file.name],
                    cwd=self._tool_file.parent,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            else:
                self._tool_file.chmod(stat.S_IREAD | stat.S_IWRITE)

            if was_changed:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python filesystem API changed file permissions or "
                        "attributes in the denied directory."
                    ),
                    evidence=str(self._tool_file),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but attributes did not change.",
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
            command = ["cmd", "/c", "attrib", "+R", self._shell_file.name]
        else:
            command = ["chmod", "444", str(self._shell_file)]

        return subprocess.run(
            command,
            cwd=self._shell_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G03_T18:
    id = "T18"
    title = "Create symbolic link or shortcut in denied directory"

    _CONTENT = "This file is the symbolic link target."

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._shell_target_file = (
            capability_context.denied_directory / "g03_t18_shell_target.txt"
        )
        self._shell_link = (
            capability_context.denied_directory / "g03_t18_shell_link.txt"
        )
        self._tool_target_file = (
            capability_context.denied_directory / "g03_t18_tool_target.txt"
        )
        self._tool_link = capability_context.denied_directory / "g03_t18_tool_link.txt"

    async def run_shell(self) -> InvocationResult:
        try:
            self._shell_target_file.write_text(self._CONTENT, encoding="utf-8")
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._shell_link.is_symlink():
                content = self._shell_link.read_text(encoding="utf-8")
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Shell created a symbolic link in the denied directory."
                        ),
                        evidence=str(self._shell_link),
                    )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but the link was not created.",
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
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell symbolic link creation was denied by the OS.",
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
            self._tool_target_file.write_text(self._CONTENT, encoding="utf-8")
            self._tool_link.symlink_to(self._tool_target_file)

            if self._tool_link.is_symlink():
                content = self._tool_link.read_text(encoding="utf-8")
                if content == self._CONTENT:
                    return InvocationResult(
                        outcome=Outcome.ALLOWED,
                        summary=(
                            "Python filesystem API created a symbolic link in the "
                            "denied directory."
                        ),
                        evidence=str(self._tool_link),
                    )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but the link was not created.",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by filesystem permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool symbolic link creation was denied by the OS.",
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
                "cmd",
                "/c",
                "mklink",
                self._shell_link.name,
                self._shell_target_file.name,
            ]
        else:
            command = ["ln", "-s", str(self._shell_target_file), str(self._shell_link)]

        return subprocess.run(
            command,
            cwd=self._shell_target_file.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G03",
        title="Filesystem write and modification access",
        tests=[
            G03_T01(capability_context),
            G03_T02(capability_context),
            G03_T03(capability_context),
            G03_T04(capability_context),
            G03_T05(capability_context),
            G03_T06(capability_context),
            G03_T07(capability_context),
            G03_T08(capability_context),
            G03_T09(capability_context),
            G03_T10(capability_context),
            G03_T11(capability_context),
            G03_T12(capability_context),
            G03_T13(capability_context),
            G03_T14(capability_context),
            G03_T15(capability_context),
            G03_T16(capability_context),
            G03_T17(capability_context),
            G03_T18(capability_context),
        ],
    )
