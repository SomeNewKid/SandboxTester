"""Command-line interface for VirtualBox sandbox experiments."""

from __future__ import annotations

import argparse
from pathlib import Path

from .agent_profiles import SUPPORTED_AGENT_NAMES
from .credentials import load_or_create_guest_credentials
from .models import (
    BaseFinalizationResult,
    BaseFinalizationStatus,
    VirtualBoxConfiguration,
    VmCloneResult,
    VmCloneStatus,
)
from .run_results import save_run_results
from .virtual_machine_factory import (
    create_vm_clone,
    finalize_base_vm,
    stop_and_remove_vm_clone,
)
from .virtual_machine_setup import VirtualMachineSetup

_DEFAULT_VM_NAME = "Sandbox Tester Base"
_DEFAULT_GUEST_USER = "sandbox"
_DEFAULT_HOSTNAME = "sandbox-tester-base.local"
_DEFAULT_BASE_DIRECTORY = Path(".virtualbox_sandbox")
_DEFAULT_DISK_SIZE_MEGABYTES = 8_192
_DEFAULT_MEMORY_MEGABYTES = 2_048
_DEFAULT_CPU_COUNT = 2
_ISO_ENVIRONMENT_VARIABLE = "SANDBOX_TESTER_ISO"


def main() -> int:
    """Run the command-line interface."""
    arguments = _parse_arguments()
    configuration = _configuration_from_arguments(arguments)

    if arguments.finalize_base:
        result = finalize_base_vm(configuration)
        _print_base_finalization_result(result)
        return _exit_code_from_base_finalization_result(result)

    result = create_vm_clone(configuration)
    _print_result(result)
    _setup_clone_if_started(
        result,
        configuration,
        keep_vm=arguments.keep_vm,
        script_path=arguments.script,
        source_directory=arguments.source_directory,
        agent_name=arguments.agent,
    )
    return _exit_code_from_result(result)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or clone VirtualBox VMs for sandbox experiments."
    )
    parser.add_argument(
        "--vm-name",
        default=_DEFAULT_VM_NAME,
        help=f"Name of the golden/base VM. Default: {_DEFAULT_VM_NAME}",
    )
    parser.add_argument(
        "--iso",
        type=Path,
        default=None,
        help=(
            "Path to an Ubuntu Server installer ISO. If omitted, the CLI checks "
            f"{_ISO_ENVIRONMENT_VARIABLE} and then the Downloads directory."
        ),
    )
    parser.add_argument(
        "--base-directory",
        type=Path,
        default=_DEFAULT_BASE_DIRECTORY,
        help=(
            f"Host directory for generated VM files. Default: {_DEFAULT_BASE_DIRECTORY}"
        ),
    )
    parser.add_argument(
        "--disk-size-mb",
        type=int,
        default=_DEFAULT_DISK_SIZE_MEGABYTES,
        help=f"Virtual disk size in megabytes. Default: {_DEFAULT_DISK_SIZE_MEGABYTES}",
    )
    parser.add_argument(
        "--memory-mb",
        type=int,
        default=_DEFAULT_MEMORY_MEGABYTES,
        help=f"VM memory in megabytes. Default: {_DEFAULT_MEMORY_MEGABYTES}",
    )
    parser.add_argument(
        "--cpus",
        type=int,
        default=_DEFAULT_CPU_COUNT,
        help=f"VM CPU count. Default: {_DEFAULT_CPU_COUNT}",
    )
    parser.add_argument(
        "--guest-user",
        default=_DEFAULT_GUEST_USER,
        help=f"Guest login user. Default: {_DEFAULT_GUEST_USER}",
    )
    parser.add_argument(
        "--hostname",
        default=_DEFAULT_HOSTNAME,
        help=f"Guest hostname. Default: {_DEFAULT_HOSTNAME}",
    )
    parser.add_argument(
        "--keep-vm",
        action="store_true",
        help="Keep the disposable VM after setup instead of stopping and removing it.",
    )
    parser.add_argument(
        "--script",
        type=Path,
        default=None,
        help="Local Python script to upload and run in the disposable VM.",
    )
    parser.add_argument(
        "--source-directory",
        type=Path,
        default=None,
        help=(
            "Local source tree to upload and add to PYTHONPATH for the guest script."
        ),
    )
    parser.add_argument(
        "--agent",
        choices=SUPPORTED_AGENT_NAMES,
        default=None,
        help="Python agent profile to upload, install, and run in the disposable VM.",
    )
    parser.add_argument(
        "--finalize-base",
        action="store_true",
        help=(
            "Start the base VM, install Python agent support packages, shut it "
            "down, and remove the temporary SSH port forward."
        ),
    )
    arguments = parser.parse_args()
    _validate_arguments(parser, arguments)
    return arguments


def _validate_arguments(
    parser: argparse.ArgumentParser,
    arguments: argparse.Namespace,
) -> None:
    if arguments.finalize_base:
        if (
            arguments.agent is not None
            or arguments.script is not None
            or arguments.source_directory is not None
            or arguments.keep_vm
        ):
            parser.error(
                "--finalize-base cannot be combined with --agent, --script, "
                "--source-directory, or --keep-vm."
            )
        return

    if arguments.agent is None:
        return

    if arguments.script is not None or arguments.source_directory is not None:
        parser.error("--agent cannot be combined with --script or --source-directory.")


def _configuration_from_arguments(
    arguments: argparse.Namespace,
) -> VirtualBoxConfiguration:
    base_directory = arguments.base_directory.resolve()
    credentials = load_or_create_guest_credentials(base_directory, arguments.guest_user)

    return VirtualBoxConfiguration(
        vm_name=arguments.vm_name,
        iso_path=arguments.iso,
        base_directory=base_directory,
        disk_size_megabytes=arguments.disk_size_mb,
        memory_megabytes=arguments.memory_mb,
        cpu_count=arguments.cpus,
        guest_credentials=credentials,
        hostname=arguments.hostname,
    )


def _print_result(result: VmCloneResult) -> None:
    if result.status == VmCloneStatus.BASE_CREATED:
        print(
            f"Base VM '{result.base_vm_name}' has been created and Ubuntu "
            "installation has been started. Wait for the installation to complete, "
            "then shut down the base VM and run this command again."
        )
        return

    if result.status == VmCloneStatus.BASE_RUNNING:
        print(
            f"Base VM '{result.base_vm_name}' is running. If Ubuntu is still "
            "installing, wait for installation to complete. Once installation "
            "is complete, shut down the base VM and run this command again."
        )
        return

    if result.status == VmCloneStatus.CLONE_STARTED:
        print(
            f"Started disposable run VM '{result.run_vm_name}'. Configuring "
            "the clone now."
        )
        return

    if result.status == VmCloneStatus.ISO_MISSING:
        print(
            "Base VM does not exist, and no installer ISO was found. "
            f"Pass --iso or set {_ISO_ENVIRONMENT_VARIABLE}."
        )
        return

    print(
        f"Base VM '{result.base_vm_name}' exists but is not ready to clone. "
        "Open VirtualBox, shut it down cleanly, and run this command again."
    )


def _print_base_finalization_result(result: BaseFinalizationResult) -> None:
    if result.status == BaseFinalizationStatus.FINALIZED:
        print(
            f"Base VM '{result.base_vm_name}' was finalized and shut down. "
            "Temporary SSH port forwarding was removed."
        )
        return

    if result.status == BaseFinalizationStatus.MISSING:
        print(
            f"Base VM '{result.base_vm_name}' does not exist. Run without "
            "--finalize-base first to create and install it."
        )
        return

    print(
        f"Base VM '{result.base_vm_name}' exists but is not ready to finalize. "
        "Open VirtualBox, shut it down cleanly or inspect its state, then run "
        "this command again."
    )


def _exit_code_from_result(result: VmCloneResult) -> int:
    if result.status == VmCloneStatus.ISO_MISSING:
        return 2

    if result.status == VmCloneStatus.NOT_READY:
        return 1

    return 0


def _exit_code_from_base_finalization_result(result: BaseFinalizationResult) -> int:
    if result.status == BaseFinalizationStatus.FINALIZED:
        return 0

    return 1


def _setup_clone_if_started(
    result: VmCloneResult,
    configuration: VirtualBoxConfiguration,
    keep_vm: bool,
    script_path: Path | None,
    source_directory: Path | None,
    agent_name: str | None,
) -> None:
    if result.status != VmCloneStatus.CLONE_STARTED:
        return

    if result.run_vm_name is None:
        raise RuntimeError("VM clone result did not include a run VM name.")

    if result.ssh_host is None or result.ssh_port is None:
        raise RuntimeError("VM clone result did not include SSH connection details.")

    if result.run_directory is None:
        raise RuntimeError("VM clone result did not include a run directory.")

    setup = VirtualMachineSetup(
        result.run_vm_name,
        result.ssh_host,
        result.ssh_port,
        configuration.guest_credentials.user,
        configuration.guest_credentials.password,
        script_path=script_path,
        source_directory=source_directory,
        agent_name=agent_name,
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
            print(f"Kept disposable run VM '{result.run_vm_name}'.")
        else:
            stop_and_remove_vm_clone(result.run_vm_name)
            print(f"Stopped and removed disposable run VM '{result.run_vm_name}'.")
