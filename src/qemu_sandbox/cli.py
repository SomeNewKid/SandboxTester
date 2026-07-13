"""Command-line interface for QEMU sandbox experiments."""

from __future__ import annotations

import argparse
from pathlib import Path

from virtualbox_sandbox.agent_profiles import SUPPORTED_AGENT_NAMES

from .credentials import load_or_create_guest_credentials
from .models import QemuConfiguration, QemuRunResult, QemuRunStatus
from .qemu_machine_factory import create_qemu_run, stop_and_remove_qemu_run
from .run_results import save_run_results
from .virtual_machine_setup import QemuVirtualMachineSetup

_DEFAULT_BASE_DIRECTORY = Path(".qemu_sandbox")
_DEFAULT_BASE_IMAGE_NAME = "ubuntu-24.04-sandbox-base.clean.qcow2"
_DEFAULT_GUEST_USER = "sandbox"
_DEFAULT_MACHINE = "q35"
_DEFAULT_ACCELERATOR = "auto"
_DEFAULT_CPU = "qemu64"
_DEFAULT_MEMORY_MEGABYTES = 4_096
_DEFAULT_CPU_COUNT = 2


def main() -> int:
    """Run the command-line interface."""
    arguments = _parse_arguments()
    configuration = _configuration_from_arguments(arguments)
    result = create_qemu_run(configuration)
    _print_result(result)

    if result.status != QemuRunStatus.STARTED:
        return _exit_code_from_result(result)

    _setup_run_if_started(
        result,
        configuration,
        keep_vm=arguments.keep_vm,
        agent_name=arguments.agent,
        agent_verbose=arguments.verbose,
        agent_serialize_evidence=arguments.serialize_evidence,
    )
    return _exit_code_from_result(result)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Sandbox Tester in a disposable QEMU VM."
    )
    parser.add_argument(
        "--base-directory",
        type=Path,
        default=_DEFAULT_BASE_DIRECTORY,
        help=(
            f"Host directory for QEMU sandbox files. Default: {_DEFAULT_BASE_DIRECTORY}"
        ),
    )
    parser.add_argument(
        "--base-image",
        type=Path,
        default=None,
        help=(
            "Reusable base qcow2 image. Defaults to "
            f"{_DEFAULT_BASE_DIRECTORY / _DEFAULT_BASE_IMAGE_NAME}."
        ),
    )
    parser.add_argument(
        "--qemu",
        type=Path,
        default=Path("qemu-system-x86_64"),
        help="Path to qemu-system-x86_64.",
    )
    parser.add_argument(
        "--machine",
        default=_DEFAULT_MACHINE,
        help=f"QEMU machine type. Default: {_DEFAULT_MACHINE}",
    )
    parser.add_argument(
        "--accelerator",
        default=_DEFAULT_ACCELERATOR,
        help=f"QEMU accelerator. Default: {_DEFAULT_ACCELERATOR}",
    )
    parser.add_argument(
        "--cpu",
        default=_DEFAULT_CPU,
        help=f"QEMU CPU model. Default: {_DEFAULT_CPU}",
    )
    parser.add_argument(
        "--memory-mb",
        type=int,
        default=_DEFAULT_MEMORY_MEGABYTES,
        help=f"Guest memory in megabytes. Default: {_DEFAULT_MEMORY_MEGABYTES}",
    )
    parser.add_argument(
        "--cpus",
        type=int,
        default=_DEFAULT_CPU_COUNT,
        help=f"Guest CPU count. Default: {_DEFAULT_CPU_COUNT}",
    )
    parser.add_argument(
        "--guest-user",
        default=_DEFAULT_GUEST_USER,
        help=f"Guest login user. Default: {_DEFAULT_GUEST_USER}",
    )
    parser.add_argument(
        "--keep-vm",
        action="store_true",
        help="Keep the disposable QEMU VM running after execution.",
    )
    parser.add_argument(
        "--agent",
        choices=SUPPORTED_AGENT_NAMES,
        default="sandbox_tester",
        help="Python agent profile to upload, install, and run in the QEMU VM.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Pass verbose progress output through to the selected Python agent.",
    )
    parser.add_argument(
        "--serialize-evidence",
        action="store_true",
        help="Pass --serialize-evidence through to the sandbox_tester agent.",
    )
    return parser.parse_args()


def _configuration_from_arguments(arguments: argparse.Namespace) -> QemuConfiguration:
    base_directory = arguments.base_directory.resolve()
    base_image_path = _resolve_base_image_path(base_directory, arguments.base_image)
    credentials = load_or_create_guest_credentials(
        base_directory,
        arguments.guest_user,
    )

    return QemuConfiguration(
        base_directory=base_directory,
        base_image_path=base_image_path,
        qemu_path=arguments.qemu,
        guest_credentials=credentials,
        machine=arguments.machine,
        accelerator=arguments.accelerator,
        cpu=arguments.cpu,
        memory_megabytes=arguments.memory_mb,
        cpu_count=arguments.cpus,
    )


def _resolve_base_image_path(
    base_directory: Path,
    configured_base_image: Path | None,
) -> Path:
    if configured_base_image is not None:
        return configured_base_image.expanduser().resolve()

    return (base_directory / _DEFAULT_BASE_IMAGE_NAME).resolve()


def _print_result(result: QemuRunResult) -> None:
    if result.status == QemuRunStatus.QEMU_MISSING:
        print("qemu-system-x86_64 was not found.")
        return

    if result.status == QemuRunStatus.BASE_IMAGE_MISSING:
        print(f"Base QEMU image was not found: {result.base_image_path}")
        return

    print(f"Started disposable QEMU VM using disk: {result.run_disk_path}")


def _setup_run_if_started(
    result: QemuRunResult,
    configuration: QemuConfiguration,
    keep_vm: bool,
    agent_name: str,
    agent_verbose: bool,
    agent_serialize_evidence: bool,
) -> None:
    if result.run_directory is None:
        raise RuntimeError("QEMU run result did not include a run directory.")

    if result.ssh_host is None or result.ssh_port is None:
        raise RuntimeError("QEMU run result did not include SSH connection details.")

    setup = QemuVirtualMachineSetup(
        result.ssh_host,
        result.ssh_port,
        configuration.guest_credentials,
        agent_name=agent_name,
        agent_verbose=agent_verbose,
        agent_serialize_evidence=agent_serialize_evidence,
    )

    try:
        setup_result = setup.setup()
        save_run_results(result.run_directory, result, setup_result)
        print(f"Remote Python probe completed with exit code {setup_result.exit_code}.")
        print(f"Run results saved to: {result.run_directory}")
        print(f"Remote stdout saved to: {result.run_directory / 'stdout.txt'}")
        if setup_result.stderr:
            print(f"Remote stderr saved to: {result.run_directory / 'stderr.txt'}")
    finally:
        if keep_vm:
            print(f"Kept disposable QEMU VM on port {result.ssh_port}.")
        else:
            try:
                setup.shutdown()
            finally:
                stop_and_remove_qemu_run(result)
            print("Stopped and removed disposable QEMU VM.")


def _exit_code_from_result(result: QemuRunResult) -> int:
    if result.status == QemuRunStatus.STARTED:
        return 0

    return 1
