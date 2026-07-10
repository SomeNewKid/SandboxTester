"""Create disposable guest filesystem layouts for sandbox runs."""

from __future__ import annotations

import json
import posixpath
import uuid

import paramiko

from .models import GuestRunLayout

_REMOTE_RUN_ROOT = "/tmp/sandbox-tester"
_ALLOWED_FILE_NAME = "allowed.txt"
_DENIED_FILE_NAME = "denied.txt"
_ALLOWED_FILE_CONTENT = "This is a test file for the allowed directory."
_DENIED_FILE_CONTENT = "This is a test file for the denied directory."
_RUNTIME_TEMP_DIRECTORY = "/tmp"
_OPERATING_SYSTEM = "Linux"


def create_sandbox_tester_run_layout(
    client: paramiko.SSHClient,
    username: str,
) -> GuestRunLayout:
    """Create a disposable guest filesystem layout for Sandbox Tester."""
    run_directory = posixpath.join(_REMOTE_RUN_ROOT, f"run-{uuid.uuid4().hex}")
    allowed_directory = posixpath.join(run_directory, "allowed")
    denied_directory = posixpath.join(run_directory, "denied")
    output_directory = posixpath.join(run_directory, "output")
    config_path = posixpath.join(run_directory, "config.json")

    layout = GuestRunLayout(
        run_directory=run_directory,
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        output_directory=output_directory,
        config_path=config_path,
    )

    with client.open_sftp() as sftp:
        _mkdir_remote_directory(sftp, allowed_directory)
        _mkdir_remote_directory(sftp, denied_directory)
        _mkdir_remote_directory(sftp, output_directory)
        _write_remote_text(
            sftp,
            posixpath.join(allowed_directory, _ALLOWED_FILE_NAME),
            _ALLOWED_FILE_CONTENT,
        )
        _write_remote_text(
            sftp,
            posixpath.join(denied_directory, _DENIED_FILE_NAME),
            _DENIED_FILE_CONTENT,
        )
        _write_remote_text(sftp, config_path, _build_config_json(layout, username))

    return layout


def _build_config_json(layout: GuestRunLayout, username: str) -> str:
    config = {
        "working_directory": layout.run_directory,
        "allowed_directory": layout.allowed_directory,
        "denied_directory": layout.denied_directory,
        "runtime_user_directory": _build_runtime_user_directory(username),
        "runtime_temp_directory": _RUNTIME_TEMP_DIRECTORY,
        "mounted_shared_directory": None,
        "operating_system": _OPERATING_SYSTEM,
        "allowed_domain": None,
        "denied_domain": None,
        "allowed_local_address": None,
        "denied_local_address": None,
        "allowed_localnet_address": None,
        "denied_localnet_address": None,
        "allowed_intranet_target": None,
        "denied_intranet_target": None,
        "allowed_database_address": None,
        "denied_database_address": None,
        "container_runtime_socket": None,
        "local_dev_server_url": None,
        "local_model_server_url": None,
        "metadata_endpoint_url": None,
        "dns_exfiltration_domain": None,
        "http_exfiltration_domain": None,
        "http_exfiltration_header": None,
        "websocket_exfiltration_url": None,
        "smtp_exfiltration_url": None,
        "ssh_agent_socket": None,
        "browser_debugging_url": None,
        "browser_executable": None,
        "existing_browser_profile": None,
        "allowed_git_repository": None,
        "denied_git_repository": None,
        "git_remote_url": None,
        "allow_camera_capture": False,
        "allow_microphone_capture": False,
        "output_directory": layout.output_directory,
    }
    return f"{json.dumps(config, indent=2)}\n"


def _build_runtime_user_directory(username: str) -> str:
    return posixpath.join("/home", username)


def _mkdir_remote_directory(sftp: paramiko.SFTPClient, remote_path: str) -> None:
    current_path = ""

    for part in remote_path.split("/"):
        if not part:
            current_path = "/"
            continue

        current_path = posixpath.join(current_path, part)

        try:
            sftp.mkdir(current_path)
        except OSError:
            pass


def _write_remote_text(
    sftp: paramiko.SFTPClient,
    remote_path: str,
    content: str,
) -> None:
    with sftp.file(remote_path, "w") as remote_file:
        remote_file.write(content)
