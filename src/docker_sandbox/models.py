"""Models for Docker sandbox orchestration."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DockerImageStatus(StrEnum):
    """Result status for a Docker sandbox image request."""

    EXISTS = "exists"
    CREATED = "created"
    BUILD_FAILED = "build_failed"
    DOCKER_MISSING = "docker_missing"
    DOCKERFILE_MISSING = "dockerfile_missing"


@dataclass(frozen=True)
class DockerConfiguration:
    """Configuration for creating Docker sandbox images."""

    base_directory: Path
    image_name: str
    dockerfile_path: Path
    build_context: Path


@dataclass(frozen=True)
class DockerImageResult:
    """Result of ensuring the Docker sandbox image exists."""

    status: DockerImageStatus
    image_name: str
    dockerfile_path: Path
    command: list[str] | None = None


@dataclass(frozen=True)
class DockerRunResult:
    """Result of running Sandbox Tester in a disposable Docker container."""

    image_name: str
    container_name: str
    run_directory: Path
    command: list[str]
    remove_command: list[str]
    exit_code: int
    stdout: str
    stderr: str

    def remove_container(self) -> None:
        """Remove the disposable Docker container for this run."""
        import subprocess

        subprocess.run(
            self.remove_command,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
