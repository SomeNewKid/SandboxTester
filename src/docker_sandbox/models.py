"""Models for Docker sandbox orchestration."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class LandlockPathRule:
    """Path rule for the container-side Landlock launcher."""

    path: str
    access: str


@dataclass(frozen=True)
class NetworkGatewayProfile:
    """Network egress gateway settings for a Docker profile."""

    image_name: str
    proxy_host: str
    proxy_port: int
    allowed_domains: tuple[str, ...] = ()
    allowed_ip_addresses: tuple[str, ...] = ()


@dataclass(frozen=True)
class SocketMount:
    """Explicit host socket mount allowed for a Docker profile."""

    source_path: Path
    target_path: str
    readonly: bool = True


@dataclass(frozen=True)
class AgentSocketForward:
    """Explicit SSH or GPG agent socket forwarding for a Docker profile."""

    source_path: Path
    target_path: str


@dataclass(frozen=True)
class BrowserDebuggingProfile:
    """Explicit browser debugging surface allowed for a Docker profile."""

    debugging_url: str | None = None
    browser_executable: str | None = None
    existing_browser_profile: str | None = None


@dataclass(frozen=True)
class EnvironmentVariablePolicy:
    """Environment variable override for a Docker profile."""

    name: str
    value: str | None


@dataclass(frozen=True)
class DockerProfile:
    """Docker image and container hardening profile."""

    name: str
    description: str
    image_name: str
    image_build_arguments: tuple[str, ...] = ()
    ipc_mode: str | None = "host"
    shm_size: str | None = None
    cgroupns_mode: str | None = "private"
    pids_limit: int | None = 512
    cap_drop: tuple[str, ...] = ("ALL",)
    cap_add: tuple[str, ...] = ()
    security_options: tuple[str, ...] = ("no-new-privileges",)
    container_run_options: tuple[str, ...] = ()
    remote_run_root: str = "/tmp/sandbox-tester"
    allowed_directory_template: str = "{remote_run_directory}/allowed"
    denied_directory_template: str = "{remote_run_directory}/denied"
    readonly_denied_mount_target: str | None = None
    landlock_rules: tuple[LandlockPathRule, ...] = ()
    network_gateway: NetworkGatewayProfile | None = None
    socket_mounts: tuple[SocketMount, ...] = ()
    ssh_agent_socket: AgentSocketForward | None = None
    gpg_agent_socket: AgentSocketForward | None = None
    browser_debugging: BrowserDebuggingProfile | None = None
    environment: tuple[EnvironmentVariablePolicy, ...] = ()
    denied_executables: tuple[str, ...] = ()
    denied_executable_paths: tuple[str, ...] = (
        "/opt/sandbox-tester/.venv/bin/pip",
        "/opt/sandbox-tester/.venv/bin/pip3",
        "/usr/bin/apt",
        "/usr/bin/apt-get",
        "/usr/bin/bash",
        "/usr/bin/busctl",
        "/usr/bin/dbus-send",
        "/usr/bin/dpkg",
        "/usr/bin/dpkg-query",
        "/usr/bin/findmnt",
        "/usr/bin/git",
        "/usr/bin/gpg",
        "/usr/bin/gpg-connect-agent",
        "/usr/bin/gpgconf",
        "/usr/bin/journalctl",
        "/usr/bin/loginctl",
        "/usr/bin/mount",
        "/usr/bin/nice",
        "/usr/bin/nohup",
        "/usr/bin/nsenter",
        "/usr/bin/perl",
        "/usr/bin/renice",
        "/usr/bin/scp",
        "/usr/bin/sftp",
        "/usr/bin/setsid",
        "/usr/bin/ssh",
        "/usr/bin/ssh-add",
        "/usr/bin/su",
        "/usr/bin/systemd-run",
        "/usr/bin/systemctl",
        "/usr/bin/umount",
        "/usr/bin/unshare",
        "/usr/sbin/service",
    )


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
    network_name: str | None = None
    gateway_container_name: str | None = None
    gateway_ip_address: str | None = None
    gateway_commands: list[list[str]] | None = None
    gateway_cleanup_commands: list[list[str]] | None = None

    def remove_container(self) -> None:
        """Remove disposable Docker resources for this run."""
        import subprocess

        subprocess.run(
            self.remove_command,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if self.gateway_cleanup_commands is None:
            return

        for command in self.gateway_cleanup_commands:
            subprocess.run(
                command,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
