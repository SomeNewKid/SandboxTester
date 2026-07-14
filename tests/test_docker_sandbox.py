"""Tests for the Docker sandbox harness."""

from pathlib import Path

import pytest

from docker_sandbox.cli import main
from docker_sandbox.container_factory import _build_image_command
from docker_sandbox.models import DockerConfiguration, DockerProfile
from docker_sandbox.profiles import (
    BASELINE_IMAGE_NAME,
    READONLY_FS_IMAGE_NAME,
    get_docker_profile,
)
from docker_sandbox.sandbox_container import (
    _build_config_json,
    _build_container_script,
    _build_docker_run_command,
    _delete_readonly_denied_directory,
    _prepare_readonly_denied_directory,
    _resolve_environment_variables,
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


def test_readonly_denied_fixture_is_removed_after_run(tmp_path: Path) -> None:
    """Verify the readonly denied mount source is temporary run scaffolding."""
    configuration = _create_configuration(tmp_path, get_docker_profile("readonly-fs"))
    run_directory = tmp_path / ".docker_sandbox" / "runs" / "run-test"

    _prepare_readonly_denied_directory(configuration, run_directory)

    denied_source_directory = run_directory / "readonly-denied"
    assert denied_source_directory.exists()

    _delete_readonly_denied_directory(configuration, run_directory)

    assert not denied_source_directory.exists()


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
