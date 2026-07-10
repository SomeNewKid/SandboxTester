"""Run Python scripts inside a sandbox guest over SSH."""

from __future__ import annotations

import os
import posixpath
import shlex
import uuid
from fnmatch import fnmatch
from pathlib import Path

import paramiko

from .models import GuestScriptResult, PythonAgentProfile

_REMOTE_SCRIPT_DIRECTORY = "/tmp"
_REMOTE_SOURCE_DIRECTORY = "/tmp"
_REMOTE_AGENT_DIRECTORY = "/tmp"
_REMOTE_VENV_DIRECTORY = "/tmp"


class GuestScriptRunner:
    """Copy Python script content into the guest and execute it."""

    def __init__(self, client: paramiko.SSHClient) -> None:
        self._client = client

    def run_python_script(
        self,
        script_content: str,
        source_directory: Path | None = None,
    ) -> GuestScriptResult:
        """Copy and run a Python script in the guest VM."""
        script_path = _create_remote_script_path()
        source_path = self._write_remote_source_directory(source_directory, [])
        self._write_remote_script(script_path, script_content)
        return self._execute_remote_script(
            script_path,
            source_path,
            python_executable="python3",
        )

    def run_python_agent(
        self,
        profile: PythonAgentProfile,
        environment_variables: dict[str, str] | None = None,
    ) -> GuestScriptResult:
        """Copy a Python agent source tree, install dependencies, and run it."""
        script_path = _create_remote_script_path()
        venv_path = _create_remote_venv_path()
        python_executable = posixpath.join(venv_path, "bin", "python")
        source_path = self._write_remote_agent_source(profile)
        self._write_remote_script(script_path, profile.entry_script)
        self._create_virtual_environment(venv_path)
        self._install_dependencies(python_executable, profile.dependencies)
        return self._execute_remote_script(
            script_path,
            source_path,
            python_executable=python_executable,
            environment_variables=environment_variables,
        )

    def _write_remote_source_directory(
        self,
        source_directory: Path | None,
        exclude_patterns: list[str],
    ) -> str | None:
        if source_directory is None:
            return None

        resolved_source_directory = source_directory.expanduser().resolve()

        if not resolved_source_directory.exists():
            raise FileNotFoundError(
                f"Source directory does not exist: {resolved_source_directory}"
            )

        if not resolved_source_directory.is_dir():
            raise ValueError(
                f"Source directory path is not a directory: {resolved_source_directory}"
            )

        remote_source_path = _create_remote_source_path()

        with self._client.open_sftp() as sftp:
            _mkdir_remote_directory(sftp, remote_source_path)
            self._write_remote_directory(
                sftp,
                resolved_source_directory,
                remote_source_path,
                exclude_patterns,
            )

        return remote_source_path

    def _write_remote_agent_source(self, profile: PythonAgentProfile) -> str:
        resolved_source_directory = profile.source_directory.expanduser().resolve()

        if not resolved_source_directory.exists():
            raise FileNotFoundError(
                f"Agent source directory does not exist: {resolved_source_directory}"
            )

        if not resolved_source_directory.is_dir():
            raise ValueError(
                "Agent source directory path is not a directory: "
                f"{resolved_source_directory}"
            )

        remote_source_parent = _create_remote_agent_path()
        remote_package_path = posixpath.join(
            remote_source_parent,
            profile.package_directory_name,
        )

        with self._client.open_sftp() as sftp:
            _mkdir_remote_directory(sftp, remote_package_path)
            self._write_remote_directory(
                sftp,
                resolved_source_directory,
                remote_package_path,
                profile.exclude_patterns,
            )

        return remote_source_parent

    def _write_remote_directory(
        self,
        sftp: paramiko.SFTPClient,
        source_directory: Path,
        remote_source_path: str,
        exclude_patterns: list[str],
    ) -> None:
        for root, directory_names, file_names in os.walk(source_directory):
            directory_names[:] = [
                name
                for name in directory_names
                if not _is_excluded(name, exclude_patterns)
            ]
            root_path = Path(root)
            relative_root = root_path.relative_to(source_directory)
            remote_root = _join_remote_path(remote_source_path, relative_root)
            _mkdir_remote_directory(sftp, remote_root)

            for file_name in file_names:
                if _is_excluded(file_name, exclude_patterns):
                    continue

                local_file_path = root_path / file_name
                remote_file_path = posixpath.join(remote_root, file_name)
                sftp.put(str(local_file_path), remote_file_path)

    def _write_remote_script(self, script_path: str, script_content: str) -> None:
        script_bytes = script_content.encode("utf-8")

        with self._client.open_sftp() as sftp:
            with sftp.file(script_path, "wb") as script_file:
                script_file.write(script_bytes)

    def _execute_remote_script(
        self,
        script_path: str,
        source_path: str | None,
        python_executable: str,
        environment_variables: dict[str, str] | None = None,
    ) -> GuestScriptResult:
        command = _create_remote_python_command(
            script_path,
            source_path,
            python_executable,
            environment_variables,
        )
        _, stdout, stderr = self._client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        stdout_text = stdout.read().decode("utf-8", errors="replace").strip()
        stderr_text = stderr.read().decode("utf-8", errors="replace").strip()
        return GuestScriptResult(
            script_path=script_path,
            source_path=source_path,
            command=command,
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
        )

    def _create_virtual_environment(self, venv_path: str) -> None:
        command = f"python3 -m venv {shlex.quote(venv_path)}"
        _run_remote_command(self._client, command)

    def _install_dependencies(
        self,
        python_executable: str,
        dependencies: list[str],
    ) -> None:
        quoted_python = shlex.quote(python_executable)
        _run_remote_command(
            self._client, f"{quoted_python} -m pip install --upgrade pip"
        )

        if not dependencies:
            return

        quoted_dependencies = " ".join(
            shlex.quote(dependency) for dependency in dependencies
        )
        _run_remote_command(
            self._client,
            f"{quoted_python} -m pip install {quoted_dependencies}",
        )


def _create_remote_script_path() -> str:
    script_name = f"sandbox-script-{uuid.uuid4().hex}.py"
    return posixpath.join(_REMOTE_SCRIPT_DIRECTORY, script_name)


def _create_remote_source_path() -> str:
    directory_name = f"sandbox-source-{uuid.uuid4().hex}"
    return posixpath.join(_REMOTE_SOURCE_DIRECTORY, directory_name)


def _create_remote_agent_path() -> str:
    directory_name = f"sandbox-agent-{uuid.uuid4().hex}"
    return posixpath.join(_REMOTE_AGENT_DIRECTORY, directory_name)


def _create_remote_venv_path() -> str:
    directory_name = f"sandbox-venv-{uuid.uuid4().hex}"
    return posixpath.join(_REMOTE_VENV_DIRECTORY, directory_name)


def _join_remote_path(base_path: str, relative_path: Path) -> str:
    if str(relative_path) == ".":
        return base_path

    return posixpath.join(base_path, relative_path.as_posix())


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


def _is_excluded(name: str, exclude_patterns: list[str]) -> bool:
    return any(fnmatch(name, pattern) for pattern in exclude_patterns)


def _create_remote_python_command(
    script_path: str,
    source_path: str | None,
    python_executable: str,
    environment_variables: dict[str, str] | None,
) -> str:
    quoted_script_path = shlex.quote(script_path)
    quoted_python = shlex.quote(python_executable)
    environment_prefix = _create_environment_prefix(environment_variables)

    if source_path is None:
        return f"{environment_prefix}{quoted_python} {quoted_script_path}"

    quoted_source_path = shlex.quote(source_path)
    return (
        f"{environment_prefix}PYTHONPATH={quoted_source_path}:$PYTHONPATH "
        f"{quoted_python} {quoted_script_path}"
    )


def _create_environment_prefix(
    environment_variables: dict[str, str] | None,
) -> str:
    if not environment_variables:
        return ""

    assignments = [
        f"{name}={shlex.quote(value)}" for name, value in environment_variables.items()
    ]
    return f"{' '.join(assignments)} "


def _run_remote_command(client: paramiko.SSHClient, command: str) -> None:
    _, stdout, stderr = client.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    stdout_text = stdout.read().decode("utf-8", errors="replace").strip()
    stderr_text = stderr.read().decode("utf-8", errors="replace").strip()

    if exit_code != 0:
        raise RuntimeError(
            f"Remote command failed with exit code {exit_code}: {command}\n"
            f"stdout:\n{stdout_text}\n"
            f"stderr:\n{stderr_text}"
        )
