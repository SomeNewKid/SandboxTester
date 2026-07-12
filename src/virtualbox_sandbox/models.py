"""Models for VirtualBox sandbox orchestration."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class VirtualMachineState(StrEnum):
    """Known VirtualBox VM states used by the sandbox factory."""

    NOT_CREATED = "not_created"
    RUNNING = "running"
    STOPPED = "stopped"
    OTHER = "other"


class VmCloneStatus(StrEnum):
    """Result status for a VM clone creation request."""

    BASE_CREATED = "base_created"
    BASE_RUNNING = "base_running"
    CLONE_STARTED = "clone_started"
    ISO_MISSING = "iso_missing"
    NOT_READY = "not_ready"


class BaseFinalizationStatus(StrEnum):
    """Result status for base VM finalization."""

    FINALIZED = "finalized"
    MISSING = "missing"
    NOT_READY = "not_ready"


@dataclass(frozen=True)
class VirtualMachine:
    """A registered VirtualBox virtual machine."""

    name: str
    uuid: str


@dataclass(frozen=True)
class GuestCredentials:
    """Guest operating system credentials used by the sandbox orchestrator."""

    user: str
    password: str


@dataclass(frozen=True)
class VirtualBoxConfiguration:
    """Configuration for creating and cloning sandbox VMs."""

    vm_name: str
    iso_path: Path | None
    base_directory: Path
    disk_size_megabytes: int
    memory_megabytes: int
    cpu_count: int
    guest_credentials: GuestCredentials
    hostname: str


@dataclass(frozen=True)
class PythonAgentProfile:
    """Configuration for a Python agent that can run in the sandbox VM."""

    name: str
    source_directory: Path
    package_directory_name: str
    dependencies: list[str]
    entry_script: str
    exclude_patterns: list[str]
    environment_variables: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GuestRunLayout:
    """Disposable guest paths prepared for an agent run."""

    run_directory: str
    allowed_directory: str
    denied_directory: str
    output_directory: str
    config_path: str
    config_json: str


@dataclass(frozen=True)
class VmCloneResult:
    """Result of attempting to create and start a sandbox VM clone."""

    status: VmCloneStatus
    base_vm_name: str
    run_vm_name: str | None = None
    run_directory: Path | None = None
    ssh_host: str | None = None
    ssh_port: int | None = None


@dataclass(frozen=True)
class BaseFinalizationResult:
    """Result of attempting to finalize the base VM."""

    status: BaseFinalizationStatus
    base_vm_name: str
    ssh_host: str | None = None
    ssh_port: int | None = None


@dataclass(frozen=True)
class GuestScriptResult:
    """Result of running a Python script in the guest VM."""

    script_path: str
    source_path: str | None
    command: str
    exit_code: int
    stdout: str
    stderr: str
    artifacts: dict[str, str] = field(default_factory=dict)
