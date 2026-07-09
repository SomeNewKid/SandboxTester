"""Run Python scripts inside a sandbox guest over SSH."""

from __future__ import annotations

import posixpath
import uuid

import paramiko

from .models import GuestScriptResult

_REMOTE_SCRIPT_DIRECTORY = "/tmp"


class GuestScriptRunner:
    """Copy Python script content into the guest and execute it."""

    def __init__(self, client: paramiko.SSHClient) -> None:
        self._client = client

    def run_python_script(self, script_content: str) -> GuestScriptResult:
        """Copy and run a Python script in the guest VM."""
        script_path = _create_remote_script_path()
        self._write_remote_script(script_path, script_content)
        return self._execute_remote_script(script_path)

    def _write_remote_script(self, script_path: str, script_content: str) -> None:
        script_bytes = script_content.encode("utf-8")

        with self._client.open_sftp() as sftp:
            with sftp.file(script_path, "wb") as script_file:
                script_file.write(script_bytes)

    def _execute_remote_script(self, script_path: str) -> GuestScriptResult:
        command = f"python3 {script_path}"
        _, stdout, stderr = self._client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        stdout_text = stdout.read().decode("utf-8", errors="replace").strip()
        stderr_text = stderr.read().decode("utf-8", errors="replace").strip()
        return GuestScriptResult(
            script_path=script_path,
            command=command,
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
        )


def _create_remote_script_path() -> str:
    script_name = f"sandbox-script-{uuid.uuid4().hex}.py"
    return posixpath.join(_REMOTE_SCRIPT_DIRECTORY, script_name)
