"""Set up a disposable QEMU sandbox VM after it starts."""

from __future__ import annotations

import posixpath
import shlex
import socket
import time
from dataclasses import replace

import paramiko

from virtualbox_sandbox.agent_profiles import get_python_agent_profile
from virtualbox_sandbox.guest_run_layout import create_sandbox_tester_run_layout
from virtualbox_sandbox.guest_script_runner import GuestScriptRunner
from virtualbox_sandbox.models import GuestRunLayout, GuestScriptResult

from .models import GuestCredentials

_SSH_CONNECT_TIMEOUT_SECONDS = 300
_SSH_POLL_INTERVAL_SECONDS = 2
_SSH_BANNER_TIMEOUT_SECONDS = 5


class _SshNotReadyError(RuntimeError):
    pass


class QemuVirtualMachineSetup:
    """Configure a disposable QEMU VM for a test run."""

    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        credentials: GuestCredentials,
        agent_name: str | None = None,
        agent_verbose: bool = False,
        agent_serialize_evidence: bool = False,
    ) -> None:
        self._ssh_host = ssh_host
        self._ssh_port = ssh_port
        self._credentials = credentials
        self._agent_name = agent_name
        self._agent_verbose = agent_verbose
        self._agent_serialize_evidence = agent_serialize_evidence
        self._guest_run_layout: GuestRunLayout | None = None

    def setup(self) -> GuestScriptResult:
        """Set up the disposable VM before running sandbox work."""
        print(
            "Waiting for SSH on disposable QEMU VM "
            f"at {self._ssh_host}:{self._ssh_port}."
        )
        client = self._wait_for_ssh()

        try:
            runner = GuestScriptRunner(client)
            if self._agent_name is not None:
                profile = get_python_agent_profile(self._agent_name)
                environment_variables = self._prepare_agent_environment(client)
                result = runner.run_python_agent(profile, environment_variables)
                return self._download_agent_artifacts(client, result)

            raise ValueError("QEMU sandbox currently requires --agent.")
        finally:
            client.close()

    def shutdown(self) -> None:
        """Request a graceful guest shutdown over SSH."""
        client = self._wait_for_ssh()

        try:
            _run_sudo_command(
                client,
                self._credentials.password,
                "shutdown now",
                check=False,
            )
        finally:
            client.close()

    def _prepare_agent_environment(
        self,
        client: paramiko.SSHClient,
    ) -> dict[str, str]:
        environment_variables = _resolve_openai_environment_variables()

        if self._agent_name != "sandbox_tester":
            return environment_variables

        layout = create_sandbox_tester_run_layout(client, self._credentials.user)
        self._guest_run_layout = layout
        environment_variables["SANDBOX_TESTER_CONFIG_PATH"] = layout.config_path

        if self._agent_verbose:
            environment_variables["SANDBOX_TESTER_VERBOSE"] = "1"

        if self._agent_serialize_evidence:
            environment_variables["SANDBOX_TESTER_SERIALIZE_EVIDENCE"] = "1"

        return environment_variables

    def _download_agent_artifacts(
        self,
        client: paramiko.SSHClient,
        result: GuestScriptResult,
    ) -> GuestScriptResult:
        if self._agent_name != "sandbox_tester" or self._guest_run_layout is None:
            return result

        report_path = f"{self._guest_run_layout.output_directory}/report.json"
        config_path = self._guest_run_layout.config_path
        screenshot_paths = [
            f"{self._guest_run_layout.output_directory}/browser_screenshot.png",
            (
                f"{self._guest_run_layout.output_directory}/"
                "playwright_shell_screenshot.png"
            ),
            (
                f"{self._guest_run_layout.output_directory}/"
                "playwright_tool_screenshot.png"
            ),
        ]
        artifacts = dict(result.artifacts)

        with client.open_sftp() as sftp:
            try:
                with sftp.file(report_path, "r") as report_file:
                    report_bytes = report_file.read()
                with sftp.file(config_path, "r") as config_file:
                    config_bytes = config_file.read()
            except OSError as error:
                if result.exit_code == 0:
                    raise FileNotFoundError(
                        "Sandbox Tester completed successfully, but guest "
                        f"artifacts were not found below {report_path}."
                    ) from error

                return result

            screenshot_artifacts = _read_screenshot_artifacts(sftp, screenshot_paths)

        artifacts["report.json"] = report_bytes.decode("utf-8", errors="replace")
        artifacts["config.json"] = config_bytes.decode("utf-8", errors="replace")
        artifacts.update(screenshot_artifacts)

        return replace(result, artifacts=artifacts)

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
                    f"'{self._credentials.user}'."
                ) from error
            except (OSError, _SshNotReadyError, paramiko.SSHException) as error:
                last_error = error
                time.sleep(_SSH_POLL_INTERVAL_SECONDS)

        raise RuntimeError(f"Timed out waiting for SSH on QEMU VM: {last_error}")

    def _wait_for_ssh_banner(self) -> None:
        with socket.create_connection(
            (self._ssh_host, self._ssh_port),
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
            hostname=self._ssh_host,
            port=self._ssh_port,
            username=self._credentials.user,
            password=self._credentials.password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
            banner_timeout=10,
            auth_timeout=10,
        )
        return client


def _read_screenshot_artifacts(
    sftp: paramiko.SFTPClient,
    screenshot_paths: list[str],
) -> dict[str, bytes]:
    artifacts: dict[str, bytes] = {}

    for screenshot_path in screenshot_paths:
        try:
            with sftp.file(screenshot_path, "rb") as screenshot_file:
                screenshot_bytes = screenshot_file.read()
        except OSError:
            continue

        artifacts[posixpath.basename(screenshot_path)] = screenshot_bytes

    return artifacts


def _resolve_openai_environment_variables() -> dict[str, str]:
    environment_variables: dict[str, str] = {}

    try:
        import os

        value = os.environ.get("OPENAI_API_KEY")
    except OSError:
        value = None

    if value is not None:
        environment_variables["OPENAI_API_KEY"] = value

    return environment_variables


def _run_sudo_command(
    client: paramiko.SSHClient,
    password: str,
    command: str,
    check: bool = True,
) -> None:
    quoted_password = shlex.quote(password)
    remote_command = f"printf '%s\\n' {quoted_password} | sudo -S {command}"
    _, stdout, stderr = client.exec_command(remote_command)
    exit_code = stdout.channel.recv_exit_status()

    if not check or exit_code == 0:
        return

    stdout_text = stdout.read().decode("utf-8", errors="replace").strip()
    stderr_text = stderr.read().decode("utf-8", errors="replace").strip()
    raise RuntimeError(
        f"Remote sudo command failed with exit code {exit_code}: {command}\n"
        f"stdout:\n{stdout_text}\n"
        f"stderr:\n{stderr_text}"
    )
