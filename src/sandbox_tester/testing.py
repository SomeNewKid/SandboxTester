"""Testing for the Sandbox Tester."""

import platform
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from .models import CapabilityGroupResult, CapabilityResult, InvocationResult
from .reporter import TestReporter

ALLOWED_CHILD_DIRECTORY = "allowed"
DENIED_CHILD_DIRECTORY = "denied"
HIDDEN_FILE_NAME = ".hidden"
ALLOWED_FILE_NAME = "allowed.txt"
DENIED_FILE_NAME = "denied.txt"


class OperatingSystem(StrEnum):
    WINDOWS = "Windows"
    LINUX = "Linux"


@dataclass(frozen=True)
class CapabilityContext:
    working_directory: Path
    allowed_directory: Path
    denied_directory: Path
    runtime_user_directory: Path
    runtime_temp_directory: Path
    mounted_shared_directory: Path | None
    operating_system: OperatingSystem
    allowed_domain: str | None = None
    denied_domain: str | None = None
    allowed_local_address: str | None = None
    denied_local_address: str | None = None
    allowed_localnet_address: str | None = None
    denied_localnet_address: str | None = None
    allowed_database_address: str | None = None
    denied_database_address: str | None = None
    container_runtime_socket: str | None = None
    local_dev_server_url: str | None = None
    local_model_server_url: str | None = None
    ssh_agent_socket: str | None = None
    browser_debugging_url: str | None = None
    browser_executable: Path | None = None
    existing_browser_profile: Path | None = None
    allowed_git_repository: Path | None = None
    denied_git_repository: Path | None = None
    git_remote_url: str | None = None
    allow_camera_capture: bool = False
    allow_microphone_capture: bool = False

    @classmethod
    def from_current_environment(
        cls,
        working_directory: Path,
        allowed_directory: Path,
        denied_directory: Path,
        mounted_shared_directory: Path | None = None,
        allowed_domain: str | None = None,
        denied_domain: str | None = None,
        allowed_local_address: str | None = None,
        denied_local_address: str | None = None,
        allowed_localnet_address: str | None = None,
        denied_localnet_address: str | None = None,
        allowed_database_address: str | None = None,
        denied_database_address: str | None = None,
        container_runtime_socket: str | None = None,
        local_dev_server_url: str | None = None,
        local_model_server_url: str | None = None,
        ssh_agent_socket: str | None = None,
        browser_debugging_url: str | None = None,
        browser_executable: Path | None = None,
        existing_browser_profile: Path | None = None,
        allowed_git_repository: Path | None = None,
        denied_git_repository: Path | None = None,
        git_remote_url: str | None = None,
        allow_camera_capture: bool = False,
        allow_microphone_capture: bool = False,
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
            allowed_directory=allowed_directory,
            denied_directory=denied_directory,
            runtime_user_directory=Path.home().resolve(),
            runtime_temp_directory=Path(tempfile.gettempdir()).resolve(),
            mounted_shared_directory=(
                mounted_shared_directory.resolve()
                if mounted_shared_directory is not None
                else None
            ),
            operating_system=operating_system,
            allowed_domain=allowed_domain,
            denied_domain=denied_domain,
            allowed_local_address=allowed_local_address,
            denied_local_address=denied_local_address,
            allowed_localnet_address=allowed_localnet_address,
            denied_localnet_address=denied_localnet_address,
            allowed_database_address=allowed_database_address,
            denied_database_address=denied_database_address,
            container_runtime_socket=container_runtime_socket,
            local_dev_server_url=local_dev_server_url,
            local_model_server_url=local_model_server_url,
            ssh_agent_socket=ssh_agent_socket,
            browser_debugging_url=browser_debugging_url,
            browser_executable=browser_executable,
            existing_browser_profile=existing_browser_profile,
            allowed_git_repository=(
                allowed_git_repository.resolve()
                if allowed_git_repository is not None
                else None
            ),
            denied_git_repository=(
                denied_git_repository.resolve()
                if denied_git_repository is not None
                else None
            ),
            git_remote_url=git_remote_url,
            allow_camera_capture=allow_camera_capture,
            allow_microphone_capture=allow_microphone_capture,
        )


def create_allowed_directory() -> Path:
    allowed_directory = Path(tempfile.mkdtemp(prefix="sandbox-tester-")).resolve()
    allowed_child_directory = allowed_directory / ALLOWED_CHILD_DIRECTORY
    allowed_child_directory.mkdir(parents=True, exist_ok=True)
    text_file = allowed_child_directory / ALLOWED_FILE_NAME
    text_file.write_text(
        "This is a test file for the allowed directory.", encoding="utf-8"
    )
    hidden_file = allowed_child_directory / HIDDEN_FILE_NAME
    hidden_file.write_text("This is a hidden file.", encoding="utf-8")

    return allowed_directory


def create_disallowed_directory() -> Path:
    denied_directory = Path(tempfile.mkdtemp(prefix="sandbox-tester-denied-")).resolve()
    denied_child_directory = denied_directory / DENIED_CHILD_DIRECTORY
    denied_child_directory.mkdir(parents=True, exist_ok=True)
    denied_file = denied_child_directory / DENIED_FILE_NAME
    denied_file.write_text(
        "This is a test file for the denied directory.", encoding="utf-8"
    )
    hidden_file = denied_child_directory / HIDDEN_FILE_NAME
    hidden_file.write_text(
        "This is a hidden file in the denied directory.", encoding="utf-8"
    )

    return denied_directory


def delete_allowed_directory(allowed_directory: Path) -> None:
    """Delete the allowed directory and its contents."""
    _delete_directory(allowed_directory)


def delete_denied_directory(denied_directory: Path) -> None:
    """Delete the denied directory and its contents."""
    _delete_directory(denied_directory)


def _delete_directory(directory: Path) -> None:
    if directory.exists() and directory.is_dir():
        for child in directory.iterdir():
            if child.is_file() or child.is_symlink():
                try:
                    child.unlink()
                except PermissionError:
                    pass
            elif child.is_dir():
                _delete_directory(child)
        try:
            directory.rmdir()
        except OSError:
            pass


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
