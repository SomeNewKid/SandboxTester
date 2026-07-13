"""Create and start QEMU sandbox virtual machines."""

from __future__ import annotations

import datetime as dt
import os
import shutil
import socket
import subprocess
import time
from dataclasses import replace
from pathlib import Path

from .models import QemuConfiguration, QemuRunResult, QemuRunStatus

_QEMU_ENVIRONMENT_VARIABLE = "QEMU_SYSTEM_X86_64"
_WINDOWS_QEMU_PATH = Path(r"C:\Program Files\qemu\qemu-system-x86_64.exe")
_RUN_DISK_FILE_NAME = "ubuntu-24.04-sandbox-run.qcow2"
_SSH_FORWARD_HOST = "127.0.0.1"


def create_qemu_run(configuration: QemuConfiguration) -> QemuRunResult:
    """Copy the base disk image and start a disposable QEMU VM."""
    qemu_path = _find_qemu(configuration.qemu_path)

    if qemu_path is None:
        return QemuRunResult(
            status=QemuRunStatus.QEMU_MISSING,
            base_image_path=configuration.base_image_path,
        )

    if not configuration.base_image_path.exists():
        return QemuRunResult(
            status=QemuRunStatus.BASE_IMAGE_MISSING,
            base_image_path=configuration.base_image_path,
            qemu_path=qemu_path,
        )

    resolved_configuration = replace(
        configuration,
        accelerator=_resolve_accelerator(qemu_path, configuration.accelerator),
    )
    timestamp = dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    run_directory = resolved_configuration.base_directory / "runs" / f"run-{timestamp}"
    run_directory.mkdir(parents=True, exist_ok=True)
    run_disk_path = run_directory / _RUN_DISK_FILE_NAME
    shutil.copy2(resolved_configuration.base_image_path, run_disk_path)
    ssh_port = _find_available_host_port()
    command = _build_qemu_command(
        resolved_configuration,
        qemu_path,
        run_disk_path,
        ssh_port,
    )
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    if process.poll() is not None:
        raise RuntimeError(
            f"QEMU exited immediately with exit code {process.returncode}."
        )

    return QemuRunResult(
        status=QemuRunStatus.STARTED,
        base_image_path=resolved_configuration.base_image_path,
        qemu_path=qemu_path,
        run_directory=run_directory,
        run_disk_path=run_disk_path,
        ssh_host=_SSH_FORWARD_HOST,
        ssh_port=ssh_port,
        process=process,
        command=command,
    )


def stop_and_remove_qemu_run(result: QemuRunResult) -> None:
    """Stop a disposable QEMU VM process and remove its copied disk."""
    stop_qemu_run(result)
    _remove_run_disk(result)


def stop_qemu_run(result: QemuRunResult) -> None:
    """Stop a disposable QEMU VM process if it is still running."""
    process = result.process

    if process is None:
        return

    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=30)


def _remove_run_disk(result: QemuRunResult) -> None:
    run_directory = result.run_directory
    run_disk_path = result.run_disk_path

    if run_directory is None or run_disk_path is None:
        return

    resolved_run_directory = run_directory.resolve()
    resolved_run_disk_path = run_disk_path.resolve()

    if resolved_run_directory not in resolved_run_disk_path.parents:
        raise RuntimeError(
            "Refusing to remove QEMU run disk outside the run directory: "
            f"{resolved_run_disk_path}"
        )

    if resolved_run_disk_path.exists():
        resolved_run_disk_path.unlink()


def _find_qemu(configured_path: Path) -> Path | None:
    if str(configured_path):
        resolved_path = configured_path.expanduser().resolve()
        if resolved_path.exists():
            return resolved_path

    environment_value = os.environ.get(_QEMU_ENVIRONMENT_VARIABLE)
    if environment_value:
        environment_path = Path(environment_value).expanduser().resolve()
        if environment_path.exists():
            return environment_path

    if _WINDOWS_QEMU_PATH.exists():
        return _WINDOWS_QEMU_PATH

    discovered_path = shutil.which("qemu-system-x86_64")
    if discovered_path is None:
        return None

    return Path(discovered_path)


def _resolve_accelerator(qemu_path: Path, configured_accelerator: str) -> str:
    if configured_accelerator != "auto":
        return configured_accelerator

    supported_accelerators = _get_supported_accelerators(qemu_path)

    if "whpx" in supported_accelerators:
        return "whpx"

    return "tcg"


def _get_supported_accelerators(qemu_path: Path) -> set[str]:
    completed = subprocess.run(
        [str(qemu_path), "-accel", "help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        return set()

    return {
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip() and not line.startswith("Accelerators")
    }


def _build_qemu_command(
    configuration: QemuConfiguration,
    qemu_path: Path,
    run_disk_path: Path,
    ssh_port: int,
) -> list[str]:
    if configuration.machine == "microvm":
        return _build_microvm_qemu_command(
            configuration,
            qemu_path,
            run_disk_path,
            ssh_port,
        )

    return _build_pc_qemu_command(
        configuration,
        qemu_path,
        run_disk_path,
        ssh_port,
    )


def _build_pc_qemu_command(
    configuration: QemuConfiguration,
    qemu_path: Path,
    run_disk_path: Path,
    ssh_port: int,
) -> list[str]:
    host_forward = f"tcp:{_SSH_FORWARD_HOST}:{ssh_port}-:22"
    return [
        str(qemu_path),
        "-machine",
        f"{configuration.machine},accel={configuration.accelerator}",
        "-cpu",
        configuration.cpu,
        "-m",
        str(configuration.memory_megabytes),
        "-smp",
        str(configuration.cpu_count),
        "-drive",
        f"file={run_disk_path},format=qcow2,if=virtio",
        "-netdev",
        f"user,id=net0,hostfwd={host_forward}",
        "-device",
        "virtio-net-pci,netdev=net0",
        "-display",
        "none",
    ]


def _build_microvm_qemu_command(
    configuration: QemuConfiguration,
    qemu_path: Path,
    run_disk_path: Path,
    ssh_port: int,
) -> list[str]:
    if configuration.kernel_path is None:
        raise ValueError("--kernel is required for QEMU microvm mode.")

    if configuration.initrd_path is None:
        raise ValueError("--initrd is required for QEMU microvm mode.")

    if configuration.kernel_append is None:
        raise ValueError("--kernel-append is required for QEMU microvm mode.")

    host_forward = f"tcp:{_SSH_FORWARD_HOST}:{ssh_port}-:22"
    serial_log_path = run_disk_path.parent / "serial.log"
    return [
        str(qemu_path),
        "-M",
        f"microvm,accel={configuration.accelerator}",
        "-cpu",
        configuration.cpu,
        "-m",
        str(configuration.memory_megabytes),
        "-smp",
        str(configuration.cpu_count),
        "-kernel",
        str(configuration.kernel_path),
        "-initrd",
        str(configuration.initrd_path),
        "-append",
        configuration.kernel_append,
        "-nodefaults",
        "-no-user-config",
        "-display",
        "none",
        "-serial",
        f"file:{serial_log_path}",
        "-no-reboot",
        "-drive",
        f"id=root,file={run_disk_path},format=qcow2,if=none",
        "-device",
        "virtio-blk-device,drive=root",
        "-netdev",
        f"user,id=net0,hostfwd={host_forward}",
        "-device",
        "virtio-net-device,netdev=net0",
    ]


def _find_available_host_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((_SSH_FORWARD_HOST, 0))
        _, port = server_socket.getsockname()
        return int(port)
