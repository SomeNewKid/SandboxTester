"""Tests for the Docker sandbox harness."""

import json
from pathlib import Path

import pytest

from docker_sandbox.cli import main
from docker_sandbox.container_factory import _build_image_command
from docker_sandbox.models import (
    AgentSocketForward,
    BrowserDebuggingProfile,
    BrowserSurfaceProfile,
    DockerConfiguration,
    DockerProfile,
    LandlockPathRule,
    NetworkDnsPolicy,
    SeccompProfile,
    SocketMount,
)
from docker_sandbox.profiles import (
    AMBIENT_SERVICES_IMAGE_NAME,
    BASELINE_IMAGE_NAME,
    BROWSER_SURFACE_IMAGE_NAME,
    DNS_PROXY_CONTROL_IMAGE_NAME,
    EXECUTION_CONTROL_IMAGE_NAME,
    FILESYSTEM_VISIBILITY_IMAGE_NAME,
    MINIMIZED_IMAGE_IMAGE_NAME,
    NETWORK_EGRESS_IMAGE_NAME,
    READONLY_FS_IMAGE_NAME,
    RESOURCE_LIMITS_IMAGE_NAME,
    SYSCALL_CONTROL_IMAGE_NAME,
    get_docker_profile,
)
from docker_sandbox.sandbox_container import (
    _build_allowed_gateway_domains,
    _build_allowed_gateway_ip_addresses,
    _build_config_json,
    _build_container_script,
    _build_docker_run_command,
    _build_gateway_start_commands,
    _build_squid_configuration_text,
    _delete_denied_executable_directory,
    _delete_readonly_denied_directory,
    _prepare_denied_executable_stubs,
    _prepare_readonly_denied_directory,
    _resolve_environment_variables,
    _write_landlock_policy,
    _write_seccomp_profile,
)


def _create_configuration(
    tmp_path: Path,
    profile: DockerProfile | None = None,
) -> DockerConfiguration:
    return DockerConfiguration(
        base_directory=tmp_path / ".docker_sandbox",
        dockerfile_path=tmp_path / "Dockerfile",
        build_context=tmp_path,
        guest_user="sandbox",
        profile=profile or get_docker_profile("baseline"),
    )


def test_docker_build_command_uses_configured_image_and_dockerfile(
    tmp_path: Path,
) -> None:
    """Verify the Docker build command uses the configured inputs."""
    configuration = _create_configuration(tmp_path)

    command = _build_image_command(configuration)

    assert command == [
        "docker",
        "build",
        "--file",
        str(tmp_path / "Dockerfile"),
        "--tag",
        BASELINE_IMAGE_NAME,
        str(tmp_path),
    ]


def test_docker_build_command_includes_profile_build_arguments(
    tmp_path: Path,
) -> None:
    """Verify profiles can add Docker image build options."""
    profile = DockerProfile(
        name="test-profile",
        description="Test profile.",
        image_name="sandbox-tester/docker-sandbox:test",
        image_build_arguments=("--build-arg", "EXAMPLE=1"),
    )
    configuration = _create_configuration(tmp_path, profile)

    command = _build_image_command(configuration)

    assert command == [
        "docker",
        "build",
        "--file",
        str(tmp_path / "Dockerfile"),
        "--tag",
        "sandbox-tester/docker-sandbox:test",
        "--build-arg",
        "EXAMPLE=1",
        str(tmp_path),
    ]


def test_dockerfile_installs_dependencies_without_copying_source() -> None:
    """Verify the Docker image does not bake sandbox_tester source code."""
    dockerfile_text = Path("src/docker_sandbox/dockerfile/Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "ARG SANDBOX_MINIMIZE_IMAGE=false" in dockerfile_text
    assert "SANDBOX_MINIMIZE_IMAGE" in dockerfile_text
    assert "apt-get purge --yes --auto-remove" in dockerfile_text
    assert "/usr/bin/apt-get" in dockerfile_text
    assert "COPY src" not in dockerfile_text
    assert "pip install --no-cache-dir -e ." not in dockerfile_text
    assert "pip install --no-cache-dir openai paramiko pillow playwright pymysql" in (
        dockerfile_text
    )


def test_main_fails_when_configured_dockerfile_is_missing(tmp_path: Path) -> None:
    """Verify the CLI fails before Docker calls when the Dockerfile is missing."""
    exit_code = main(
        [
            "--base-directory",
            str(tmp_path / ".docker_sandbox"),
            "--dockerfile",
            str(tmp_path / "missing.Dockerfile"),
        ]
    )

    assert exit_code == 1


def test_main_rejects_direct_image_override(tmp_path: Path) -> None:
    """Verify Docker image selection is controlled by the selected profile."""
    with pytest.raises(SystemExit):
        main(
            [
                "--base-directory",
                str(tmp_path / ".docker_sandbox"),
                "--image",
                "sandbox-tester/docker-sandbox:custom",
            ]
        )


def test_docker_run_command_uses_disposable_container_and_output_mount(
    tmp_path: Path,
) -> None:
    """Verify the Docker run command uses a named disposable container."""
    configuration = _create_configuration(tmp_path)
    run_directory = tmp_path / ".docker_sandbox" / "runs" / "run-test"

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=run_directory,
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
        verbose=True,
        serialize_evidence=True,
    )

    assert command[:10] == [
        "docker",
        "run",
        "--name",
        "sandbox-tester-run-test",
        "--init",
        "--ipc=host",
        "--mount",
        f"type=bind,source={run_directory},target=/sandbox-output",
        "--mount",
        f"type=bind,source={tmp_path / 'src'},target=/sandbox-source/src,readonly",
    ]
    assert "--user" in command
    assert "sandbox" in command
    assert "PYTHONPATH=/sandbox-source/src" in command
    assert BASELINE_IMAGE_NAME in command
    assert "--verbose" in command[-1]
    assert "--serialize-evidence" in command[-1]


def test_docker_run_command_includes_profile_container_options(
    tmp_path: Path,
) -> None:
    """Verify profiles can add Docker container hardening options."""
    profile = DockerProfile(
        name="test-profile",
        description="Test profile.",
        image_name="sandbox-tester/docker-sandbox:test",
        container_run_options=("--read-only", "--cap-drop=ALL"),
    )
    configuration = _create_configuration(tmp_path, profile)

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
    )

    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert command.index("--read-only") < command.index(
        configuration.profile.image_name
    )


def test_readonly_fs_profile_uses_read_only_root_with_writable_tmp(
    tmp_path: Path,
) -> None:
    """Verify the readonly-fs profile applies its runtime hardening options."""
    configuration = _create_configuration(tmp_path, get_docker_profile("readonly-fs"))

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        remote_run_directory="/sandbox-work/run-test",
    )

    assert READONLY_FS_IMAGE_NAME in command
    assert "--read-only" in command
    assert "--tmpfs" in command
    assert "/tmp:rw,nosuid,nodev,noexec,size=2g" in command
    assert "/sandbox-work:rw,nosuid,nodev,noexec,size=256m" in command
    assert "target=/sandbox-denied,readonly" in " ".join(command)
    assert "HOME=/tmp/sandbox-home" in command
    assert "XDG_CACHE_HOME=/tmp/sandbox-cache" in command
    assert "XDG_CONFIG_HOME=/tmp/sandbox-config" in command
    assert "XDG_RUNTIME_DIR=/tmp/sandbox-runtime" in command
    assert "mkdir -p /sandbox-work/run-test/allowed/allowed" in command[-1]
    assert "mkdir -p /sandbox-denied/denied" not in command[-1]
    assert "python -m docker_sandbox.landlock_runner" in command[-1]
    assert "--policy /sandbox-output/landlock-policy.json" in command[-1]


def test_readonly_denied_fixture_is_removed_after_run(tmp_path: Path) -> None:
    """Verify the readonly denied mount source is temporary run scaffolding."""
    configuration = _create_configuration(tmp_path, get_docker_profile("readonly-fs"))
    run_directory = tmp_path / ".docker_sandbox" / "runs" / "run-test"

    _prepare_readonly_denied_directory(configuration, run_directory)

    denied_source_directory = run_directory / "readonly-denied"
    assert denied_source_directory.exists()

    _delete_readonly_denied_directory(configuration, run_directory)

    assert not denied_source_directory.exists()


def test_readonly_fs_profile_writes_landlock_policy(tmp_path: Path) -> None:
    """Verify the readonly-fs profile emits its Landlock path policy."""
    configuration = _create_configuration(tmp_path, get_docker_profile("readonly-fs"))
    run_directory = tmp_path / ".docker_sandbox" / "runs" / "run-test"
    run_directory.mkdir(parents=True)

    _write_landlock_policy(configuration, run_directory)

    policy_path = run_directory / "landlock-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))

    assert {"path": "/sandbox-work", "access": "rw"} in policy["rules"]
    assert {"path": "/sandbox-denied", "access": "r"} not in policy["rules"]
    assert {"path": "/", "access": "r"} not in policy["rules"]
    assert {"path": "/etc", "access": "r"} in policy["rules"]
    assert {"path": "/ms-playwright", "access": "rx"} in policy["rules"]
    assert {"path": "/usr", "access": "rx"} in policy["rules"]


def test_network_egress_profile_starts_from_readonly_fs_profile() -> None:
    """Verify network-egress begins as a readonly-fs clone."""
    readonly_profile = get_docker_profile("readonly-fs")
    network_profile = get_docker_profile("network-egress")

    assert network_profile.image_name == NETWORK_EGRESS_IMAGE_NAME
    assert network_profile.image_name != readonly_profile.image_name
    assert (
        network_profile.container_run_options == readonly_profile.container_run_options
    )
    assert network_profile.remote_run_root == readonly_profile.remote_run_root
    assert (
        network_profile.allowed_directory_template
        == readonly_profile.allowed_directory_template
    )
    assert (
        network_profile.denied_directory_template
        == readonly_profile.denied_directory_template
    )
    assert (
        network_profile.readonly_denied_mount_target
        == readonly_profile.readonly_denied_mount_target
    )
    assert network_profile.landlock_rules == readonly_profile.landlock_rules
    assert network_profile.network_gateway is not None


def test_ambient_services_profile_starts_from_network_egress_profile() -> None:
    """Verify ambient-services begins as a network-egress clone."""
    network_profile = get_docker_profile("network-egress")
    ambient_profile = get_docker_profile("ambient-services")

    assert ambient_profile.image_name == AMBIENT_SERVICES_IMAGE_NAME
    assert ambient_profile.image_name != network_profile.image_name
    assert network_profile.ipc_mode == "host"
    assert network_profile.shm_size is None
    assert network_profile.cgroupns_mode is None
    assert network_profile.pids_limit is None
    assert network_profile.memory is None
    assert network_profile.memory_swap is None
    assert network_profile.cpus is None
    assert network_profile.ulimits == ()
    assert network_profile.cap_drop == ()
    assert network_profile.security_options == ()
    assert network_profile.denied_executable_paths == ()
    assert ambient_profile.ipc_mode == "private"
    assert ambient_profile.shm_size == "1g"
    assert ambient_profile.cgroupns_mode == "private"
    assert ambient_profile.pids_limit == 512
    assert ambient_profile.cap_drop == ("ALL",)
    assert ambient_profile.security_options == ("no-new-privileges",)
    assert (
        ambient_profile.container_run_options == network_profile.container_run_options
    )
    assert ambient_profile.remote_run_root == network_profile.remote_run_root
    assert (
        ambient_profile.allowed_directory_template
        == network_profile.allowed_directory_template
    )
    assert (
        ambient_profile.denied_directory_template
        == network_profile.denied_directory_template
    )
    assert (
        ambient_profile.readonly_denied_mount_target
        == network_profile.readonly_denied_mount_target
    )
    assert ambient_profile.landlock_rules == network_profile.landlock_rules
    assert ambient_profile.network_gateway == network_profile.network_gateway
    assert ambient_profile.socket_mounts == ()
    assert ambient_profile.ssh_agent_socket is None
    assert ambient_profile.gpg_agent_socket is None
    assert ambient_profile.browser_debugging is None
    assert {policy.name for policy in ambient_profile.environment} == {
        "SSH_AUTH_SOCK",
        "GPG_AGENT_INFO",
        "DBUS_SESSION_BUS_ADDRESS",
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "GNUPGHOME",
    }
    assert set(ambient_profile.denied_executable_paths) == {
        "/usr/bin/busctl",
        "/usr/bin/dbus-send",
        "/usr/bin/gpg",
        "/usr/bin/gpg-connect-agent",
        "/usr/bin/gpgconf",
        "/usr/bin/journalctl",
        "/usr/bin/loginctl",
        "/usr/bin/scp",
        "/usr/bin/sftp",
        "/usr/bin/ssh",
        "/usr/bin/ssh-add",
        "/usr/bin/systemctl",
        "/usr/sbin/service",
    }


def test_ambient_services_profile_uses_private_ipc_and_bounded_shm(
    tmp_path: Path,
) -> None:
    """Verify ambient-services avoids host IPC while preserving Chromium shm."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("ambient-services")
    )

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        network_name="sandbox-tester-net-test",
        remote_run_directory="/sandbox-work/run-test",
        gateway_ip_address="172.20.0.2",
    )

    assert "--ipc=host" not in command
    assert "--ipc=private" in command
    assert "--shm-size" in command
    assert "1g" in command
    assert "--cgroupns=private" in command
    assert "--pids-limit" in command
    assert "512" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt" in command
    assert "no-new-privileges" in command
    assert command.index("--ipc=private") < command.index(
        configuration.profile.image_name
    )
    assert "/var/run/docker.sock" not in " ".join(command)
    assert "SSH_AUTH_SOCK" not in command
    assert "GNUPGHOME=/tmp/sandbox-gnupg-empty" in command
    assert "GPG_AGENT_INFO" not in command
    assert "DBUS_SESSION_BUS_ADDRESS" not in command
    assert "DISPLAY" not in command
    assert "WAYLAND_DISPLAY" not in command
    assert 'mkdir -p "$GNUPGHOME"' in command[-1]
    joined_command = " ".join(command)
    assert "target=/usr/bin/gpgconf,readonly" in joined_command
    assert "target=/usr/bin/gpg-connect-agent,readonly" in joined_command
    assert "target=/usr/bin/ssh,readonly" in joined_command
    assert "target=/usr/bin/dbus-send,readonly" in joined_command
    assert "target=/usr/sbin/service,readonly" in joined_command


def test_execution_control_profile_starts_from_ambient_services_profile() -> None:
    """Verify execution-control begins as an ambient-services clone."""
    ambient_profile = get_docker_profile("ambient-services")
    execution_profile = get_docker_profile("execution-control")

    assert execution_profile.image_name == EXECUTION_CONTROL_IMAGE_NAME
    assert execution_profile.image_name != ambient_profile.image_name
    assert execution_profile.ipc_mode == ambient_profile.ipc_mode
    assert execution_profile.shm_size == ambient_profile.shm_size
    assert execution_profile.cgroupns_mode == ambient_profile.cgroupns_mode
    assert execution_profile.pids_limit == ambient_profile.pids_limit
    assert execution_profile.memory == ambient_profile.memory
    assert execution_profile.memory_swap == ambient_profile.memory_swap
    assert execution_profile.cpus == ambient_profile.cpus
    assert execution_profile.ulimits == ambient_profile.ulimits
    assert execution_profile.cap_drop == ambient_profile.cap_drop
    assert execution_profile.cap_add == ambient_profile.cap_add
    assert execution_profile.security_options == ambient_profile.security_options
    assert execution_profile.container_run_options == (
        ambient_profile.container_run_options
    )
    assert execution_profile.remote_run_root == ambient_profile.remote_run_root
    assert (
        execution_profile.allowed_directory_template
        == ambient_profile.allowed_directory_template
    )
    assert (
        execution_profile.denied_directory_template
        == ambient_profile.denied_directory_template
    )
    assert (
        execution_profile.readonly_denied_mount_target
        == ambient_profile.readonly_denied_mount_target
    )
    assert execution_profile.landlock_rules == ambient_profile.landlock_rules
    assert execution_profile.network_gateway == ambient_profile.network_gateway
    assert execution_profile.socket_mounts == ambient_profile.socket_mounts
    assert execution_profile.ssh_agent_socket == ambient_profile.ssh_agent_socket
    assert execution_profile.gpg_agent_socket == ambient_profile.gpg_agent_socket
    assert execution_profile.browser_debugging == ambient_profile.browser_debugging
    assert execution_profile.environment == ambient_profile.environment
    assert execution_profile.denied_executables == ambient_profile.denied_executables
    assert set(execution_profile.denied_executable_paths).issuperset(
        ambient_profile.denied_executable_paths
    )
    assert "/usr/bin/apt" in execution_profile.denied_executable_paths
    assert "/usr/bin/apt-get" in execution_profile.denied_executable_paths
    assert "/opt/sandbox-tester/.venv/bin/pip" in (
        execution_profile.denied_executable_paths
    )
    assert "/usr/bin/git" in execution_profile.denied_executable_paths
    assert "/usr/bin/bash" in execution_profile.denied_executable_paths
    assert "/usr/bin/perl" in execution_profile.denied_executable_paths
    assert "/usr/bin/mount" in execution_profile.denied_executable_paths
    assert "/usr/bin/unshare" in execution_profile.denied_executable_paths
    assert "/usr/bin/systemd-run" in execution_profile.denied_executable_paths
    assert "/usr/bin/nohup" in execution_profile.denied_executable_paths
    assert "/usr/bin/setsid" in execution_profile.denied_executable_paths


def test_execution_control_profile_denies_common_execution_tools(
    tmp_path: Path,
) -> None:
    """Verify execution-control overlays common execution-control targets."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("execution-control")
    )

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        network_name="sandbox-tester-net-test",
        remote_run_directory="/sandbox-work/run-test",
        gateway_ip_address="172.20.0.2",
    )

    joined_command = " ".join(command)
    assert "target=/usr/bin/apt,readonly" in joined_command
    assert "target=/usr/bin/apt-get,readonly" in joined_command
    assert "target=/opt/sandbox-tester/.venv/bin/pip,readonly" in joined_command
    assert "target=/usr/bin/git,readonly" in joined_command
    assert "target=/usr/bin/bash,readonly" in joined_command
    assert "target=/usr/bin/perl,readonly" in joined_command
    assert "target=/usr/bin/unshare,readonly" in joined_command
    assert "target=/usr/bin/systemd-run,readonly" in joined_command
    assert "target=/usr/bin/nohup,readonly" in joined_command
    assert "target=/usr/bin/setsid,readonly" in joined_command
    assert "target=/opt/sandbox-tester/.venv/bin/python,readonly" not in joined_command
    assert "target=/usr/bin/sh,readonly" not in joined_command


def test_syscall_control_profile_starts_from_execution_control_profile() -> None:
    """Verify syscall-control begins as an execution-control clone."""
    execution_profile = get_docker_profile("execution-control")
    syscall_profile = get_docker_profile("syscall-control")

    assert syscall_profile.image_name == SYSCALL_CONTROL_IMAGE_NAME
    assert syscall_profile.image_name != execution_profile.image_name
    assert syscall_profile.ipc_mode == execution_profile.ipc_mode
    assert syscall_profile.shm_size == execution_profile.shm_size
    assert syscall_profile.cgroupns_mode == execution_profile.cgroupns_mode
    assert syscall_profile.pids_limit == execution_profile.pids_limit
    assert syscall_profile.memory == execution_profile.memory
    assert syscall_profile.memory_swap == execution_profile.memory_swap
    assert syscall_profile.cpus == execution_profile.cpus
    assert syscall_profile.ulimits == execution_profile.ulimits
    assert syscall_profile.cap_drop == execution_profile.cap_drop
    assert syscall_profile.cap_add == execution_profile.cap_add
    assert syscall_profile.security_options == execution_profile.security_options
    assert execution_profile.seccomp_profile is None
    assert syscall_profile.seccomp_profile == SeccompProfile()
    assert syscall_profile.container_run_options == (
        execution_profile.container_run_options
    )
    assert syscall_profile.remote_run_root == execution_profile.remote_run_root
    assert (
        syscall_profile.allowed_directory_template
        == execution_profile.allowed_directory_template
    )
    assert (
        syscall_profile.denied_directory_template
        == execution_profile.denied_directory_template
    )
    assert (
        syscall_profile.readonly_denied_mount_target
        == execution_profile.readonly_denied_mount_target
    )
    assert syscall_profile.landlock_rules == execution_profile.landlock_rules
    assert syscall_profile.network_gateway == execution_profile.network_gateway
    assert syscall_profile.socket_mounts == execution_profile.socket_mounts
    assert syscall_profile.ssh_agent_socket == execution_profile.ssh_agent_socket
    assert syscall_profile.gpg_agent_socket == execution_profile.gpg_agent_socket
    assert syscall_profile.browser_debugging == execution_profile.browser_debugging
    assert syscall_profile.environment == execution_profile.environment
    assert syscall_profile.denied_executables == execution_profile.denied_executables
    assert (
        syscall_profile.denied_executable_paths
        == execution_profile.denied_executable_paths
    )


def test_syscall_control_profile_uses_generated_seccomp_profile(
    tmp_path: Path,
) -> None:
    """Verify syscall-control adds its generated seccomp profile to Docker."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("syscall-control")
    )
    run_directory = tmp_path / ".docker_sandbox" / "runs" / "run-test"
    run_directory.mkdir(parents=True)

    _write_seccomp_profile(configuration, run_directory)

    seccomp_path = run_directory / "seccomp-profile.json"
    seccomp_data = json.loads(seccomp_path.read_text(encoding="utf-8"))
    denied_syscalls = seccomp_data["syscalls"][0]["names"]

    assert seccomp_data["defaultAction"] == "SCMP_ACT_ALLOW"
    assert seccomp_data["syscalls"][0]["action"] == "SCMP_ACT_ERRNO"
    assert "mount" in denied_syscalls
    assert "umount2" in denied_syscalls
    assert "unshare" in denied_syscalls
    assert "setns" in denied_syscalls
    assert "ptrace" in denied_syscalls
    assert "process_vm_readv" in denied_syscalls
    assert "keyctl" in denied_syscalls
    assert "add_key" in denied_syscalls
    assert "init_module" in denied_syscalls
    assert "bpf" in denied_syscalls
    assert "perf_event_open" in denied_syscalls

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=run_directory,
        container_name="sandbox-tester-run-test",
        network_name="sandbox-tester-net-test",
        remote_run_directory="/sandbox-work/run-test",
        gateway_ip_address="172.20.0.2",
    )

    assert "--security-opt" in command
    assert f"seccomp={seccomp_path}" in command


def test_resource_limits_profile_starts_from_syscall_control_profile() -> None:
    """Verify resource-limits begins as a syscall-control clone."""
    syscall_profile = get_docker_profile("syscall-control")
    resource_profile = get_docker_profile("resource-limits")

    assert resource_profile.image_name == RESOURCE_LIMITS_IMAGE_NAME
    assert resource_profile.image_name != syscall_profile.image_name
    assert resource_profile.ipc_mode == syscall_profile.ipc_mode
    assert resource_profile.shm_size == syscall_profile.shm_size
    assert resource_profile.cgroupns_mode == syscall_profile.cgroupns_mode
    assert resource_profile.pids_limit == syscall_profile.pids_limit
    assert syscall_profile.memory is None
    assert syscall_profile.memory_swap is None
    assert syscall_profile.cpus is None
    assert syscall_profile.ulimits == ()
    assert resource_profile.memory == "2g"
    assert resource_profile.memory_swap == "2g"
    assert resource_profile.cpus == "2"
    assert {ulimit.name for ulimit in resource_profile.ulimits} == {
        "nofile",
        "nproc",
    }
    assert resource_profile.cap_drop == syscall_profile.cap_drop
    assert resource_profile.cap_add == syscall_profile.cap_add
    assert resource_profile.security_options == syscall_profile.security_options
    assert resource_profile.seccomp_profile == syscall_profile.seccomp_profile
    assert resource_profile.container_run_options == (
        syscall_profile.container_run_options
    )
    assert resource_profile.remote_run_root == syscall_profile.remote_run_root
    assert (
        resource_profile.allowed_directory_template
        == syscall_profile.allowed_directory_template
    )
    assert (
        resource_profile.denied_directory_template
        == syscall_profile.denied_directory_template
    )
    assert (
        resource_profile.readonly_denied_mount_target
        == syscall_profile.readonly_denied_mount_target
    )
    assert resource_profile.landlock_rules == syscall_profile.landlock_rules
    assert resource_profile.network_gateway == syscall_profile.network_gateway
    assert resource_profile.socket_mounts == syscall_profile.socket_mounts
    assert resource_profile.ssh_agent_socket == syscall_profile.ssh_agent_socket
    assert resource_profile.gpg_agent_socket == syscall_profile.gpg_agent_socket
    assert resource_profile.browser_debugging == syscall_profile.browser_debugging
    assert resource_profile.environment == syscall_profile.environment
    assert resource_profile.denied_executables == syscall_profile.denied_executables
    assert (
        resource_profile.denied_executable_paths
        == syscall_profile.denied_executable_paths
    )


def test_resource_limits_profile_applies_docker_resource_limits(
    tmp_path: Path,
) -> None:
    """Verify resource-limits adds CPU, memory, and ulimit guards."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("resource-limits")
    )
    run_directory = tmp_path / ".docker_sandbox" / "runs" / "run-test"

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=run_directory,
        container_name="sandbox-tester-run-test",
        network_name="sandbox-tester-net-test",
        remote_run_directory="/sandbox-work/run-test",
        gateway_ip_address="172.20.0.2",
    )

    assert "--memory" in command
    assert "2g" in command
    assert "--memory-swap" in command
    assert "--cpus" in command
    assert "2" in command
    assert "--ulimit" in command
    assert "nofile=4096:4096" in command
    assert "nproc=512:512" in command


def test_browser_surface_profile_starts_from_resource_limits_profile() -> None:
    """Verify browser-surface begins as a resource-limits clone."""
    resource_profile = get_docker_profile("resource-limits")
    browser_profile = get_docker_profile("browser-surface")

    assert browser_profile.image_name == BROWSER_SURFACE_IMAGE_NAME
    assert browser_profile.image_name != resource_profile.image_name
    assert browser_profile.ipc_mode == resource_profile.ipc_mode
    assert browser_profile.shm_size == resource_profile.shm_size
    assert browser_profile.cgroupns_mode == resource_profile.cgroupns_mode
    assert browser_profile.pids_limit == resource_profile.pids_limit
    assert browser_profile.memory == resource_profile.memory
    assert browser_profile.memory_swap == resource_profile.memory_swap
    assert browser_profile.cpus == resource_profile.cpus
    assert browser_profile.ulimits == resource_profile.ulimits
    assert browser_profile.cap_drop == resource_profile.cap_drop
    assert browser_profile.cap_add == resource_profile.cap_add
    assert browser_profile.security_options == resource_profile.security_options
    assert browser_profile.seccomp_profile == resource_profile.seccomp_profile
    assert browser_profile.container_run_options == (
        resource_profile.container_run_options
    )
    assert browser_profile.remote_run_root == resource_profile.remote_run_root
    assert (
        browser_profile.allowed_directory_template
        == resource_profile.allowed_directory_template
    )
    assert (
        browser_profile.denied_directory_template
        == resource_profile.denied_directory_template
    )
    assert (
        browser_profile.readonly_denied_mount_target
        == resource_profile.readonly_denied_mount_target
    )
    assert browser_profile.landlock_rules == resource_profile.landlock_rules
    assert browser_profile.network_gateway == resource_profile.network_gateway
    assert browser_profile.network_dns_policy == resource_profile.network_dns_policy
    assert browser_profile.socket_mounts == resource_profile.socket_mounts
    assert browser_profile.ssh_agent_socket == resource_profile.ssh_agent_socket
    assert browser_profile.gpg_agent_socket == resource_profile.gpg_agent_socket
    assert browser_profile.browser_debugging == resource_profile.browser_debugging
    assert resource_profile.browser_surface is None
    assert browser_profile.browser_surface == BrowserSurfaceProfile()
    assert browser_profile.environment == resource_profile.environment
    assert browser_profile.denied_executables == resource_profile.denied_executables
    assert (
        browser_profile.denied_executable_paths
        == resource_profile.denied_executable_paths
    )


def test_browser_surface_profile_hardens_browser_context() -> None:
    """Verify browser-surface config denies media and adds Chromium flags."""
    profile = get_docker_profile("browser-surface")
    config_json = _build_config_json(
        "/sandbox-work/run-test",
        "/sandbox-work/run-test/allowed",
        "/sandbox-denied",
        "sandbox",
        browser_surface=profile.browser_surface,
    )

    assert '"allow_camera_capture": false' in config_json
    assert '"allow_microphone_capture": false' in config_json
    assert '"--disable-sync"' in config_json
    assert '"--password-store=basic"' in config_json
    assert '"--use-mock-keychain"' in config_json
    assert '"--disable-gpu"' in config_json


def test_dns_proxy_control_profile_starts_from_browser_surface_profile() -> None:
    """Verify dns-proxy-control begins as a browser-surface clone."""
    browser_profile = get_docker_profile("browser-surface")
    dns_profile = get_docker_profile("dns-proxy-control")

    assert dns_profile.image_name == DNS_PROXY_CONTROL_IMAGE_NAME
    assert dns_profile.image_name != browser_profile.image_name
    assert dns_profile.ipc_mode == browser_profile.ipc_mode
    assert dns_profile.shm_size == browser_profile.shm_size
    assert dns_profile.cgroupns_mode == browser_profile.cgroupns_mode
    assert dns_profile.pids_limit == browser_profile.pids_limit
    assert dns_profile.memory == browser_profile.memory
    assert dns_profile.memory_swap == browser_profile.memory_swap
    assert dns_profile.cpus == browser_profile.cpus
    assert dns_profile.ulimits == browser_profile.ulimits
    assert dns_profile.cap_drop == browser_profile.cap_drop
    assert dns_profile.cap_add == browser_profile.cap_add
    assert dns_profile.security_options == browser_profile.security_options
    assert dns_profile.seccomp_profile == browser_profile.seccomp_profile
    assert dns_profile.container_run_options == browser_profile.container_run_options
    assert dns_profile.remote_run_root == browser_profile.remote_run_root
    assert (
        dns_profile.allowed_directory_template
        == browser_profile.allowed_directory_template
    )
    assert (
        dns_profile.denied_directory_template
        == browser_profile.denied_directory_template
    )
    assert (
        dns_profile.readonly_denied_mount_target
        == browser_profile.readonly_denied_mount_target
    )
    assert dns_profile.landlock_rules == browser_profile.landlock_rules
    assert dns_profile.network_gateway == browser_profile.network_gateway
    assert browser_profile.network_dns_policy is None
    assert dns_profile.network_dns_policy == NetworkDnsPolicy()
    assert dns_profile.socket_mounts == browser_profile.socket_mounts
    assert dns_profile.ssh_agent_socket == browser_profile.ssh_agent_socket
    assert dns_profile.gpg_agent_socket == browser_profile.gpg_agent_socket
    assert dns_profile.browser_debugging == browser_profile.browser_debugging
    assert dns_profile.browser_surface == browser_profile.browser_surface
    assert dns_profile.environment == browser_profile.environment
    assert dns_profile.denied_executables == browser_profile.denied_executables
    assert (
        dns_profile.denied_executable_paths == browser_profile.denied_executable_paths
    )


def test_dns_proxy_control_profile_adds_dns_policy_options(
    tmp_path: Path,
) -> None:
    """Verify dns-proxy-control constrains DNS and Docker host aliases."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("dns-proxy-control")
    )

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        network_name="sandbox-tester-net-test",
        remote_run_directory="/sandbox-work/run-test",
        gateway_ip_address="172.20.0.2",
    )

    assert "--dns" in command
    assert "172.20.0.2" in command
    assert "--dns-option" in command
    assert "attempts:1" in command
    assert "timeout:1" in command
    assert "--add-host" in command
    assert "host.docker.internal:0.0.0.0" in command
    assert "gateway.docker.internal:0.0.0.0" in command
    assert "kubernetes.docker.internal:0.0.0.0" in command
    assert command.index("--network") < command.index("--dns")
    assert command.index("--dns") < command.index(configuration.profile.image_name)


def test_dns_proxy_control_profile_fails_closed_without_gateway_ip(
    tmp_path: Path,
) -> None:
    """Verify dns-proxy-control uses loopback DNS if gateway inspect fails."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("dns-proxy-control")
    )

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        network_name="sandbox-tester-net-test",
        remote_run_directory="/sandbox-work/run-test",
    )

    assert "--dns" in command
    assert "127.0.0.1" in command


def test_minimized_image_profile_starts_from_dns_proxy_control_profile() -> None:
    """Verify minimized-image begins as a dns-proxy-control clone."""
    dns_profile = get_docker_profile("dns-proxy-control")
    minimized_profile = get_docker_profile("minimized-image")

    assert minimized_profile.image_name == MINIMIZED_IMAGE_IMAGE_NAME
    assert minimized_profile.image_name != dns_profile.image_name
    assert minimized_profile.image_build_arguments == (
        "--build-arg",
        "SANDBOX_MINIMIZE_IMAGE=true",
    )
    assert minimized_profile.ipc_mode == dns_profile.ipc_mode
    assert minimized_profile.shm_size == dns_profile.shm_size
    assert minimized_profile.cgroupns_mode == dns_profile.cgroupns_mode
    assert minimized_profile.pids_limit == dns_profile.pids_limit
    assert minimized_profile.memory == dns_profile.memory
    assert minimized_profile.memory_swap == dns_profile.memory_swap
    assert minimized_profile.cpus == dns_profile.cpus
    assert minimized_profile.ulimits == dns_profile.ulimits
    assert minimized_profile.cap_drop == dns_profile.cap_drop
    assert minimized_profile.cap_add == dns_profile.cap_add
    assert minimized_profile.security_options == dns_profile.security_options
    assert minimized_profile.seccomp_profile == dns_profile.seccomp_profile
    assert minimized_profile.container_run_options == dns_profile.container_run_options
    assert minimized_profile.remote_run_root == dns_profile.remote_run_root
    assert (
        minimized_profile.allowed_directory_template
        == dns_profile.allowed_directory_template
    )
    assert (
        minimized_profile.denied_directory_template
        == dns_profile.denied_directory_template
    )
    assert (
        minimized_profile.readonly_denied_mount_target
        == dns_profile.readonly_denied_mount_target
    )
    assert minimized_profile.landlock_rules == dns_profile.landlock_rules
    assert minimized_profile.network_gateway == dns_profile.network_gateway
    assert minimized_profile.network_dns_policy == dns_profile.network_dns_policy
    assert minimized_profile.socket_mounts == dns_profile.socket_mounts
    assert minimized_profile.ssh_agent_socket == dns_profile.ssh_agent_socket
    assert minimized_profile.gpg_agent_socket == dns_profile.gpg_agent_socket
    assert minimized_profile.browser_debugging == dns_profile.browser_debugging
    assert minimized_profile.browser_surface == dns_profile.browser_surface
    assert minimized_profile.environment == dns_profile.environment
    assert minimized_profile.denied_executables == dns_profile.denied_executables
    assert (
        minimized_profile.denied_executable_paths == dns_profile.denied_executable_paths
    )


def test_minimized_image_profile_uses_minimization_build_argument(
    tmp_path: Path,
) -> None:
    """Verify minimized-image passes the Dockerfile minimization flag."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("minimized-image")
    )

    command = _build_image_command(configuration)

    assert command == [
        "docker",
        "build",
        "--file",
        str(tmp_path / "Dockerfile"),
        "--tag",
        MINIMIZED_IMAGE_IMAGE_NAME,
        "--build-arg",
        "SANDBOX_MINIMIZE_IMAGE=true",
        str(tmp_path),
    ]


def test_filesystem_visibility_profile_starts_from_minimized_image_profile() -> None:
    """Verify filesystem-visibility begins as a minimized-image clone."""
    minimized_profile = get_docker_profile("minimized-image")
    filesystem_profile = get_docker_profile("filesystem-visibility")

    assert filesystem_profile.image_name == FILESYSTEM_VISIBILITY_IMAGE_NAME
    assert filesystem_profile.image_name != minimized_profile.image_name
    assert filesystem_profile.image_build_arguments == (
        "--build-arg",
        "SANDBOX_MINIMIZE_IMAGE=true",
    )
    assert filesystem_profile.ipc_mode == minimized_profile.ipc_mode
    assert filesystem_profile.shm_size == minimized_profile.shm_size
    assert filesystem_profile.cgroupns_mode == minimized_profile.cgroupns_mode
    assert filesystem_profile.pids_limit == minimized_profile.pids_limit
    assert filesystem_profile.memory == minimized_profile.memory
    assert filesystem_profile.memory_swap == minimized_profile.memory_swap
    assert filesystem_profile.cpus == minimized_profile.cpus
    assert {ulimit.name for ulimit in filesystem_profile.ulimits} == {
        "nofile",
        "nproc",
        "fsize",
    }
    assert filesystem_profile.cap_drop == minimized_profile.cap_drop
    assert filesystem_profile.cap_add == minimized_profile.cap_add
    assert filesystem_profile.security_options == minimized_profile.security_options
    assert filesystem_profile.seccomp_profile == minimized_profile.seccomp_profile
    assert filesystem_profile.remote_run_root == minimized_profile.remote_run_root
    assert (
        filesystem_profile.allowed_directory_template
        == minimized_profile.allowed_directory_template
    )
    assert (
        filesystem_profile.denied_directory_template
        == minimized_profile.denied_directory_template
    )
    assert (
        filesystem_profile.readonly_denied_mount_target
        == minimized_profile.readonly_denied_mount_target
    )
    assert filesystem_profile.network_gateway == minimized_profile.network_gateway
    assert filesystem_profile.network_dns_policy == minimized_profile.network_dns_policy
    assert filesystem_profile.socket_mounts == minimized_profile.socket_mounts
    assert filesystem_profile.ssh_agent_socket == minimized_profile.ssh_agent_socket
    assert filesystem_profile.gpg_agent_socket == minimized_profile.gpg_agent_socket
    assert filesystem_profile.browser_debugging == minimized_profile.browser_debugging
    assert filesystem_profile.browser_surface == minimized_profile.browser_surface
    assert filesystem_profile.environment == minimized_profile.environment
    assert filesystem_profile.denied_executables == minimized_profile.denied_executables
    assert (
        filesystem_profile.denied_executable_paths
        == minimized_profile.denied_executable_paths
    )


def test_filesystem_visibility_profile_reduces_runtime_surface(
    tmp_path: Path,
) -> None:
    """Verify filesystem-visibility narrows runtime filesystem exposure."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("filesystem-visibility")
    )

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        network_name="sandbox-tester-net-test",
        remote_run_directory="/sandbox-work/run-test",
        gateway_ip_address="172.20.0.2",
    )
    profile = configuration.profile

    assert FILESYSTEM_VISIBILITY_IMAGE_NAME in command
    assert "--pid=private" not in command
    assert "--uts=private" not in command
    assert "/tmp:rw,nosuid,nodev,noexec,size=1g" in command
    assert "/proc/acpi:rw,nosuid,nodev,noexec,size=1k" in command
    assert "/sys/firmware:rw,nosuid,nodev,noexec,size=1k" in command
    assert "fsize=104857600:104857600" in command
    assert LandlockPathRule("/sys", "r") not in profile.landlock_rules
    assert LandlockPathRule("/dev", "rw") in profile.landlock_rules


def test_denied_executable_stubs_are_temporary_run_scaffolding(
    tmp_path: Path,
) -> None:
    """Verify denied executable stubs are generated and then removed."""
    profile = DockerProfile(
        name="deny-profile",
        description="Test denied executable profile.",
        image_name="sandbox-tester/docker-sandbox:deny-test",
        denied_executables=("gpgconf",),
        denied_executable_paths=(),
    )
    configuration = _create_configuration(tmp_path, profile)
    run_directory = tmp_path / ".docker_sandbox" / "runs" / "run-test"

    _prepare_denied_executable_stubs(configuration, run_directory)

    stub_path = run_directory / "denied-executables" / "usr__bin__gpgconf"
    assert "denied by sandbox profile" in stub_path.read_text(encoding="utf-8")

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=run_directory,
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
    )

    assert f"type=bind,source={stub_path},target=/usr/bin/gpgconf,readonly" in command

    _delete_denied_executable_directory(configuration, run_directory)

    assert not stub_path.parent.exists()


def test_profile_socket_mounts_are_explicit_opt_in(tmp_path: Path) -> None:
    """Verify host service sockets are mounted only when profiles allow them."""
    socket_path = tmp_path / "agent.sock"
    profile = DockerProfile(
        name="socket-profile",
        description="Test socket profile.",
        image_name="sandbox-tester/docker-sandbox:socket-test",
        socket_mounts=(
            SocketMount(
                source_path=socket_path,
                target_path="/sandbox-sockets/agent.sock",
                readonly=False,
            ),
        ),
    )
    configuration = _create_configuration(tmp_path, profile)

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
    )

    assert "--mount" in command
    assert (
        f"type=bind,source={socket_path},target=/sandbox-sockets/agent.sock" in command
    )
    assert (
        f"type=bind,source={socket_path},target=/sandbox-sockets/agent.sock,readonly"
        not in command
    )


def test_profile_ssh_agent_forward_is_explicit_opt_in(tmp_path: Path) -> None:
    """Verify SSH agent sockets are mounted and configured only by profile."""
    socket_path = tmp_path / "ssh-agent.sock"
    profile = DockerProfile(
        name="ssh-agent-profile",
        description="Test SSH agent profile.",
        image_name="sandbox-tester/docker-sandbox:ssh-agent-test",
        ssh_agent_socket=AgentSocketForward(
            source_path=socket_path,
            target_path="/tmp/ssh-agent.sock",
        ),
    )
    configuration = _create_configuration(tmp_path, profile)

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
    )
    config_json = _build_config_json(
        "/tmp/sandbox-tester/run-test",
        "/tmp/sandbox-tester/run-test/allowed",
        "/tmp/sandbox-tester/run-test/denied",
        "sandbox",
        ssh_agent_socket="/tmp/ssh-agent.sock",
    )

    assert f"type=bind,source={socket_path},target=/tmp/ssh-agent.sock" in command
    assert "SSH_AUTH_SOCK=/tmp/ssh-agent.sock" in command
    assert '"ssh_agent_socket": "/tmp/ssh-agent.sock"' in config_json


def test_profile_gpg_agent_forward_is_explicit_opt_in(tmp_path: Path) -> None:
    """Verify GPG agent sockets set GNUPGHOME only when profiles allow them."""
    socket_path = tmp_path / "S.gpg-agent"
    profile = DockerProfile(
        name="gpg-agent-profile",
        description="Test GPG agent profile.",
        image_name="sandbox-tester/docker-sandbox:gpg-agent-test",
        gpg_agent_socket=AgentSocketForward(
            source_path=socket_path,
            target_path="/tmp/S.gpg-agent",
        ),
    )
    configuration = _create_configuration(tmp_path, profile)

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
    )

    assert f"type=bind,source={socket_path},target=/tmp/S.gpg-agent" in command
    assert "GNUPGHOME=/tmp" in command


def test_browser_debugging_controls_are_disabled_by_default() -> None:
    """Verify ambient-services does not expose browser debugging by default."""
    config_json = _build_config_json(
        "/sandbox-work/run-test",
        "/sandbox-work/run-test/allowed",
        "/sandbox-denied",
        "sandbox",
    )

    assert '"browser_debugging_url": null' in config_json
    assert '"browser_executable": null' in config_json
    assert '"existing_browser_profile": null' in config_json


def test_browser_debugging_controls_are_explicit_opt_in() -> None:
    """Verify browser debugging context is populated only when configured."""
    browser_debugging = BrowserDebuggingProfile(
        debugging_url="http://127.0.0.1:9222/json/version",
        browser_executable="/usr/bin/chromium",
        existing_browser_profile="/sandbox-work/browser-profile",
    )

    config_json = _build_config_json(
        "/sandbox-work/run-test",
        "/sandbox-work/run-test/allowed",
        "/sandbox-denied",
        "sandbox",
        browser_debugging=browser_debugging,
    )

    assert (
        '"browser_debugging_url": "http://127.0.0.1:9222/json/version"' in config_json
    )
    assert '"browser_executable": "/usr/bin/chromium"' in config_json
    assert '"existing_browser_profile": "/sandbox-work/browser-profile"' in config_json


def test_network_egress_profile_uses_internal_network_and_proxy(
    tmp_path: Path,
) -> None:
    """Verify network-egress routes the sandbox through the gateway address."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("network-egress")
    )

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        network_name="sandbox-tester-net-test",
        remote_run_directory="/sandbox-work/run-test",
        gateway_ip_address="172.20.0.2",
    )

    assert "--network" in command
    assert "sandbox-tester-net-test" in command
    assert "HTTP_PROXY=http://172.20.0.2:3128" in command
    assert "HTTPS_PROXY=http://172.20.0.2:3128" in command
    assert "NO_PROXY=localhost,127.0.0.1" in command


def test_network_egress_profile_can_fall_back_to_gateway_alias(
    tmp_path: Path,
) -> None:
    """Verify network-egress still has a proxy host when inspection fails."""
    configuration = _create_configuration(
        tmp_path, get_docker_profile("network-egress")
    )

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        network_name="sandbox-tester-net-test",
        remote_run_directory="/sandbox-work/run-test",
    )

    assert "HTTP_PROXY=http://egress-gateway:3128" in command
    assert "HTTPS_PROXY=http://egress-gateway:3128" in command


def test_gateway_start_commands_create_internal_network_and_sidecar(
    tmp_path: Path,
) -> None:
    """Verify gateway startup uses a sidecar attached to a private network."""
    squid_config_path = tmp_path / "squid.conf"

    commands = _build_gateway_start_commands(
        "ubuntu/squid:latest",
        "sandbox-tester-gateway-test",
        "sandbox-tester-net-test",
        squid_config_path,
    )

    assert commands[0] == [
        "docker",
        "network",
        "create",
        "--internal",
        "sandbox-tester-net-test",
    ]
    assert commands[1][:8] == [
        "docker",
        "run",
        "--detach",
        "--name",
        "sandbox-tester-gateway-test",
        "--network",
        "bridge",
        "--mount",
    ]
    assert commands[2] == [
        "docker",
        "network",
        "connect",
        "--alias",
        "egress-gateway",
        "sandbox-tester-net-test",
        "sandbox-tester-gateway-test",
    ]
    assert commands[3][:4] == [
        "docker",
        "exec",
        "sandbox-tester-gateway-test",
        "/bin/sh",
    ]
    assert "squid -k check" in commands[3][-1]


def test_squid_configuration_allows_normalized_domains() -> None:
    """Verify gateway domains support suffix-style profile entries."""
    domains = _build_allowed_gateway_domains(
        ("*.openai.com", ".github.com"),
        {
            "allowed_domain": "example.com",
            "git_remote_url": "https://github.com/SomeNewKid/ScratchpadOne.git",
        },
    )
    config_text = _build_squid_configuration_text(domains, 3128)

    assert ".openai.com" in domains
    assert ".github.com" not in domains
    assert "example.com" in domains
    assert "github.com" in domains
    assert "acl allowed_sites dstdomain" in config_text
    assert "http_access deny all" in config_text
    assert "access_log none" in config_text
    assert "cache_log /tmp/squid-cache.log" in config_text


def test_squid_configuration_denies_ip_literal_destinations() -> None:
    """Verify gateway policy blocks raw IPv4 and IPv6 URL targets by default."""
    config_text = _build_squid_configuration_text(("example.com",), 3128)

    assert "acl ipv4_literal_url url_regex" in config_text
    assert "acl ipv4_literal_connect url_regex" in config_text
    assert "acl ipv6_literal_url url_regex" in config_text
    assert "acl ipv6_literal_connect url_regex" in config_text
    assert "http_access deny ipv4_literal_url" in config_text
    assert "http_access deny ipv4_literal_connect" in config_text
    assert "http_access deny ipv6_literal_url" in config_text
    assert "http_access deny ipv6_literal_connect" in config_text
    assert "http_access allow allowed_sites" in config_text
    assert config_text.index("http_access deny ipv4_literal_url") < config_text.index(
        "http_access allow allowed_sites"
    )


def test_squid_configuration_allows_configured_ip_addresses() -> None:
    """Verify configured IP addresses are allowed before IP literal denial."""
    ip_addresses = _build_allowed_gateway_ip_addresses(
        ("1.1.1.1", "[2606:4700:4700::1111]")
    )
    config_text = _build_squid_configuration_text(("example.com",), 3128, ip_addresses)

    assert "1.1.1.1/32" in ip_addresses
    assert "2606:4700:4700::1111/128" in ip_addresses
    assert "acl allowed_ip_addresses dst" in config_text
    assert "http_access allow allowed_ip_addresses" in config_text
    assert config_text.index(
        "http_access allow allowed_ip_addresses"
    ) < config_text.index("http_access deny ipv4_literal_url")


def test_docker_run_command_forwards_environment_variable_by_name(
    tmp_path: Path,
) -> None:
    """Verify local secrets are not embedded directly in Docker metadata."""
    configuration = _create_configuration(tmp_path)

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
        environment_variables={"OPENAI_API_KEY": "secret-value"},
        local_environment_variable_names={"OPENAI_API_KEY"},
    )

    assert "--env" in command
    assert "OPENAI_API_KEY" in command
    assert "PYTHONPATH=/sandbox-source/src" in command
    assert "secret-value" not in command


def test_docker_run_command_forwards_literal_environment_value(
    tmp_path: Path,
) -> None:
    """Verify non-local environment values are passed into the container."""
    configuration = _create_configuration(tmp_path)

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
        environment_variables={"EXAMPLE_VALUE": "literal"},
    )

    assert "--env" in command
    assert "EXAMPLE_VALUE=literal" in command
    assert "PYTHONPATH=/sandbox-source/src" in command


def test_local_environment_value_resolves_from_host_environment() -> None:
    """Verify [local] values are copied from the host environment when present."""
    variables = _resolve_environment_variables(
        {
            "OPENAI_API_KEY": "[local]",
            "EXAMPLE_VALUE": "literal",
            "MISSING_VALUE": "[local]",
        },
        {
            "OPENAI_API_KEY": "host-secret",
        },
    )

    assert variables == {
        "OPENAI_API_KEY": "host-secret",
        "EXAMPLE_VALUE": "literal",
    }


def test_docker_config_uses_linux_container_paths() -> None:
    """Verify generated config paths target the Linux container filesystem."""
    config_json = _build_config_json(
        "/tmp/sandbox-tester/run-test",
        "/tmp/sandbox-tester/run-test/allowed",
        "/tmp/sandbox-tester/run-test/denied",
        "sandbox",
    )

    assert '"working_directory": "/tmp/sandbox-tester/run-test"' in config_json
    assert '"output_directory": "/sandbox-output"' in config_json
    assert '"operating_system": "Linux"' in config_json
    assert '"runtime_user_directory": "/home/sandbox"' in config_json


def test_container_script_creates_fixtures_and_runs_sandbox_tester() -> None:
    """Verify the container bootstrap script prepares fixtures before testing."""
    script = _build_container_script("/tmp/sandbox-tester/run-test")

    assert "mkdir -p /tmp/sandbox-tester/run-test/allowed/allowed" in script
    assert "mkdir -p /tmp/sandbox-tester/run-test/denied/denied" in script
    assert 'mkdir -p "$XDG_RUNTIME_DIR"' in script
    assert "allowed.txt" in script
    assert "denied.txt" in script
    assert "python -m sandbox_tester --config /sandbox-output/config.json" in script
