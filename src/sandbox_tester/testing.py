"""Testing for the Sandbox Tester."""

import platform
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from .models import CapabilityGroupResult, CapabilityResult, InvocationResult
from .reporter import TestReporter

CHILD_DIRECTORY_NAME = "child"
HIDDEN_FILE_NAME = ".hidden"
TEXT_FILE_NAME = "test.txt"


class OperatingSystem(StrEnum):
    WINDOWS = "Windows"
    LINUX = "Linux"


@dataclass(frozen=True)
class CapabilityContext:
    working_directory: Path
    scratch_directory: Path
    runtime_user_directory: Path
    runtime_temp_directory: Path
    mounted_shared_directory: Path | None
    operating_system: OperatingSystem

    @classmethod
    def from_current_environment(
        cls,
        working_directory: Path,
        scratch_directory: Path,
        mounted_shared_directory: Path | None = None,
    ) -> "CapabilityContext":
        system_name = platform.system()

        if system_name == "Windows":
            operating_system = OperatingSystem.WINDOWS
        elif system_name == "Linux":
            operating_system = OperatingSystem.LINUX
        else:
            raise RuntimeError(f"Unsupported operating system: {system_name}")

        return cls(
            working_directory=working_directory,
            scratch_directory=scratch_directory,
            runtime_user_directory=Path.home().resolve(),
            runtime_temp_directory=Path(tempfile.gettempdir()).resolve(),
            mounted_shared_directory=(
                mounted_shared_directory.resolve()
                if mounted_shared_directory is not None
                else None
            ),
            operating_system=operating_system,
        )


def create_scratch_directory() -> Path:
    scratch_directory = Path(tempfile.mkdtemp(prefix="sandbox-tester-")).resolve()
    child_directory = scratch_directory / CHILD_DIRECTORY_NAME
    child_directory.mkdir(parents=True, exist_ok=True)
    text_file = child_directory / TEXT_FILE_NAME
    text_file.write_text(
        "This is a test file for the scratch directory.", encoding="utf-8"
    )
    hidden_file = child_directory / HIDDEN_FILE_NAME
    hidden_file.write_text("This is a hidden file.", encoding="utf-8")

    return scratch_directory


def delete_scratch_directory(scratch_directory: Path) -> None:
    """Delete the scratch directory and its contents."""
    if scratch_directory.exists() and scratch_directory.is_dir():
        for child in scratch_directory.iterdir():
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                delete_scratch_directory(child)
        scratch_directory.rmdir()


class CapabilityTest(Protocol):
    id: str
    title: str

    async def run_shell(self) -> InvocationResult: ...

    async def run_tool(self) -> InvocationResult: ...


@dataclass(frozen=True)
class CapabilityGroup:
    id: str
    title: str
    tests: list[CapabilityTest]


async def run_group(
    group: CapabilityGroup,
    reporter: TestReporter,
) -> CapabilityGroupResult:
    results: list[CapabilityResult] = []

    reporter.group_started(group.id, group.title)

    for test in group.tests:
        reporter.capability_started(test.id, test.title)

        shell_result: InvocationResult = await test.run_shell()
        reporter.shell_completed(shell_result)

        tool_result: InvocationResult = await test.run_tool()
        reporter.tool_completed(tool_result)

        result = CapabilityResult(
            id=test.id,
            title=test.title,
            shell=shell_result,
            tool=tool_result,
        )
        results.append(result)

    group_result = CapabilityGroupResult(
        id=group.id,
        title=group.title,
        capabilities=results,
    )

    return group_result
