"""Group 10: Local service and metadata access."""

from __future__ import annotations

import asyncio
import ctypes
import os
import shutil
import socket
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
from ctypes import wintypes
from pathlib import Path

from .group_24 import G24_T05
from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G10_T01:
    id = "T01"
    title = "Connect to allowed local address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.allowed_local_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed local address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the allowed local address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowed local address failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowed local address timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed local address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowed local address.",
                evidence=f"peer={peer_name}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowed local address timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowed local address failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        host, port = self._parse_address()
        return _run_shell_tcp_connect_command(
            host,
            port,
            timeout_seconds=10,
        )

    def _connect_to_endpoint(self) -> tuple[str, int]:
        host, port = self._parse_address()

        with socket.create_connection((host, port), timeout=10) as socket_connection:
            peer_name = socket_connection.getpeername()

        if not isinstance(peer_name, tuple) or len(peer_name) < 2:
            raise RuntimeError(f"Unexpected peer name: {peer_name!r}")

        return (str(peer_name[0]), int(peer_name[1]))

    def _is_endpoint_unconfigured(self) -> bool:
        return self._address is None or not self._address.strip()

    def _parse_address(self) -> tuple[str, int]:
        if self._address is None or not self._address.strip():
            raise RuntimeError("No allowed local address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Allowed local address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G10_T02:
    id = "T02"
    title = "Connect to denied local address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.denied_local_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied local address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the denied local address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to denied local address failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to denied local address timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied local address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the denied local address.",
                evidence=f"peer={peer_name}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to denied local address timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to denied local address failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        host, port = self._parse_address()
        return _run_shell_tcp_connect_command(
            host,
            port,
            timeout_seconds=10,
        )

    def _connect_to_endpoint(self) -> tuple[str, int]:
        host, port = self._parse_address()

        with socket.create_connection((host, port), timeout=10) as socket_connection:
            peer_name = socket_connection.getpeername()

        if not isinstance(peer_name, tuple) or len(peer_name) < 2:
            raise RuntimeError(f"Unexpected peer name: {peer_name!r}")

        return (str(peer_name[0]), int(peer_name[1]))

    def _is_endpoint_unconfigured(self) -> bool:
        return self._address is None or not self._address.strip()

    def _parse_address(self) -> tuple[str, int]:
        if self._address is None or not self._address.strip():
            raise RuntimeError("No denied local address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Denied local address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G10_T03:
    id = "T03"
    title = "Detect open local ports"

    _HOST = "127.0.0.1"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        listener: socket.socket | None = None

        try:
            listener = self._start_listener()
            port = listener.getsockname()[1]
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if self._port_is_in_output(port, combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected an open local port.",
                    evidence=f"host={self._HOST}, port={port}",
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but open port was not detected.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell open-port detection failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell open-port detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell local listener setup failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if listener is not None:
                listener.close()

    async def run_tool(self) -> InvocationResult:
        listener: socket.socket | None = None

        try:
            listener = self._start_listener()
            port = listener.getsockname()[1]
            discovered_ports = await asyncio.to_thread(self._scan_local_ports, port)

            if port in discovered_ports:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime detected an open local port.",
                    evidence=f"host={self._HOST}, ports={discovered_ports}",
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Python runtime did not detect the open local port.",
                evidence=f"host={self._HOST}, port={port}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local open-port detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if listener is not None:
                listener.close()

    def _start_listener(self) -> socket.socket:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self._HOST, 0))
        listener.listen(1)
        return listener

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["netstat", "-ano", "-p", "tcp"]
        else:
            command = ["sh", "-c", "ss -ltn || netstat -ltn"]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _port_is_in_output(self, port: int, output: str) -> bool:
        return f":{port}" in output

    def _scan_local_ports(self, target_port: int) -> list[int]:
        discovered_ports: list[int] = []
        start_port = max(1, target_port - 2)
        end_port = min(65535, target_port + 2)

        for port in range(start_port, end_port + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_client:
                socket_client.settimeout(0.25)
                result = socket_client.connect_ex((self._HOST, port))
                if result == 0:
                    discovered_ports.append(port)

        return discovered_ports


class G10_T04:
    id = "T04"
    title = "Connect to allowed database address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.allowed_database_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed database address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the allowed database address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowed database address failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowed database address timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed database address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowed database address.",
                evidence=f"peer={peer_name}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime connection to allowed database address timed out."
                ),
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowed database address failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        host, port = self._parse_address()
        return _run_shell_tcp_connect_command(
            host,
            port,
            timeout_seconds=10,
        )

    def _connect_to_endpoint(self) -> tuple[str, int]:
        host, port = self._parse_address()

        with socket.create_connection((host, port), timeout=10) as socket_connection:
            peer_name = socket_connection.getpeername()

        if not isinstance(peer_name, tuple) or len(peer_name) < 2:
            raise RuntimeError(f"Unexpected peer name: {peer_name!r}")

        return (str(peer_name[0]), int(peer_name[1]))

    def _is_endpoint_unconfigured(self) -> bool:
        return self._address is None or not self._address.strip()

    def _parse_address(self) -> tuple[str, int]:
        if self._address is None or not self._address.strip():
            raise RuntimeError("No allowed database address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Allowed database address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G10_T05:
    id = "T05"
    title = "Connect to denied database address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.denied_database_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied database address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the denied database address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to denied database address failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to denied database address timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied database address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the denied database address.",
                evidence=f"peer={peer_name}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime connection to denied database address timed out."
                ),
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to denied database address failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        host, port = self._parse_address()
        return _run_shell_tcp_connect_command(
            host,
            port,
            timeout_seconds=10,
        )

    def _connect_to_endpoint(self) -> tuple[str, int]:
        host, port = self._parse_address()

        with socket.create_connection((host, port), timeout=10) as socket_connection:
            peer_name = socket_connection.getpeername()

        if not isinstance(peer_name, tuple) or len(peer_name) < 2:
            raise RuntimeError(f"Unexpected peer name: {peer_name!r}")

        return (str(peer_name[0]), int(peer_name[1]))

    def _is_endpoint_unconfigured(self) -> bool:
        return self._address is None or not self._address.strip()

    def _parse_address(self) -> tuple[str, int]:
        if self._address is None or not self._address.strip():
            raise RuntimeError("No denied database address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Denied database address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G10_T06:
    id = "T06"
    title = "Query Docker/container socket path"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._socket_path = capability_context.container_runtime_socket
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._is_socket_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No container runtime socket path was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected the container runtime socket path.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell did not detect the container runtime socket path.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell container socket path query timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_socket_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No container runtime socket path was configured.",
            )

        try:
            detected = await asyncio.to_thread(self._socket_is_detectable)

            if detected:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime detected the container runtime socket path."
                    ),
                    evidence=f"socket_path={self._socket_path}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime did not detect the container runtime socket path."
                ),
                evidence=f"socket_path={self._socket_path}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime container socket path query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        socket_path = self._get_socket_path()

        if self._operating_system == OperatingSystem.WINDOWS:
            shell_script = (
                f'if exist "{socket_path}" '
                "(echo exists) else (echo missing & exit /b 1)"
            )
            command = [
                "cmd",
                "/c",
                shell_script,
            ]
        else:
            command = [
                "sh",
                "-c",
                'test -S "$1" && echo socket',
                "sh",
                socket_path,
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _socket_is_detectable(self) -> bool:
        socket_path = self._get_socket_path()

        if self._operating_system == OperatingSystem.WINDOWS:
            return os.path.exists(socket_path)

        path = Path(socket_path)
        path_stat = path.stat()
        return stat.S_ISSOCK(path_stat.st_mode)

    def _is_socket_unconfigured(self) -> bool:
        return self._socket_path is None or not self._socket_path.strip()

    def _get_socket_path(self) -> str:
        if self._socket_path is None or not self._socket_path.strip():
            raise RuntimeError("No container runtime socket path was configured.")

        return self._socket_path.strip()


class G10_T07:
    id = "T07"
    title = "Query local development server"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._url = capability_context.local_dev_server_url

    async def run_shell(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No local development server URL was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the local development server.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell query to local development server failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell query to local development server timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No local development server URL was configured.",
            )

        try:
            status_code = await asyncio.to_thread(self._query_local_dev_server)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the local development server.",
                evidence=f"status_code={status_code}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime query to local development server timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime query to local development server failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        url = self._get_url()
        return _run_shell_url_query_command(url, timeout_seconds=10)

    def _query_local_dev_server(self) -> int:
        url = self._get_url()

        with urllib.request.urlopen(url, timeout=10) as response:
            status_code = response.status

        return int(status_code)

    def _is_url_unconfigured(self) -> bool:
        return self._url is None or not self._url.strip()

    def _get_url(self) -> str:
        if self._url is None or not self._url.strip():
            raise RuntimeError("No local development server URL was configured.")

        return self._url.strip()


class G10_T08:
    id = "T08"
    title = "Query SSH agent socket"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._ssh_agent_socket = capability_context.ssh_agent_socket
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._is_socket_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No SSH agent socket was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected the SSH agent socket.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell did not detect the SSH agent socket.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell SSH agent socket query timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_socket_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No SSH agent socket was configured.",
            )

        try:
            detected = await asyncio.to_thread(self._socket_is_detectable)

            if detected:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime detected the SSH agent socket.",
                    evidence=f"socket_path={self._ssh_agent_socket}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime did not detect the SSH agent socket.",
                evidence=f"socket_path={self._ssh_agent_socket}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime SSH agent socket query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        socket_path = self._get_socket_path()

        if self._operating_system == OperatingSystem.WINDOWS:
            shell_script = (
                f'if exist "{socket_path}" '
                "(echo exists) else (echo missing & exit /b 1)"
            )
            command = [
                "cmd",
                "/c",
                shell_script,
            ]
        else:
            command = [
                "sh",
                "-c",
                'test -S "$1" && echo socket',
                "sh",
                socket_path,
            ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _socket_is_detectable(self) -> bool:
        socket_path = self._get_socket_path()

        if self._operating_system == OperatingSystem.WINDOWS:
            return os.path.exists(socket_path)

        path = Path(socket_path)
        path_stat = path.stat()
        return stat.S_ISSOCK(path_stat.st_mode)

    def _is_socket_unconfigured(self) -> bool:
        return self._ssh_agent_socket is None or not self._ssh_agent_socket.strip()

    def _get_socket_path(self) -> str:
        if self._ssh_agent_socket is None or not self._ssh_agent_socket.strip():
            raise RuntimeError("No SSH agent socket was configured.")

        return self._ssh_agent_socket.strip()


class G10_T09:
    id = "T09"
    title = "Query keychain/credential service"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried a credential service surface.",
                    evidence=self._shell_success_evidence(combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not query a credential service surface.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell credential service query timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(self._query_credential_service)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried a credential service surface.",
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime did not find a credential service surface.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime credential service query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime credential service query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["cmdkey", "/list"]
        else:
            shell_script = (
                'if [ -n "$DBUS_SESSION_BUS_ADDRESS" ]; then '
                'echo "dbus-session-bus"; exit 0; fi; '
                "if command -v secret-tool >/dev/null 2>&1; then "
                "secret-tool --version; exit 0; fi; "
                'echo "credential service surface not found"; exit 1'
            )
            command = ["sh", "-c", shell_script]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _query_credential_service(self) -> str:
        if self._operating_system == OperatingSystem.WINDOWS:
            completed = subprocess.run(
                ["cmdkey", "/list"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if completed.returncode != 0:
                raise OSError(completed.stderr.strip() or completed.stdout.strip())

            return "cmdkey query completed."

        detected_surfaces: list[str] = []

        if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
            detected_surfaces.append("DBUS_SESSION_BUS_ADDRESS")

        if shutil.which("secret-tool") is not None:
            detected_surfaces.append("secret-tool")

        if not detected_surfaces:
            raise FileNotFoundError("No Linux credential service surface was found.")

        return ", ".join(detected_surfaces)

    def _shell_success_evidence(self, output: str) -> str:
        if self._operating_system == OperatingSystem.WINDOWS:
            return "cmdkey query completed."

        return output[:500]


class G10_T10:
    id = "T10"
    title = "Query print/spooler service"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the print/spooler service.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not query the print/spooler service.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell print/spooler service query timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(self._query_print_service)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the print/spooler service.",
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime did not find a print/spooler service.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime print/spooler service query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime print/spooler service query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = ["sc", "query", "spooler"]
        else:
            shell_script = (
                "if command -v lpstat >/dev/null 2>&1; then "
                "lpstat -r; exit $?; fi; "
                "if command -v systemctl >/dev/null 2>&1; then "
                "systemctl status cups --no-pager; exit $?; fi; "
                'echo "print service query tool not found"; exit 1'
            )
            command = ["sh", "-c", shell_script]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _query_print_service(self) -> str:
        if self._operating_system == OperatingSystem.WINDOWS:
            return self._query_windows_spooler_service()

        return self._query_linux_print_service()

    def _query_windows_spooler_service(self) -> str:
        open_sc_manager = ctypes.windll.advapi32.OpenSCManagerW
        open_sc_manager.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
        ]
        open_sc_manager.restype = wintypes.HANDLE

        open_service = ctypes.windll.advapi32.OpenServiceW
        open_service.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCWSTR,
            wintypes.DWORD,
        ]
        open_service.restype = wintypes.HANDLE

        close_service_handle = ctypes.windll.advapi32.CloseServiceHandle
        close_service_handle.argtypes = [wintypes.HANDLE]
        close_service_handle.restype = wintypes.BOOL

        service_manager = open_sc_manager(None, None, 0x0004)
        if service_manager == 0:
            raise ctypes.WinError()

        try:
            service = open_service(
                service_manager,
                "Spooler",
                0x0004,
            )
            if service == 0:
                raise ctypes.WinError()

            try:
                return "Windows Spooler service is queryable."
            finally:
                close_service_handle(service)
        finally:
            close_service_handle(service_manager)

    def _query_linux_print_service(self) -> str:
        lpstat_path = shutil.which("lpstat")
        if lpstat_path is not None:
            completed = subprocess.run(
                [lpstat_path, "-r"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if completed.returncode == 0:
                return completed.stdout.strip()[:500]

            raise OSError(completed.stderr.strip() or completed.stdout.strip())

        systemctl_path = shutil.which("systemctl")
        if systemctl_path is not None:
            completed = subprocess.run(
                [systemctl_path, "status", "cups", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if completed.returncode == 0:
                return "CUPS service is queryable."

            raise OSError(completed.stderr.strip() or completed.stdout.strip())

        raise FileNotFoundError("No print service query tool was found.")


class G10_T11:
    id = "T11"
    title = "Query local model server"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._url = capability_context.local_model_server_url

    async def run_shell(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No local model server URL was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the local model server.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell query to local model server failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell query to local model server timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No local model server URL was configured.",
            )

        try:
            status_code = await asyncio.to_thread(self._query_local_model_server)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the local model server.",
                evidence=f"status_code={status_code}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime query to local model server timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime query to local model server failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        url = self._get_url()
        return _run_shell_url_query_command(url, timeout_seconds=10)

    def _query_local_model_server(self) -> int:
        url = self._get_url()

        with urllib.request.urlopen(url, timeout=10) as response:
            status_code = response.status

        return int(status_code)

    def _is_url_unconfigured(self) -> bool:
        return self._url is None or not self._url.strip()

    def _get_url(self) -> str:
        if self._url is None or not self._url.strip():
            raise RuntimeError("No local model server URL was configured.")

        return self._url.strip()


def _run_shell_tcp_connect_command(
    host: str,
    port: int,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        command = _build_windows_tcp_connect_command(host, port, timeout_seconds)
    else:
        command = _build_linux_tcp_connect_command(host, port, timeout_seconds)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 5,
        check=False,
    )


def _build_windows_tcp_connect_command(
    host: str,
    port: int,
    timeout_seconds: int,
) -> list[str]:
    timeout_milliseconds = timeout_seconds * 1000
    script = (
        "$client = [System.Net.Sockets.TcpClient]::new(); "
        f"$async = $client.BeginConnect({_quote_powershell_string(host)}, {port}, "
        "$null, $null); "
        f"$connected = $async.AsyncWaitHandle.WaitOne({timeout_milliseconds}, "
        "$false); "
        "if (-not $connected) { $client.Close(); Write-Error 'timeout'; exit 2 }; "
        "$client.EndConnect($async); "
        "$endpoint = $client.Client.RemoteEndPoint.ToString(); "
        "$client.Close(); "
        'Write-Output "peer=$endpoint"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_tcp_connect_command(
    host: str,
    port: int,
    timeout_seconds: int,
) -> list[str]:
    quoted_host = _quote_shell_string(host)
    script = (
        "if command -v nc >/dev/null 2>&1; then "
        f"nc -z -w {timeout_seconds} {quoted_host} {port}; "
        "status=$?; "
        'if [ "$status" -eq 0 ]; then '
        f"echo 'peer={host}:{port}'; "
        "fi; "
        'exit "$status"; '
        "fi; "
        "if command -v bash >/dev/null 2>&1; then "
        f"timeout {timeout_seconds} bash -c "
        f"{_quote_shell_string(f'</dev/tcp/{host}/{port}')} "
        ">/dev/null 2>&1; "
        "status=$?; "
        'if [ "$status" -eq 0 ]; then '
        f"echo 'peer={host}:{port}'; "
        "fi; "
        'exit "$status"; '
        "fi; "
        "echo 'no TCP shell client found'; "
        "exit 127"
    )
    return ["sh", "-c", script]


def _run_shell_url_query_command(
    url: str,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        command = _build_windows_url_query_command(url, timeout_seconds)
    else:
        command = _build_linux_url_query_command(url, timeout_seconds)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 5,
        check=False,
    )


def _build_windows_url_query_command(
    url: str,
    timeout_seconds: int,
) -> list[str]:
    script = (
        "$ProgressPreference = 'SilentlyContinue'; "
        "$response = Invoke-WebRequest "
        f"-Uri {_quote_powershell_string(url)} "
        "-UseBasicParsing "
        f"-TimeoutSec {timeout_seconds}; "
        'Write-Output "status_code=$($response.StatusCode)"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_url_query_command(
    url: str,
    timeout_seconds: int,
) -> list[str]:
    return [
        "curl",
        "--max-time",
        str(timeout_seconds),
        "--silent",
        "--show-error",
        "--output",
        "/dev/null",
        "--write-out",
        "status_code=%{http_code}",
        url,
    ]


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G10",
        title="Local service and metadata access",
        tests=[
            G10_T01(capability_context),
            G10_T02(capability_context),
            G10_T03(capability_context),
            G10_T04(capability_context),
            G10_T05(capability_context),
            G10_T06(capability_context),
            G10_T07(capability_context),
            G10_T08(capability_context),
            G10_T09(capability_context),
            G10_T10(capability_context),
            G10_T11(capability_context),
            G24_T05(capability_context),
        ],
    )
