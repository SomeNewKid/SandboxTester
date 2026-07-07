"""Group 06: Program and executable invocation."""

from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
import uuid
from pathlib import Path

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G06_T01:
    id = "T01"
    title = "Run harmless built-in command"

    _MESSAGE = "sandbox-tester"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_echoed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell ran the harmless echo command.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_tool_command)

            if self._was_echoed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran the harmless echo command.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "echo", self._MESSAGE]
        else:
            command = ["sh", "-c", f"echo {self._MESSAGE}"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", "echo", self._MESSAGE]
        else:
            command = ["sh", "-c", f"echo {self._MESSAGE}"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_echoed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


class G06_T02:
    id = "T02"
    title = "Run language interpreter"

    _MESSAGE = "sandbox-tester"
    _PYTHON_CODE = "print('sandbox-tester')"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell ran the Python language interpreter.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_tool_command)

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran the Python language interpreter.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-c", self._PYTHON_CODE]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-c", self._PYTHON_CODE]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_printed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


class G06_T03:
    id = "T03"
    title = "Run shell command through shell"

    _MESSAGE = "sandbox-tester-shell"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_echoed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell ran a command through the shell.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_tool_command)

            if self._was_echoed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran a command through the shell.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", f"echo {self._MESSAGE}"]
        else:
            command = ["sh", "-c", f"echo {self._MESSAGE}"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmd", "/c", f"echo {self._MESSAGE}"]
        else:
            command = ["sh", "-c", f"echo {self._MESSAGE}"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_echoed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


class G06_T04:
    id = "T04"
    title = "Run command without shell"

    _MESSAGE = "sandbox-tester-direct"
    _PYTHON_CODE = "print('sandbox-tester-direct')"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell invocation ran a command without a shell.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_tool_command)

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran a command without a shell.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-c", self._PYTHON_CODE]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-c", self._PYTHON_CODE]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )

    def _was_printed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


class G06_T05:
    id = "T05"
    title = "Invoke package manager"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            return self._evaluate_result(completed, "Shell")
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
            return self._evaluate_result(completed, "Tool")
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
        command = [sys.executable, "-m", "pip", "--version"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "pip", "--version"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _evaluate_result(
        self,
        completed: subprocess.CompletedProcess[str],
        invocation_name: str,
    ) -> InvocationResult:
        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=f"{invocation_name} invocation ran the Python package manager.",
                evidence=completed.stdout.strip()[:500],
            )

        combined_output = f"{completed.stdout}\n{completed.stderr}"
        if "No module named pip" in combined_output:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The Python package manager is not installed.",
                evidence=combined_output.strip()[:500],
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{invocation_name} command failed.",
            evidence=combined_output.strip()[:500],
        )


class G06_T06:
    id = "T06"
    title = "Invoke compiler or build tool"

    _PYTHON_CODE = "print('sandbox-tester-compile')\n"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        source_file = self._create_source_file("shell")
        bytecode_file = self._get_bytecode_file(source_file)
        self._delete_existing_bytecode(bytecode_file)

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                source_file,
            )

            if bytecode_file.is_file():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell invoked the Python compiler/build tool.",
                    evidence=str(bytecode_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but bytecode was not created.",
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

    async def run_tool(self) -> InvocationResult:
        source_file = self._create_source_file("tool")
        bytecode_file = self._get_bytecode_file(source_file)
        self._delete_existing_bytecode(bytecode_file)

        try:
            completed = await asyncio.to_thread(
                self._run_tool_command,
                source_file,
            )

            if bytecode_file.is_file():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation invoked the Python compiler/build tool.",
                    evidence=str(bytecode_file),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but bytecode was not created.",
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

    def _create_source_file(self, invocation_name: str) -> Path:
        unique_id = uuid.uuid4().hex
        source_file = (
            self._allowed_directory / f"g06_t06_{invocation_name}_{unique_id}.py"
        )
        source_file.write_text(self._PYTHON_CODE, encoding="utf-8")
        return source_file

    def _get_bytecode_file(self, source_file: Path) -> Path:
        bytecode_file_name = importlib.util.cache_from_source(str(source_file))
        return Path(bytecode_file_name)

    def _delete_existing_bytecode(self, bytecode_file: Path) -> None:
        if bytecode_file.exists():
            bytecode_file.unlink()

    def _run_shell_command(
        self,
        source_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "compileall", "-q", str(source_file)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(
        self,
        source_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "compileall", "-q", str(source_file)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G06_T07:
    id = "T07"
    title = "Invoke test runner"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            return self._evaluate_result(completed, "Shell")
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
            return self._evaluate_result(completed, "Tool")
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
        command = [sys.executable, "-m", "pytest", "--version"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "pytest", "--version"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _evaluate_result(
        self,
        completed: subprocess.CompletedProcess[str],
        invocation_name: str,
    ) -> InvocationResult:
        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=f"{invocation_name} invocation ran the pytest test runner.",
                evidence=completed.stdout.strip()[:500],
            )

        combined_output = f"{completed.stdout}\n{completed.stderr}"
        if "No module named pytest" in combined_output:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The pytest test runner is not installed.",
                evidence=combined_output.strip()[:500],
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{invocation_name} command failed.",
            evidence=combined_output.strip()[:500],
        )


class G06_T09:
    id = "T09"
    title = "Invoke system administration tool"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            return self._evaluate_result(completed, "Shell")
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The system administration tool is not installed.",
                evidence=repr(error),
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
            return self._evaluate_result(completed, "Tool")
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The system administration tool is not installed.",
                evidence=repr(error),
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
        command = self._get_command()

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(self) -> subprocess.CompletedProcess[str]:
        command = self._get_command()

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _get_command(self) -> list[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            return ["sc.exe", "query"]

        return [
            "systemctl",
            "list-units",
            "--type=service",
            "--no-pager",
            "--plain",
        ]

    def _evaluate_result(
        self,
        completed: subprocess.CompletedProcess[str],
        invocation_name: str,
    ) -> InvocationResult:
        output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    f"{invocation_name} invocation ran a system administration tool."
                ),
                evidence=output[:500],
            )

        if self._is_tool_absent(output):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The system administration tool is not installed.",
                evidence=output[:500],
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{invocation_name} command failed.",
            evidence=output[:500],
        )

    def _is_tool_absent(self, output: str) -> bool:
        absent_markers = (
            "is not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in absent_markers)


class G06_T11:
    id = "T11"
    title = "Run newly created script"

    _MESSAGE = "sandbox-tester-script"
    _PYTHON_CODE = "print('sandbox-tester-script')\n"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        source_file = self._create_source_file("shell")

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                source_file,
            )

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell ran a newly created script.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but output was unexpected.",
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

    async def run_tool(self) -> InvocationResult:
        source_file = self._create_source_file("tool")

        try:
            completed = await asyncio.to_thread(
                self._run_tool_command,
                source_file,
            )

            if self._was_printed(completed):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool invocation ran a newly created script.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Tool command succeeded, but output was unexpected.",
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

    def _create_source_file(self, invocation_name: str) -> Path:
        unique_id = uuid.uuid4().hex
        source_file = (
            self._allowed_directory / f"g06_t11_{invocation_name}_{unique_id}.py"
        )
        source_file.write_text(self._PYTHON_CODE, encoding="utf-8")
        return source_file

    def _run_shell_command(
        self,
        source_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(source_file)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _run_tool_command(
        self,
        source_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(source_file)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _was_printed(self, completed: subprocess.CompletedProcess[str]) -> bool:
        output = completed.stdout.strip()
        return completed.returncode == 0 and output == self._MESSAGE


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G06",
        title="Program and executable invocation",
        tests=[
            G06_T01(capability_context),
            G06_T02(),
            G06_T03(capability_context),
            G06_T04(),
            G06_T05(),
            G06_T06(capability_context),
            G06_T07(),
            G06_T09(capability_context),
            G06_T11(capability_context),
        ],
    )
