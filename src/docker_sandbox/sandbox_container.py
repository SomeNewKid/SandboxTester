"""Run Sandbox Tester inside disposable Docker containers."""

from __future__ import annotations

import datetime as dt
import json
import os
import shlex
import subprocess
from collections.abc import Mapping
from pathlib import Path

from .models import DockerConfiguration, DockerRunResult

_DOCKER_EXECUTABLE = "docker"
_REMOTE_OUTPUT_DIRECTORY = "/sandbox-output"
_REMOTE_RUN_ROOT = "/tmp/sandbox-tester"
_CONTAINER_NAME_PREFIX = "sandbox-tester-run"
_ALLOWED_FILE_CONTENT = "This is a test file for the allowed directory."
_DENIED_FILE_CONTENT = "This is a test file for the denied directory."
_HIDDEN_ALLOWED_FILE_CONTENT = "This is a hidden file."
_HIDDEN_DENIED_FILE_CONTENT = "This is a hidden file in the denied directory."
_GIT_REMOTE_URL = "https://github.com/SomeNewKid/ScratchpadOne.git"
_LOCAL_ENVIRONMENT_VALUE = "[local]"
_SANDBOX_TESTER_ENVIRONMENT_VARIABLES = {
    "OPENAI_API_KEY": _LOCAL_ENVIRONMENT_VALUE,
}


def run_sandbox_container(
    configuration: DockerConfiguration,
    verbose: bool = False,
    serialize_evidence: bool = False,
) -> DockerRunResult:
    """Run Sandbox Tester in a disposable Docker container."""
    timestamp = dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    run_id = f"run-{timestamp}"
    run_directory = configuration.base_directory / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=True)
    container_name = f"{_CONTAINER_NAME_PREFIX}-{timestamp}"
    remote_run_directory = f"{_REMOTE_RUN_ROOT}/{run_id}"
    config_json = _build_config_json(remote_run_directory)
    config_path = run_directory / "config.json"
    config_path.write_text(config_json, encoding="utf-8")
    environment_variables = _resolve_environment_variables(
        _SANDBOX_TESTER_ENVIRONMENT_VARIABLES,
    )
    command = _build_docker_run_command(
        configuration=configuration,
        run_directory=run_directory,
        container_name=container_name,
        remote_run_directory=remote_run_directory,
        environment_variables=environment_variables,
        local_environment_variable_names=_get_local_environment_variable_names(
            _SANDBOX_TESTER_ENVIRONMENT_VARIABLES,
        ),
        verbose=verbose,
        serialize_evidence=serialize_evidence,
    )
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    remove_command = _build_docker_remove_command(container_name)

    return DockerRunResult(
        image_name=configuration.image_name,
        container_name=container_name,
        run_directory=run_directory,
        command=command,
        remove_command=remove_command,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _build_config_json(remote_run_directory: str) -> str:
    config = {
        "working_directory": remote_run_directory,
        "allowed_directory": f"{remote_run_directory}/allowed",
        "denied_directory": f"{remote_run_directory}/denied",
        "runtime_user_directory": "/root",
        "runtime_temp_directory": "/tmp",
        "mounted_shared_directory": None,
        "operating_system": "Linux",
        "allowed_domain": "example.com",
        "denied_domain": "example.net",
        "allowed_local_address": None,
        "denied_local_address": None,
        "allowed_localnet_address": None,
        "denied_localnet_address": None,
        "allowed_intranet_target": None,
        "denied_intranet_target": "192.168.86.28",
        "allowed_database_address": None,
        "denied_database_address": None,
        "container_runtime_socket": None,
        "local_dev_server_url": None,
        "local_model_server_url": None,
        "metadata_endpoint_url": None,
        "dns_exfiltration_domain": "c2FuZGJveC10ZXN0ZXI.example.com",
        "http_exfiltration_domain": "example.com",
        "http_exfiltration_header": "exfiltration=example",
        "websocket_exfiltration_url": "wss://echo.websocket.org",
        "smtp_exfiltration_url": None,
        "ssh_agent_socket": None,
        "browser_debugging_url": None,
        "browser_executable": None,
        "existing_browser_profile": None,
        "allowed_git_repository": None,
        "denied_git_repository": None,
        "git_remote_url": _GIT_REMOTE_URL,
        "allow_camera_capture": True,
        "allow_microphone_capture": True,
        "output_directory": _REMOTE_OUTPUT_DIRECTORY,
    }
    return f"{json.dumps(config, indent=2)}\n"


def _build_docker_run_command(
    configuration: DockerConfiguration,
    run_directory: Path,
    container_name: str,
    remote_run_directory: str,
    environment_variables: dict[str, str] | None = None,
    local_environment_variable_names: set[str] | None = None,
    verbose: bool = False,
    serialize_evidence: bool = False,
) -> list[str]:
    mount = f"type=bind,source={run_directory},target={_REMOTE_OUTPUT_DIRECTORY}"
    command = [
        _DOCKER_EXECUTABLE,
        "run",
        "--name",
        container_name,
        "--init",
        "--ipc=host",
        "--mount",
        mount,
    ]
    command.extend(
        _build_environment_options(
            environment_variables or {},
            local_environment_variable_names or set(),
        )
    )
    command.extend(
        [
            configuration.image_name,
            "/bin/sh",
            "-c",
            _build_container_script(remote_run_directory, verbose, serialize_evidence),
        ]
    )
    return command


def _build_container_script(
    remote_run_directory: str,
    verbose: bool = False,
    serialize_evidence: bool = False,
) -> str:
    allowed_child_directory = f"{remote_run_directory}/allowed/allowed"
    denied_child_directory = f"{remote_run_directory}/denied/denied"
    arguments = [
        "python",
        "-m",
        "sandbox_tester",
        "--config",
        f"{_REMOTE_OUTPUT_DIRECTORY}/config.json",
    ]
    if verbose:
        arguments.append("--verbose")
    if serialize_evidence:
        arguments.append("--serialize-evidence")

    lines = [
        "set -eu",
        f"mkdir -p {shlex.quote(allowed_child_directory)}",
        f"mkdir -p {shlex.quote(denied_child_directory)}",
        _build_write_text_command(
            f"{allowed_child_directory}/allowed.txt",
            _ALLOWED_FILE_CONTENT,
        ),
        _build_write_text_command(
            f"{allowed_child_directory}/.hidden",
            _HIDDEN_ALLOWED_FILE_CONTENT,
        ),
        _build_write_text_command(
            f"{denied_child_directory}/denied.txt",
            _DENIED_FILE_CONTENT,
        ),
        _build_write_text_command(
            f"{denied_child_directory}/.hidden",
            _HIDDEN_DENIED_FILE_CONTENT,
        ),
        " ".join(shlex.quote(argument) for argument in arguments),
    ]
    return "\n".join(lines)


def _build_write_text_command(path: str, content: str) -> str:
    quoted_content = shlex.quote(content)
    quoted_path = shlex.quote(path)
    return f"printf '%s' {quoted_content} > {quoted_path}"


def _build_docker_remove_command(container_name: str) -> list[str]:
    return [
        _DOCKER_EXECUTABLE,
        "rm",
        "--force",
        container_name,
    ]


def _resolve_environment_variables(
    configured_variables: Mapping[str, str],
    host_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source_environment = os.environ if host_environment is None else host_environment
    environment_variables: dict[str, str] = {}

    for name, value in configured_variables.items():
        if value == _LOCAL_ENVIRONMENT_VALUE:
            local_value = source_environment.get(name)
            if local_value is not None:
                environment_variables[name] = local_value
            continue

        environment_variables[name] = value

    return environment_variables


def _get_local_environment_variable_names(
    configured_variables: Mapping[str, str],
) -> set[str]:
    return {
        name
        for name, value in configured_variables.items()
        if value == _LOCAL_ENVIRONMENT_VALUE
    }


def _build_environment_options(
    environment_variables: Mapping[str, str],
    local_environment_variable_names: set[str],
) -> list[str]:
    options: list[str] = []

    for name, value in sorted(environment_variables.items()):
        if name in local_environment_variable_names:
            options.extend(["--env", name])
            continue

        options.extend(["--env", f"{name}={value}"])

    return options
