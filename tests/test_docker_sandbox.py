"""Tests for the Docker sandbox harness."""

from pathlib import Path

from docker_sandbox.cli import main
from docker_sandbox.container_factory import _build_image_command
from docker_sandbox.models import DockerConfiguration
from docker_sandbox.sandbox_container import (
    _build_config_json,
    _build_container_script,
    _build_docker_run_command,
    _resolve_environment_variables,
)


def test_docker_build_command_uses_configured_image_and_dockerfile(
    tmp_path: Path,
) -> None:
    """Verify the Docker build command uses the configured inputs."""
    configuration = DockerConfiguration(
        base_directory=tmp_path / ".docker_sandbox",
        image_name="sandbox-tester/docker-sandbox:test",
        dockerfile_path=tmp_path / "Dockerfile",
        build_context=tmp_path,
    )

    command = _build_image_command(configuration)

    assert command == [
        "docker",
        "build",
        "--file",
        str(tmp_path / "Dockerfile"),
        "--tag",
        "sandbox-tester/docker-sandbox:test",
        str(tmp_path),
    ]


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


def test_docker_run_command_uses_disposable_container_and_output_mount(
    tmp_path: Path,
) -> None:
    """Verify the Docker run command uses a named disposable container."""
    configuration = DockerConfiguration(
        base_directory=tmp_path / ".docker_sandbox",
        image_name="sandbox-tester/docker-sandbox:test",
        dockerfile_path=tmp_path / "Dockerfile",
        build_context=tmp_path,
    )
    run_directory = tmp_path / ".docker_sandbox" / "runs" / "run-test"

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=run_directory,
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
        verbose=True,
        serialize_evidence=True,
    )

    assert command[:8] == [
        "docker",
        "run",
        "--name",
        "sandbox-tester-run-test",
        "--init",
        "--ipc=host",
        "--mount",
        f"type=bind,source={run_directory},target=/sandbox-output",
    ]
    assert "sandbox-tester/docker-sandbox:test" in command
    assert "--verbose" in command[-1]
    assert "--serialize-evidence" in command[-1]


def test_docker_run_command_forwards_environment_variable_by_name(
    tmp_path: Path,
) -> None:
    """Verify local secrets are not embedded directly in Docker metadata."""
    configuration = DockerConfiguration(
        base_directory=tmp_path / ".docker_sandbox",
        image_name="sandbox-tester/docker-sandbox:test",
        dockerfile_path=tmp_path / "Dockerfile",
        build_context=tmp_path,
    )

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
    assert "secret-value" not in command


def test_docker_run_command_forwards_literal_environment_value(
    tmp_path: Path,
) -> None:
    """Verify non-local environment values are passed into the container."""
    configuration = DockerConfiguration(
        base_directory=tmp_path / ".docker_sandbox",
        image_name="sandbox-tester/docker-sandbox:test",
        dockerfile_path=tmp_path / "Dockerfile",
        build_context=tmp_path,
    )

    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=tmp_path / ".docker_sandbox" / "runs" / "run-test",
        container_name="sandbox-tester-run-test",
        remote_run_directory="/tmp/sandbox-tester/run-test",
        environment_variables={"EXAMPLE_VALUE": "literal"},
    )

    assert "--env" in command
    assert "EXAMPLE_VALUE=literal" in command


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
    config_json = _build_config_json("/tmp/sandbox-tester/run-test")

    assert '"working_directory": "/tmp/sandbox-tester/run-test"' in config_json
    assert '"output_directory": "/sandbox-output"' in config_json
    assert '"operating_system": "Linux"' in config_json


def test_container_script_creates_fixtures_and_runs_sandbox_tester() -> None:
    """Verify the container bootstrap script prepares fixtures before testing."""
    script = _build_container_script("/tmp/sandbox-tester/run-test")

    assert "mkdir -p /tmp/sandbox-tester/run-test/allowed/allowed" in script
    assert "mkdir -p /tmp/sandbox-tester/run-test/denied/denied" in script
    assert "allowed.txt" in script
    assert "denied.txt" in script
    assert "python -m sandbox_tester --config /sandbox-output/config.json" in script
