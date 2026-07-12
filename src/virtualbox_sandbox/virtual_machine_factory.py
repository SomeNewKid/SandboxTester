"""Create and start VirtualBox sandbox virtual machines."""

from __future__ import annotations

import datetime as dt
import os
import re
import shlex
import socket
import subprocess
import time
from pathlib import Path

import paramiko

from .models import (
    BaseFinalizationResult,
    BaseFinalizationStatus,
    VirtualBoxConfiguration,
    VirtualMachine,
    VirtualMachineState,
    VmCloneResult,
    VmCloneStatus,
)

_DEFAULT_OS_TYPE = "Ubuntu24_LTS_64"
_ENABLE_OPENSSH_COMMAND = (
    "apt-get update && "
    "apt-get install -y openssh-server python3 && "
    "systemctl enable ssh && "
    "systemctl start ssh"
)
_FINALIZE_BASE_PACKAGES = [
    "python3-pip",
    "python3-venv",
    "xvfb",
    "fonts-noto-color-emoji",
    "fonts-unifont",
    "libfontconfig1",
    "libfreetype6",
    "xfonts-cyrillic",
    "xfonts-scalable",
    "fonts-liberation",
    "fonts-ipafont-gothic",
    "fonts-wqy-zenhei",
    "fonts-tlwg-loma-otf",
    "fonts-freefont-ttf",
    "libasound2t64",
    "libatk-bridge2.0-0t64",
    "libatk1.0-0t64",
    "libatspi2.0-0t64",
    "libcairo2",
    "libcups2t64",
    "libdbus-1-3",
    "libdrm2",
    "libgbm1",
    "libglib2.0-0t64",
    "libnspr4",
    "libnss3",
    "libpango-1.0-0",
    "libx11-6",
    "libxcb1",
    "libxcomposite1",
    "libxdamage1",
    "libxext6",
    "libxfixes3",
    "libxkbcommon0",
    "libxrandr2",
]
_BASE_SSH_FORWARD_NAME = "sandbox-base-ssh"
_RUN_VM_NAME_PREFIX = "Sandbox Tester Run"
_SSH_FORWARD_NAME = "sandbox-ssh"
_SSH_FORWARD_HOST = "127.0.0.1"
_VBOXMANAGE_ENVIRONMENT_VARIABLE = "VBOXMANAGE"
_ISO_ENVIRONMENT_VARIABLE = "SANDBOX_TESTER_ISO"
_WINDOWS_VBOXMANAGE_PATH = Path(r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe")
_VM_LINE_PATTERN = re.compile(r'^"(?P<name>.*)" \{(?P<uuid>[^}]+)\}$')


class _SshNotReadyError(RuntimeError):
    pass


def create_vm_clone(configuration: VirtualBoxConfiguration) -> VmCloneResult:
    """Create the base VM when needed, or clone and start it when ready."""
    vboxmanage_path = _find_vboxmanage()
    state = _get_virtual_machine_state(vboxmanage_path, configuration.vm_name)

    if state == VirtualMachineState.NOT_CREATED:
        return _create_missing_base_vm(vboxmanage_path, configuration)

    if state == VirtualMachineState.RUNNING:
        return VmCloneResult(
            status=VmCloneStatus.BASE_RUNNING,
            base_vm_name=configuration.vm_name,
        )

    if state == VirtualMachineState.STOPPED:
        run_vm_name, run_directory, ssh_port = _clone_and_start_run_vm(
            vboxmanage_path,
            configuration,
        )
        return VmCloneResult(
            status=VmCloneStatus.CLONE_STARTED,
            base_vm_name=configuration.vm_name,
            run_vm_name=run_vm_name,
            run_directory=run_directory,
            ssh_host=_SSH_FORWARD_HOST,
            ssh_port=ssh_port,
        )

    return VmCloneResult(
        status=VmCloneStatus.NOT_READY,
        base_vm_name=configuration.vm_name,
    )


def stop_and_remove_vm_clone(vm_name: str) -> None:
    """Stop and remove a disposable VM clone."""
    vboxmanage_path = _find_vboxmanage()
    state = _get_virtual_machine_state(vboxmanage_path, vm_name)

    if state == VirtualMachineState.NOT_CREATED:
        return

    if state == VirtualMachineState.RUNNING:
        _run_vboxmanage(vboxmanage_path, ["controlvm", vm_name, "poweroff"])
        _wait_for_virtual_machine_to_stop(vboxmanage_path, vm_name)

    _run_vboxmanage(vboxmanage_path, ["unregistervm", vm_name, "--delete"])


def finalize_base_vm(configuration: VirtualBoxConfiguration) -> BaseFinalizationResult:
    """Install base VM packages needed for Python agent execution."""
    vboxmanage_path = _find_vboxmanage()
    state = _get_virtual_machine_state(vboxmanage_path, configuration.vm_name)

    if state == VirtualMachineState.NOT_CREATED:
        return BaseFinalizationResult(
            status=BaseFinalizationStatus.MISSING,
            base_vm_name=configuration.vm_name,
        )

    if state == VirtualMachineState.OTHER:
        return BaseFinalizationResult(
            status=BaseFinalizationStatus.NOT_READY,
            base_vm_name=configuration.vm_name,
        )

    ssh_port = _find_available_host_port()

    if state == VirtualMachineState.STOPPED:
        _add_stopped_vm_nat_forward(vboxmanage_path, configuration.vm_name, ssh_port)
        _run_vboxmanage(
            vboxmanage_path,
            ["startvm", "--type=headless", configuration.vm_name],
        )
    else:
        _add_running_vm_nat_forward(vboxmanage_path, configuration.vm_name, ssh_port)

    try:
        _install_base_vm_packages(configuration, ssh_port)
        _wait_for_virtual_machine_to_stop(vboxmanage_path, configuration.vm_name)
    finally:
        _remove_base_vm_nat_forward(vboxmanage_path, configuration.vm_name)

    return BaseFinalizationResult(
        status=BaseFinalizationStatus.FINALIZED,
        base_vm_name=configuration.vm_name,
        ssh_host=_SSH_FORWARD_HOST,
        ssh_port=ssh_port,
    )


def _find_vboxmanage() -> Path:
    environment_value = os.environ.get(_VBOXMANAGE_ENVIRONMENT_VARIABLE)

    if environment_value:
        environment_path = Path(environment_value)
        if environment_path.exists():
            return environment_path

    if _WINDOWS_VBOXMANAGE_PATH.exists():
        return _WINDOWS_VBOXMANAGE_PATH

    return Path("VBoxManage")


def _get_virtual_machine_state(
    vboxmanage_path: Path,
    vm_name: str,
) -> VirtualMachineState:
    virtual_machines = _list_virtual_machines(vboxmanage_path, "vms")

    if vm_name not in {virtual_machine.name for virtual_machine in virtual_machines}:
        return VirtualMachineState.NOT_CREATED

    running_virtual_machines = _list_virtual_machines(vboxmanage_path, "runningvms")

    if vm_name in {
        virtual_machine.name for virtual_machine in running_virtual_machines
    }:
        return VirtualMachineState.RUNNING

    machine_readable_info = _run_vboxmanage(
        vboxmanage_path,
        ["showvminfo", vm_name, "--machinereadable"],
    ).stdout
    vm_state = _get_machine_readable_value(machine_readable_info, "VMState")

    if vm_state == "poweroff":
        return VirtualMachineState.STOPPED

    return VirtualMachineState.OTHER


def _list_virtual_machines(
    vboxmanage_path: Path,
    list_kind: str,
) -> list[VirtualMachine]:
    result = _run_vboxmanage(vboxmanage_path, ["list", list_kind])
    virtual_machines: list[VirtualMachine] = []

    for line in result.stdout.splitlines():
        match = _VM_LINE_PATTERN.match(line)

        if match is None:
            continue

        virtual_machine = VirtualMachine(
            name=match.group("name"),
            uuid=match.group("uuid"),
        )
        virtual_machines.append(virtual_machine)

    return virtual_machines


def _get_machine_readable_value(text: str, key: str) -> str | None:
    prefix = f'{key}="'

    for line in text.splitlines():
        if not line.startswith(prefix):
            continue

        return line.removeprefix(prefix).removesuffix('"')

    return None


def _create_missing_base_vm(
    vboxmanage_path: Path,
    configuration: VirtualBoxConfiguration,
) -> VmCloneResult:
    iso_path = _resolve_iso_path(configuration.iso_path)

    if iso_path is None:
        return VmCloneResult(
            status=VmCloneStatus.ISO_MISSING,
            base_vm_name=configuration.vm_name,
        )

    _create_base_virtual_machine(vboxmanage_path, configuration, iso_path)
    return VmCloneResult(
        status=VmCloneStatus.BASE_CREATED,
        base_vm_name=configuration.vm_name,
    )


def _resolve_iso_path(configured_path: Path | None) -> Path | None:
    if configured_path is not None:
        return _existing_path_or_none(configured_path)

    environment_value = os.environ.get(_ISO_ENVIRONMENT_VARIABLE)

    if environment_value:
        environment_path = Path(environment_value)
        resolved_environment_path = _existing_path_or_none(environment_path)

        if resolved_environment_path is not None:
            return resolved_environment_path

    return _find_downloaded_ubuntu_iso()


def _existing_path_or_none(path: Path) -> Path | None:
    resolved_path = path.expanduser().resolve()

    if resolved_path.exists():
        return resolved_path

    return None


def _find_downloaded_ubuntu_iso() -> Path | None:
    downloads_directory = Path.home() / "Downloads"

    if not downloads_directory.exists():
        return None

    patterns = [
        "ubuntu-24.04*-live-server-amd64.iso",
        "ubuntu-*-live-server-amd64.iso",
    ]
    candidates: list[Path] = []

    for pattern in patterns:
        candidates.extend(downloads_directory.glob(pattern))

    if not candidates:
        return None

    return max(candidates, key=lambda candidate: candidate.stat().st_mtime)


def _create_base_virtual_machine(
    vboxmanage_path: Path,
    configuration: VirtualBoxConfiguration,
    iso_path: Path,
) -> None:
    configuration.base_directory.mkdir(parents=True, exist_ok=True)
    disk_path = configuration.base_directory / f"{configuration.vm_name}.vdi"

    commands = [
        [
            "createvm",
            f"--name={configuration.vm_name}",
            "--platform-architecture=x86",
            f"--ostype={_DEFAULT_OS_TYPE}",
            f"--basefolder={configuration.base_directory}",
            "--register",
        ],
        [
            "modifyvm",
            configuration.vm_name,
            f"--memory={configuration.memory_megabytes}",
            f"--cpus={configuration.cpu_count}",
            "--nic1=nat",
            "--graphicscontroller=vmsvga",
            "--vram=32",
            "--audio-enabled=off",
            "--clipboard-mode=disabled",
            "--drag-and-drop=disabled",
        ],
        [
            "createmedium",
            "disk",
            f"--filename={disk_path}",
            f"--size={configuration.disk_size_megabytes}",
            "--format=VDI",
        ],
        [
            "storagectl",
            configuration.vm_name,
            "--name=SATA Controller",
            "--add=sata",
            "--controller=IntelAhci",
        ],
        [
            "storageattach",
            configuration.vm_name,
            "--storagectl=SATA Controller",
            "--port=0",
            "--device=0",
            "--type=hdd",
            f"--medium={disk_path}",
        ],
        [
            "unattended",
            "install",
            configuration.vm_name,
            f"--iso={iso_path}",
            f"--user={configuration.guest_credentials.user}",
            f"--user-password={configuration.guest_credentials.password}",
            f"--admin-password={configuration.guest_credentials.password}",
            f"--full-user-name={configuration.guest_credentials.user}",
            "--locale=en_US",
            "--country=US",
            "--time-zone=UTC",
            f"--hostname={configuration.hostname}",
            "--package-selection-adjustment=minimal",
            "--no-install-additions",
            f"--post-install-command={_ENABLE_OPENSSH_COMMAND}",
            "--start-vm=headless",
        ],
    ]

    for command in commands:
        _run_vboxmanage(vboxmanage_path, command)


def _clone_and_start_run_vm(
    vboxmanage_path: Path,
    configuration: VirtualBoxConfiguration,
) -> tuple[str, Path, int]:
    timestamp = dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    run_vm_name = f"{_RUN_VM_NAME_PREFIX} {timestamp}"
    run_directory = configuration.base_directory / "runs" / f"run-{timestamp}"
    ssh_port = _find_available_host_port()
    run_directory.mkdir(parents=True, exist_ok=True)

    _run_vboxmanage(
        vboxmanage_path,
        [
            "clonevm",
            configuration.vm_name,
            f"--name={run_vm_name}",
            f"--basefolder={run_directory}",
            "--mode=machine",
            "--register",
        ],
    )
    _run_vboxmanage(
        vboxmanage_path,
        [
            "modifyvm",
            run_vm_name,
            f"--nat-pf1={_SSH_FORWARD_NAME},tcp,{_SSH_FORWARD_HOST},{ssh_port},,22",
        ],
    )
    _run_vboxmanage(
        vboxmanage_path,
        [
            "startvm",
            "--type=headless",
            run_vm_name,
        ],
    )
    return run_vm_name, run_directory, ssh_port


def _find_available_host_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((_SSH_FORWARD_HOST, 0))
        _, port = server_socket.getsockname()
        return int(port)


def _add_stopped_vm_nat_forward(
    vboxmanage_path: Path,
    vm_name: str,
    ssh_port: int,
) -> None:
    _remove_base_vm_nat_forward(vboxmanage_path, vm_name)
    _run_vboxmanage(
        vboxmanage_path,
        [
            "modifyvm",
            vm_name,
            f"--nat-pf1={_BASE_SSH_FORWARD_NAME},tcp,{_SSH_FORWARD_HOST},{ssh_port},,22",
        ],
    )


def _add_running_vm_nat_forward(
    vboxmanage_path: Path,
    vm_name: str,
    ssh_port: int,
) -> None:
    _remove_base_vm_nat_forward(vboxmanage_path, vm_name)
    _run_vboxmanage(
        vboxmanage_path,
        [
            "controlvm",
            vm_name,
            "natpf1",
            f"{_BASE_SSH_FORWARD_NAME},tcp,{_SSH_FORWARD_HOST},{ssh_port},,22",
        ],
    )


def _remove_base_vm_nat_forward(vboxmanage_path: Path, vm_name: str) -> None:
    state = _get_virtual_machine_state(vboxmanage_path, vm_name)

    if state == VirtualMachineState.NOT_CREATED:
        return

    if state == VirtualMachineState.RUNNING:
        command = ["controlvm", vm_name, "natpf1delete", _BASE_SSH_FORWARD_NAME]
    else:
        command = ["modifyvm", vm_name, "--nat-pf1", "delete", _BASE_SSH_FORWARD_NAME]

    try:
        _run_vboxmanage(vboxmanage_path, command)
    except RuntimeError:
        pass


def _install_base_vm_packages(
    configuration: VirtualBoxConfiguration,
    ssh_port: int,
) -> None:
    client = _wait_for_ssh(configuration, ssh_port)

    try:
        _run_sudo_command(
            client,
            configuration.guest_credentials.password,
            "apt-get update",
        )
        packages = " ".join(shlex.quote(package) for package in _FINALIZE_BASE_PACKAGES)
        _run_sudo_command(
            client,
            configuration.guest_credentials.password,
            f"env DEBIAN_FRONTEND=noninteractive apt-get install -y {packages}",
        )
        _run_sudo_command(
            client,
            configuration.guest_credentials.password,
            "shutdown now",
        )
    finally:
        client.close()


def _wait_for_ssh(
    configuration: VirtualBoxConfiguration,
    ssh_port: int,
) -> paramiko.SSHClient:
    timeout_seconds = 180
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            _wait_for_ssh_banner(ssh_port)
            return _connect_ssh(configuration, ssh_port)
        except (
            OSError,
            _SshNotReadyError,
            paramiko.AuthenticationException,
            paramiko.SSHException,
        ) as error:
            last_error = error
            time.sleep(2)

    raise RuntimeError(
        f"Timed out waiting for SSH on base VM '{configuration.vm_name}': {last_error}"
    )


def _wait_for_ssh_banner(ssh_port: int) -> None:
    with socket.create_connection((_SSH_FORWARD_HOST, ssh_port), timeout=5) as client:
        client.settimeout(5)
        banner = _read_ssh_banner(client)

    if not banner.startswith("SSH-"):
        raise _SshNotReadyError(f"Port was reachable but did not speak SSH: {banner}")


def _read_ssh_banner(client: socket.socket) -> str:
    chunks: list[bytes] = []

    while sum(len(chunk) for chunk in chunks) < 255:
        chunk = client.recv(1)
        if not chunk:
            break

        chunks.append(chunk)
        if chunk == b"\n":
            break

    return b"".join(chunks).decode("utf-8", errors="replace").strip()


def _connect_ssh(
    configuration: VirtualBoxConfiguration,
    ssh_port: int,
) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=_SSH_FORWARD_HOST,
        port=ssh_port,
        username=configuration.guest_credentials.user,
        password=configuration.guest_credentials.password,
        look_for_keys=False,
        allow_agent=False,
        timeout=10,
        banner_timeout=10,
        auth_timeout=10,
    )
    return client


def _run_sudo_command(
    client: paramiko.SSHClient,
    password: str,
    command: str,
) -> None:
    quoted_password = shlex.quote(password)
    remote_command = f"printf '%s\\n' {quoted_password} | sudo -S {command}"
    _, stdout, stderr = client.exec_command(remote_command)
    exit_code = stdout.channel.recv_exit_status()
    stdout_text = stdout.read().decode("utf-8", errors="replace").strip()
    stderr_text = stderr.read().decode("utf-8", errors="replace").strip()

    if exit_code != 0:
        raise RuntimeError(
            f"Remote sudo command failed with exit code {exit_code}: {command}\n"
            f"stdout:\n{stdout_text}\n"
            f"stderr:\n{stderr_text}"
        )


def _wait_for_virtual_machine_to_stop(vboxmanage_path: Path, vm_name: str) -> None:
    timeout_seconds = 180
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        state = _get_virtual_machine_state(vboxmanage_path, vm_name)

        if state != VirtualMachineState.RUNNING:
            return

        time.sleep(1)

    raise RuntimeError(f"VM did not stop within {timeout_seconds} seconds: {vm_name}")


def _run_vboxmanage(
    vboxmanage_path: Path,
    arguments: list[str],
) -> subprocess.CompletedProcess[str]:
    command = [str(vboxmanage_path), *arguments]
    result = subprocess.run(
        command,
        capture_output=True,
        check=False,
        encoding="utf-8",
    )

    if result.returncode != 0:
        command_text = " ".join(command)
        message = (
            f"VBoxManage command failed with exit code {result.returncode}: "
            f"{command_text}\n{result.stderr}"
        )
        raise RuntimeError(message)

    return result
