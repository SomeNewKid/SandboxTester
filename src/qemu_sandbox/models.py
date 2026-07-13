"""Models for QEMU sandbox orchestration."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from subprocess import Popen


class QemuRunStatus(StrEnum):
    """Result status for a QEMU sandbox run request."""

    STARTED = "started"
    BASE_IMAGE_MISSING = "base_image_missing"
    QEMU_MISSING = "qemu_missing"


@dataclass(frozen=True)
class GuestCredentials:
    """Guest operating system credentials used by the sandbox orchestrator."""

    user: str
    password: str


@dataclass(frozen=True)
class QemuConfiguration:
    """Configuration for starting disposable QEMU sandbox VMs."""

    base_directory: Path
    base_image_path: Path
    kernel_path: Path | None
    initrd_path: Path | None
    kernel_append: str | None
    qemu_path: Path
    guest_credentials: GuestCredentials
    machine: str
    accelerator: str
    cpu: str
    memory_megabytes: int
    cpu_count: int


@dataclass(frozen=True)
class QemuRunResult:
    """Result of attempting to create and start a disposable QEMU VM."""

    status: QemuRunStatus
    base_image_path: Path
    qemu_path: Path | None = None
    run_directory: Path | None = None
    run_disk_path: Path | None = None
    ssh_host: str | None = None
    ssh_port: int | None = None
    process: Popen[bytes] | None = None
    command: list[str] | None = None
