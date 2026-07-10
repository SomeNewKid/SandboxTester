"""Set up a disposable VirtualBox sandbox VM after it starts."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from pathlib import Path

import paramiko

from .agent_profiles import get_python_agent_profile
from .guest_script_runner import GuestScriptRunner
from .models import GuestScriptResult

_SSH_CONNECT_TIMEOUT_SECONDS = 180
_SSH_POLL_INTERVAL_SECONDS = 2
_SSH_BANNER_TIMEOUT_SECONDS = 5
_HELLO_WORLD_SCRIPT = (
    "import json\n"
    "import platform\n"
    "\n"
    "message = {\n"
    '    "message": "hello from vm",\n'
    '    "python": platform.python_version(),\n'
    "}\n"
    "print(json.dumps(message))\n"
)


class _SshNotReadyError(RuntimeError):
    pass


@dataclass(frozen=True)
class _SshTarget:
    host: str
    port: int
    username: str
    password: str


class VirtualMachineSetup:
    """Configure a disposable sandbox VM for a test run."""

    def __init__(
        self,
        vm_name: str,
        ssh_host: str,
        ssh_port: int,
        username: str,
        password: str,
        script_path: Path | None = None,
        source_directory: Path | None = None,
        agent_name: str | None = None,
    ) -> None:
        self._vm_name = vm_name
        self._ssh_target = _SshTarget(
            host=ssh_host,
            port=ssh_port,
            username=username,
            password=password,
        )
        self._script_path = script_path
        self._source_directory = source_directory
        self._agent_name = agent_name

    def setup(self) -> GuestScriptResult:
        """Set up the disposable VM before running sandbox work."""
        print(
            f"Waiting for SSH on disposable run VM '{self._vm_name}' "
            f"at {self._ssh_target.host}:{self._ssh_target.port}."
        )
        client = self._wait_for_ssh()

        try:
            runner = GuestScriptRunner(client)
            if self._agent_name is not None:
                profile = get_python_agent_profile(self._agent_name)
                return runner.run_python_agent(profile)

            script_content = _load_script_content(self._script_path)
            return runner.run_python_script(script_content, self._source_directory)
        finally:
            client.close()

    def _wait_for_ssh(self) -> paramiko.SSHClient:
        deadline = time.monotonic() + _SSH_CONNECT_TIMEOUT_SECONDS
        last_error: Exception | None = None

        while time.monotonic() < deadline:
            try:
                self._wait_for_ssh_banner()
                return self._connect_ssh()
            except paramiko.AuthenticationException as error:
                raise RuntimeError(
                    "SSH is reachable, but authentication failed for user "
                    f"'{self._ssh_target.username}'. The base VM may have "
                    "been created with different credentials than the local "
                    "VirtualBox sandbox credential file."
                ) from error
            except (OSError, _SshNotReadyError, paramiko.SSHException) as error:
                last_error = error
                time.sleep(_SSH_POLL_INTERVAL_SECONDS)

        raise RuntimeError(
            "Timed out waiting for SSH on disposable VM "
            f"'{self._vm_name}': {last_error}"
        )

    def _wait_for_ssh_banner(self) -> None:
        with socket.create_connection(
            (self._ssh_target.host, self._ssh_target.port),
            timeout=5,
        ) as client_socket:
            client_socket.settimeout(_SSH_BANNER_TIMEOUT_SECONDS)
            banner = client_socket.recv(256)

        if not banner.startswith(b"SSH-"):
            raise _SshNotReadyError(
                f"Port is open but did not return an SSH banner: {banner!r}"
            )

    def _connect_ssh(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self._ssh_target.host,
            port=self._ssh_target.port,
            username=self._ssh_target.username,
            password=self._ssh_target.password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
            banner_timeout=10,
            auth_timeout=10,
        )
        return client


def _load_script_content(script_path: Path | None) -> str:
    if script_path is None:
        return _HELLO_WORLD_SCRIPT

    resolved_path = script_path.expanduser().resolve()

    if not resolved_path.exists():
        raise FileNotFoundError(f"Script file does not exist: {resolved_path}")

    if not resolved_path.is_file():
        raise ValueError(f"Script path is not a file: {resolved_path}")

    return resolved_path.read_text(encoding="utf-8")
