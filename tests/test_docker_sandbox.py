"""Tests for the Docker sandbox harness."""

import json
from pathlib import Path

import pytest

from docker_sandbox.cli import main
from docker_sandbox.container_factory import _build_image_command
from docker_sandbox.models import (
    AgentSocketForward,
    BrowserDebuggingProfile,
    DockerConfiguration,
    DockerProfile,
    SocketMount,
)
from docker_sandbox.profiles import (
    AMBIENT_SERVICES_IMAGE_NAME,
    BASELINE_IMAGE_NAME,
    EXECUTION_CONTROL_IMAGE_NAME,
    NETWORK_EGRESS_IMAGE_NAME,
    READONLY_FS_IMAGE_NAME,
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
