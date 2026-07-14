"""Run Sandbox Tester inside disposable Docker containers."""

from __future__ import annotations

import datetime as dt
import json
import os
import shlex
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

from .models import DockerConfiguration, DockerRunResult

_DOCKER_EXECUTABLE = "docker"
_REMOTE_OUTPUT_DIRECTORY = "/sandbox-output"
_REMOTE_SOURCE_DIRECTORY = "/sandbox-source/src"
_CONTAINER_NAME_PREFIX = "sandbox-tester-run"
_READONLY_DENIED_SOURCE_DIRECTORY = "readonly-denied"
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
    remote_run_directory = _build_remote_run_directory(configuration, run_id)
    allowed_directory = _build_allowed_directory(configuration, remote_run_directory)
    denied_directory = _build_denied_directory(configuration, remote_run_directory)
    _prepare_readonly_denied_directory(configuration, run_directory)
    config_json = _build_config_json(
        remote_run_directory,
        allowed_directory,
        denied_directory,
        configuration.guest_user,
    )
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
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
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
    _delete_readonly_denied_directory(configuration, run_directory)
    remove_command = _build_docker_remove_command(container_name)

    return DockerRunResult(
        image_name=configuration.profile.image_name,
        profile_name=configuration.profile.name,
        container_name=container_name,
        run_directory=run_directory,
        command=command,
        remove_command=remove_command,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _build_remote_run_directory(
    configuration: DockerConfiguration,
    run_id: str,
) -> str:
    remote_root = configuration.profile.remote_run_root.rstrip("/")
    return f"{remote_root}/{run_id}"


def _build_allowed_directory(
    configuration: DockerConfiguration,
    remote_run_directory: str,
) -> str:
    return _format_directory_template(
        configuration.profile.allowed_directory_template,
        remote_run_directory,
    )


def _build_denied_directory(
    configuration: DockerConfiguration,
    remote_run_directory: str,
) -> str:
    return _format_directory_template(
        configuration.profile.denied_directory_template,
        remote_run_directory,
    )


def _format_directory_template(template: str, remote_run_directory: str) -> str:
    return template.format(remote_run_directory=remote_run_directory)


def _prepare_readonly_denied_directory(
    configuration: DockerConfiguration,
    run_directory: Path,
) -> None:
    if configuration.profile.readonly_denied_mount_target is None:
        return

    denied_child_directory = (
        run_directory / _READONLY_DENIED_SOURCE_DIRECTORY / "denied"
    )
    denied_child_directory.mkdir(parents=True, exist_ok=True)
    denied_file = denied_child_directory / "denied.txt"
    denied_file.write_text(_DENIED_FILE_CONTENT, encoding="utf-8")
    hidden_file = denied_child_directory / ".hidden"
    hidden_file.write_text(_HIDDEN_DENIED_FILE_CONTENT, encoding="utf-8")


def _delete_readonly_denied_directory(
    configuration: DockerConfiguration,
    run_directory: Path,
) -> None:
    if configuration.profile.readonly_denied_mount_target is None:
        return

    denied_source_directory = run_directory / _READONLY_DENIED_SOURCE_DIRECTORY
    resolved_run_directory = run_directory.resolve()
    resolved_denied_source_directory = denied_source_directory.resolve()

    if resolved_run_directory not in resolved_denied_source_directory.parents:
        raise RuntimeError(
            "Refusing to remove readonly denied fixture outside the run "
            f"directory: {resolved_denied_source_directory}"
        )

    shutil.rmtree(denied_source_directory, ignore_errors=True)


def _build_config_json(
    remote_run_directory: str,
    allowed_directory: str,
    denied_directory: str,
    guest_user: str,
) -> str:
    config = {
        "working_directory": remote_run_directory,
        "allowed_directory": allowed_directory,
        "denied_directory": denied_directory,
        "runtime_user_directory": f"/home/{guest_user}",
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
    allowed_directory: str | None = None,
    denied_directory: str | None = None,
    environment_variables: dict[str, str] | None = None,
    local_environment_variable_names: set[str] | None = None,
    verbose: bool = False,
    serialize_evidence: bool = False,
) -> list[str]:
    mount = f"type=bind,source={run_directory},target={_REMOTE_OUTPUT_DIRECTORY}"
    source_mount = _build_source_mount(configuration)
    command = [
        _DOCKER_EXECUTABLE,
        "run",
        "--name",
        container_name,
        "--init",
        "--ipc=host",
        "--mount",
        mount,
        "--mount",
        source_mount,
        "--user",
        configuration.guest_user,
    ]
    command.extend(configuration.profile.container_run_options)
    command.extend(_build_readonly_denied_mount_options(configuration, run_directory))
    command.extend(
        _build_environment_options(
            _build_container_environment(environment_variables or {}),
            local_environment_variable_names or set(),
        )
    )
    command.extend(
        [
            configuration.profile.image_name,
            "/bin/sh",
            "-c",
            _build_container_script(
                remote_run_directory=remote_run_directory,
                allowed_directory=(
                    allowed_directory
                    if allowed_directory is not None
                    else _build_allowed_directory(configuration, remote_run_directory)
                ),
                denied_directory=(
                    denied_directory
                    if denied_directory is not None
                    else _build_denied_directory(configuration, remote_run_directory)
                ),
                create_denied_fixture=(
                    configuration.profile.readonly_denied_mount_target is None
                ),
                verbose=verbose,
                serialize_evidence=serialize_evidence,
            ),
        ]
    )
    return command


def _build_source_mount(configuration: DockerConfiguration) -> str:
    source_directory = configuration.build_context / "src"
    return (
        f"type=bind,source={source_directory},"
        f"target={_REMOTE_SOURCE_DIRECTORY},readonly"
    )


def _build_container_environment(
    environment_variables: Mapping[str, str],
) -> dict[str, str]:
    container_environment = dict(environment_variables)
    container_environment["PYTHONPATH"] = _REMOTE_SOURCE_DIRECTORY
    return container_environment


def _build_readonly_denied_mount_options(
    configuration: DockerConfiguration,
    run_directory: Path,
) -> list[str]:
    target = configuration.profile.readonly_denied_mount_target
    if target is None:
        return []

    source = run_directory / _READONLY_DENIED_SOURCE_DIRECTORY
    mount = f"type=bind,source={source},target={target},readonly"
    return [
        "--mount",
        mount,
    ]


def _build_container_script(
    remote_run_directory: str,
    allowed_directory: str | None = None,
    denied_directory: str | None = None,
    create_denied_fixture: bool = True,
    verbose: bool = False,
    serialize_evidence: bool = False,
) -> str:
    if allowed_directory is None:
        allowed_directory = f"{remote_run_directory}/allowed"
    if denied_directory is None:
        denied_directory = f"{remote_run_directory}/denied"

    allowed_child_directory = f"{allowed_directory}/allowed"
    denied_child_directory = f"{denied_directory}/denied"
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
        'if [ -n "${HOME:-}" ]; then mkdir -p "$HOME"; fi',
        'if [ -n "${XDG_CACHE_HOME:-}" ]; then mkdir -p "$XDG_CACHE_HOME"; fi',
        'if [ -n "${XDG_CONFIG_HOME:-}" ]; then mkdir -p "$XDG_CONFIG_HOME"; fi',
        (
            'if [ -n "${XDG_RUNTIME_DIR:-}" ]; then '
            'mkdir -p "$XDG_RUNTIME_DIR"; '
            'chmod 700 "$XDG_RUNTIME_DIR"; '
            "fi"
        ),
        f"mkdir -p {shlex.quote(allowed_child_directory)}",
        _build_write_text_command(
            f"{allowed_child_directory}/allowed.txt",
            _ALLOWED_FILE_CONTENT,
        ),
        _build_write_text_command(
            f"{allowed_child_directory}/.hidden",
            _HIDDEN_ALLOWED_FILE_CONTENT,
        ),
        " ".join(shlex.quote(argument) for argument in arguments),
    ]
    if create_denied_fixture:
        lines.insert(-1, f"mkdir -p {shlex.quote(denied_child_directory)}")
        lines.insert(
            -1,
            _build_write_text_command(
                f"{denied_child_directory}/denied.txt",
                _DENIED_FILE_CONTENT,
            ),
        )
        lines.insert(
            -1,
            _build_write_text_command(
                f"{denied_child_directory}/.hidden",
                _HIDDEN_DENIED_FILE_CONTENT,
            ),
        )
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
