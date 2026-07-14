"""Models for Docker sandbox orchestration."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class DockerProfile:
    """Docker image and container hardening profile."""

    name: str
    description: str
    image_name: str
    image_build_arguments: tuple[str, ...] = ()
    container_run_options: tuple[str, ...] = ()
    remote_run_root: str = "/tmp/sandbox-tester"
    allowed_directory_template: str = "{remote_run_directory}/allowed"
    denied_directory_template: str = "{remote_run_directory}/denied"
    readonly_denied_mount_target: str | None = None


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
    dockerfile_path: Path
    build_context: Path
    guest_user: str
    profile: DockerProfile


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
    profile_name: str
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
