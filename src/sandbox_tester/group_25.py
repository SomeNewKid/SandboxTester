"""Group 25: Network Policy."""

from __future__ import annotations

import asyncio
import os
import random
import socket
import struct
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_DNS_TEST_DOMAIN = "example.com"
_DNS_TEST_SERVER = "1.1.1.1"
_DNS_TEST_PORT = 53
_NO_SHELL_CANDIDATE_EXIT_CODE = 127
_METADATA_TIMEOUT_SECONDS = 2
_INTRANET_CONNECT_TIMEOUT_SECONDS = 2
_LINUX_PRIVILEGED_BIND_ADDRESS = "127.0.0.1"
_LINUX_PRIVILEGED_BIND_PORT = 80
_PROXY_ENVIRONMENT_VARIABLES = [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
]
_DEFAULT_INTRANET_PORTS = [
    445,
    80,
    443,
    5000,
    5001,
]
_DEFAULT_METADATA_PROBES = [
    (
        "AWS",
        "http://169.254.169.254/latest/meta-data/",
        {},
    ),
    (
        "Azure",
        "http://169.254.169.254/metadata/instance?api-version=2021-02-01",
        {"Metadata": "true"},
    ),
    (
        "Google",
        "http://169.254.169.254/computeMetadata/v1/",
        {"Metadata-Flavor": "Google"},
    ),
    (
        "Google",
        "http://metadata.google.internal/computeMetadata/v1/",
        {"Metadata-Flavor": "Google"},
    ),
]


class G25_T01:
    id = "T15"
    title = "UDP send/receive"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_test(
            command_builder=lambda: _build_udp_shell_command(self._operating_system),
            allowed_summary="Shell sent and received UDP data.",
            denied_summary="Shell could not send and receive UDP data.",
            not_applicable_summary="No supported shell UDP test command was available.",
            timeout_summary="Shell UDP send/receive test timed out.",
            failure_summary="Shell UDP send/receive test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(_run_udp_echo_with_python)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime sent and received UDP data.",
                evidence=evidence,
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
                summary="Python runtime UDP send/receive test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G25_T02:
    id = "T16"
    title = "ICMP ping / raw socket creation"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_test(
            command_builder=lambda: _build_ping_shell_command(self._operating_system),
            allowed_summary="Shell ran an ICMP ping command.",
            denied_summary="Shell could not run an ICMP ping command.",
            not_applicable_summary="No supported shell ping command was available.",
            timeout_summary="Shell ICMP ping test timed out.",
            failure_summary="Shell ICMP ping test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(_create_raw_icmp_socket)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime created a raw ICMP socket.",
                evidence=evidence,
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
                summary="Python runtime could not create a raw ICMP socket.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G25_T03:
    id = "T17"
    title = "DNS over TCP vs UDP"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_test(
            command_builder=lambda: _build_dns_shell_command(self._operating_system),
            allowed_summary="Shell queried DNS over both UDP and TCP.",
            denied_summary="Shell could not query DNS over both UDP and TCP.",
            not_applicable_summary="No supported shell DNS command was available.",
            timeout_summary="Shell DNS transport test timed out.",
            failure_summary="Shell DNS transport test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            udp_answer_count = await asyncio.to_thread(
                _query_dns_with_python,
                use_tcp=False,
            )
            tcp_answer_count = await asyncio.to_thread(
                _query_dns_with_python,
                use_tcp=True,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried DNS over both UDP and TCP.",
                evidence=(
                    f"server={_DNS_TEST_SERVER}; domain={_DNS_TEST_DOMAIN}; "
                    f"udp_answers={udp_answer_count}; "
                    f"tcp_answers={tcp_answer_count}"
                ),
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
                summary="Python runtime DNS transport query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G25_T04:
    id = "T18"
    title = "Connect to link-local metadata endpoint"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._metadata_endpoint_url = capability_context.metadata_endpoint_url

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_test(
            command_builder=lambda: _build_metadata_shell_command(
                self._operating_system, self._metadata_endpoint_url
            ),
            allowed_summary="Shell connected to a metadata endpoint.",
            denied_summary="Shell could not connect to a metadata endpoint.",
            not_applicable_summary=(
                "No supported shell metadata endpoint command was available."
            ),
            timeout_summary="Shell metadata endpoint probe timed out.",
            failure_summary="Shell metadata endpoint probe failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _probe_metadata_endpoints_with_python,
                self._metadata_endpoint_url,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to a metadata endpoint.",
                evidence=evidence,
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
                summary="Python runtime could not connect to a metadata endpoint.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime metadata endpoint probe failed.",
                evidence=repr(error),
            )


class G25_T05:
    id = "T19"
    title = "Connect to allowed intranet target"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._intranet_target = capability_context.allowed_intranet_target

    async def run_shell(self) -> InvocationResult:
        if _target_is_unconfigured(self._intranet_target):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed intranet target was configured.",
            )

        return await _run_shell_test(
            command_builder=lambda: _build_intranet_shell_command(
                self._operating_system,
                str(self._intranet_target),
            ),
            allowed_summary="Shell connected to the allowed intranet target.",
            denied_summary="Shell could not connect to the allowed intranet target.",
            not_applicable_summary=(
                "No supported shell intranet connection command was available."
            ),
            timeout_summary="Shell allowed intranet connection test timed out.",
            failure_summary="Shell allowed intranet connection test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        if _target_is_unconfigured(self._intranet_target):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed intranet target was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _connect_to_intranet_target_with_python,
                str(self._intranet_target),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowed intranet target.",
                evidence=evidence,
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
                summary=(
                    "Python runtime could not connect to the allowed intranet target."
                ),
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G25_T06:
    id = "T20"
    title = "Connect to denied intranet target"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._intranet_target = capability_context.denied_intranet_target

    async def run_shell(self) -> InvocationResult:
        if _target_is_unconfigured(self._intranet_target):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied intranet target was configured.",
            )

        return await _run_shell_test(
            command_builder=lambda: _build_intranet_shell_command(
                self._operating_system,
                str(self._intranet_target),
            ),
            allowed_summary="Shell connected to the denied intranet target.",
            denied_summary="Shell could not connect to the denied intranet target.",
            not_applicable_summary=(
                "No supported shell intranet connection command was available."
            ),
            timeout_summary="Shell denied intranet connection test timed out.",
            failure_summary="Shell denied intranet connection test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        if _target_is_unconfigured(self._intranet_target):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied intranet target was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _connect_to_intranet_target_with_python,
                str(self._intranet_target),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the denied intranet target.",
                evidence=evidence,
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
                summary=(
                    "Python runtime could not connect to the denied intranet target."
                ),
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G25_T07:
    id = "T21"
    title = "Listen on loopback interface"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_test(
            command_builder=lambda: _build_listen_shell_command(
                self._operating_system,
                "127.0.0.1",
            ),
            allowed_summary="Shell listened on the loopback interface.",
            denied_summary="Shell could not listen on the loopback interface.",
            not_applicable_summary=(
                "No supported shell listening socket command was available."
            ),
            timeout_summary="Shell loopback listening socket test timed out.",
            failure_summary="Shell loopback listening socket test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _listen_with_python,
                "127.0.0.1",
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime listened on the loopback interface.",
                evidence=evidence,
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
                summary="Python runtime could not listen on the loopback interface.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G25_T08:
    id = "T22"
    title = "Listen on public/all interfaces"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_test(
            command_builder=lambda: _build_listen_shell_command(
                self._operating_system,
                "0.0.0.0",
            ),
            allowed_summary="Shell listened on all network interfaces.",
            denied_summary="Shell could not listen on all network interfaces.",
            not_applicable_summary=(
                "No supported shell listening socket command was available."
            ),
            timeout_summary="Shell all-interface listening socket test timed out.",
            failure_summary="Shell all-interface listening socket test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _listen_with_python,
                "0.0.0.0",
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime listened on all network interfaces.",
                evidence=evidence,
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
                summary="Python runtime could not listen on all network interfaces.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G25_T09:
    id = "T23"
    title = "Bind Linux privileged loopback port"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux privileged port binding is not applicable.",
            )

        return await _run_shell_test(
            command_builder=_build_privileged_port_shell_command,
            allowed_summary="Shell bound a Linux privileged loopback port.",
            denied_summary="Shell could not bind a Linux privileged loopback port.",
            not_applicable_summary="Linux privileged loopback port was unavailable.",
            timeout_summary="Shell privileged port binding test timed out.",
            failure_summary="Shell privileged port binding test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux privileged port binding is not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(_bind_privileged_port_with_python)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime bound a Linux privileged loopback port.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            if _is_address_in_use(error):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux privileged loopback port was unavailable.",
                    evidence=repr(error),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not bind a Linux privileged loopback port."
                ),
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G25_T10:
    id = "T24"
    title = "Detect outbound proxy configuration"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_test(
            command_builder=lambda: _build_proxy_detection_shell_command(
                self._operating_system,
            ),
            allowed_summary="Shell detected outbound proxy configuration.",
            denied_summary="Shell could not detect outbound proxy configuration.",
            not_applicable_summary=(
                "No supported shell proxy detection command was available."
            ),
            timeout_summary="Shell proxy detection test timed out.",
            failure_summary="Shell proxy detection test failed.",
        )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _detect_proxy_configuration_with_python,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected outbound proxy configuration.",
                evidence=evidence,
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
                summary="Python runtime proxy detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G25",
        title="Network Policy",
        tests=[],
    )


async def _run_shell_test(
    command_builder: Callable[[], list[str]],
    allowed_summary: str,
    denied_summary: str,
    not_applicable_summary: str,
    timeout_summary: str,
    failure_summary: str,
) -> InvocationResult:
    try:
        command = command_builder()
        completed = await asyncio.to_thread(_run_command, command)
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=completed.stdout.strip()[:500],
            )

        if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=not_applicable_summary,
                evidence=_failure_evidence(completed, combined_output),
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
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
            summary=timeout_summary,
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=failure_summary,
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_udp_shell_command(operating_system: OperatingSystem) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _build_windows_udp_shell_command()

    return _build_linux_udp_shell_command()


def _build_windows_udp_shell_command() -> list[str]:
    script = """
$ErrorActionPreference = 'Stop'
$payload = [Text.Encoding]::UTF8.GetBytes('sandbox-tester-udp')
$server = [Net.Sockets.UdpClient]::new(0)
$serverEndpoint = [Net.IPEndPoint]::new([Net.IPAddress]::Loopback, 0)
$client = [Net.Sockets.UdpClient]::new()
try {
    $port = $server.Client.LocalEndPoint.Port
    [void]$client.Send($payload, $payload.Length, '127.0.0.1', $port)
    $remote = [Net.IPEndPoint]::new([Net.IPAddress]::Any, 0)
    $received = $server.Receive([ref]$remote)
    $text = [Text.Encoding]::UTF8.GetString($received)
    if ($text -ne 'sandbox-tester-udp') {
        throw "Unexpected UDP payload: $text"
    }
    "port=$port; bytes=$($received.Length)"
}
finally {
    $client.Close()
    $server.Close()
}
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _build_linux_udp_shell_command() -> list[str]:
    script = """
set -u
if ! command -v nc >/dev/null 2>&1; then
    echo 'nc not found'
    exit 127
fi
port=$((40000 + ($$ % 20000)))
tmp_file=$(mktemp)
trap 'rm -f "$tmp_file"; kill "$server_pid" 2>/dev/null || true' EXIT
nc -u -l 127.0.0.1 "$port" > "$tmp_file" &
server_pid=$!
sleep 0.2
printf 'sandbox-tester-udp' | nc -u -w 1 127.0.0.1 "$port"
sleep 0.2
if grep -q 'sandbox-tester-udp' "$tmp_file"; then
    printf 'port=%s; bytes=18\\n' "$port"
    exit 0
fi
echo 'UDP payload was not received.'
exit 1
"""
    return ["sh", "-c", script]


def _build_ping_shell_command(operating_system: OperatingSystem) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return ["ping", "-n", "1", "-w", "1000", "127.0.0.1"]

    return ["ping", "-c", "1", "-W", "1", "127.0.0.1"]


def _build_proxy_detection_shell_command(
    operating_system: OperatingSystem,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _build_windows_proxy_detection_shell_command()

    return _build_linux_proxy_detection_shell_command()


def _build_windows_proxy_detection_shell_command() -> list[str]:
    proxy_names = ", ".join(
        _quote_powershell_string(name) for name in _PROXY_ENVIRONMENT_VARIABLES
    )
    script = f"""
$ErrorActionPreference = 'Stop'
$names = @({proxy_names})
$presentNames = @()
foreach ($name in $names) {{
    $value = [Environment]::GetEnvironmentVariable($name)
    if (-not [string]::IsNullOrWhiteSpace($value)) {{
        $presentNames += $name
    }}
}}
$winhttp = netsh winhttp show proxy 2>$null
$winhttpProxyPresent = $false
if ($LASTEXITCODE -eq 0) {{
    $winhttpText = $winhttp -join ' '
    $winhttpProxyPresent = (
        $winhttpText -notmatch 'Direct access' -and
        $winhttpText -notmatch 'no proxy server'
    )
}}
$parts = @(
    "env_proxy_names=[$($presentNames -join ',')]",
    "env_proxy_count=$($presentNames.Count)",
    "winhttp_proxy_present=$winhttpProxyPresent",
    "netsh_available=$($LASTEXITCODE -eq 0)"
)
Write-Output ($parts -join '; ')
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _build_linux_proxy_detection_shell_command() -> list[str]:
    names = " ".join(_PROXY_ENVIRONMENT_VARIABLES)
    printf_format = (
        "env_proxy_names=[%s]; env_proxy_count=%s; "
        "winhttp_proxy_present=not_applicable; netsh_available=False\\n"
    )
    script = f"""
set -u
present=""
count=0
for name in {names}; do
    value=$(printenv "$name" 2>/dev/null || true)
    if [ -n "$value" ]; then
        present="${{present}}${{name}},"
        count=$((count + 1))
    fi
done
printf {printf_format!r} "$present" "$count"
"""
    return ["sh", "-c", script]


def _build_dns_shell_command(operating_system: OperatingSystem) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _build_windows_dns_shell_command()

    return _build_linux_dns_shell_command()


def _build_intranet_shell_command(
    operating_system: OperatingSystem,
    target: str,
) -> list[str]:
    host, ports = _parse_intranet_target(target)

    if operating_system == OperatingSystem.WINDOWS:
        return _build_windows_intranet_shell_command(host, ports)

    return _build_linux_intranet_shell_command(host, ports)


def _build_listen_shell_command(
    operating_system: OperatingSystem,
    bind_address: str,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _build_windows_listen_shell_command(bind_address)

    return _build_linux_listen_shell_command(bind_address)


def _build_privileged_port_shell_command() -> list[str]:
    script = f"""
set -u
bind_address={_quote_shell_string(_LINUX_PRIVILEGED_BIND_ADDRESS)}
bind_port={_LINUX_PRIVILEGED_BIND_PORT}
if command -v ss >/dev/null 2>&1; then
    if ss -ltn "sport = :$bind_port" | grep -q ":$bind_port"; then
        echo "bind_address=$bind_address; port=$bind_port; available=False"
        exit {_NO_SHELL_CANDIDATE_EXIT_CODE}
    fi
fi
if ! command -v nc >/dev/null 2>&1; then
    echo 'nc not found'
    exit {_NO_SHELL_CANDIDATE_EXIT_CODE}
fi
nc -l "$bind_address" "$bind_port" >/dev/null 2>&1 &
listener_pid=$!
sleep 0.2
if kill -0 "$listener_pid" 2>/dev/null; then
    kill "$listener_pid" 2>/dev/null || true
    echo "bind_address=$bind_address; port=$bind_port; listening=True"
    exit 0
fi
echo "bind_address=$bind_address; port=$bind_port; listening=False"
exit 1
"""
    return ["sh", "-c", script]


def _build_windows_listen_shell_command(bind_address: str) -> list[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
$address = [Net.IPAddress]::Parse('{bind_address}')
$listener = [Net.Sockets.TcpListener]::new($address, 0)
try {{
    $listener.Start()
    $endpoint = $listener.LocalEndpoint
    Write-Output "bind_address={bind_address}; port=$($endpoint.Port); listening=True"
}}
finally {{
    $listener.Stop()
}}
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _build_linux_listen_shell_command(bind_address: str) -> list[str]:
    quoted_bind_address = _quote_shell_string(bind_address)
    script = f"""
set -u
if command -v nc >/dev/null 2>&1; then
    bind_address={quoted_bind_address}
    nc -l "$bind_address" 0 >/dev/null 2>&1 &
    listener_pid=$!
    sleep 0.2
    if kill -0 "$listener_pid" 2>/dev/null; then
        kill "$listener_pid" 2>/dev/null || true
        echo "bind_address=$bind_address; port=ephemeral; listening=True"
        exit 0
    fi
    echo "bind_address=$bind_address; listening=False"
    exit 1
fi
echo 'nc not found'
exit {_NO_SHELL_CANDIDATE_EXIT_CODE}
"""
    return ["sh", "-c", script]


def _build_windows_intranet_shell_command(host: str, ports: list[int]) -> list[str]:
    port_values = ", ".join(str(port) for port in ports)
    script = f"""
$ErrorActionPreference = 'Stop'
$hostName = {_quote_powershell_string(host)}
$ports = @({port_values})
foreach ($port in $ports) {{
    $client = [Net.Sockets.TcpClient]::new()
    try {{
        $async = $client.BeginConnect($hostName, $port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(
            {_INTRANET_CONNECT_TIMEOUT_SECONDS * 1000},
            $false
        )
        if ($connected) {{
            $client.EndConnect($async)
            Write-Output "host=$hostName; port=$port; connected=True"
            exit 0
        }}
    }}
    catch {{
    }}
    finally {{
        $client.Close()
    }}
}}
Write-Output "host=$hostName; ports=[$($ports -join ',')]; connected=False"
exit 1
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _build_linux_intranet_shell_command(host: str, ports: list[int]) -> list[str]:
    quoted_host = _quote_shell_string(host)
    port_values = " ".join(str(port) for port in ports)
    script = f"""
set -u
if ! command -v nc >/dev/null 2>&1; then
    echo 'nc not found'
    exit {_NO_SHELL_CANDIDATE_EXIT_CODE}
fi
host={quoted_host}
for port in {port_values}; do
    if nc -z -w {_INTRANET_CONNECT_TIMEOUT_SECONDS} \\
        "$host" "$port" >/dev/null 2>&1; then
        echo "host=$host; port=$port; connected=True"
        exit 0
    fi
done
echo "host=$host; ports=[{",".join(str(port) for port in ports)}]; connected=False"
exit 1
"""
    return ["sh", "-c", script]


def _build_metadata_shell_command(
    operating_system: OperatingSystem,
    metadata_endpoint_url: str | None,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _build_windows_metadata_shell_command(metadata_endpoint_url)

    return _build_linux_metadata_shell_command(metadata_endpoint_url)


def _build_windows_metadata_shell_command(
    metadata_endpoint_url: str | None,
) -> list[str]:
    probes = _metadata_probes(metadata_endpoint_url)
    probe_lines = []

    for provider, url, headers in probes:
        header_lines = "".join(
            f"$request.Headers.Add('{name}', '{value}');\n"
            for name, value in headers.items()
        )
        probe_lines.append(
            f"""
$request = [System.Net.HttpWebRequest]::Create('{url}')
$request.Method = 'GET'
$request.Timeout = {_METADATA_TIMEOUT_SECONDS * 1000}
$request.ReadWriteTimeout = {_METADATA_TIMEOUT_SECONDS * 1000}
$request.UserAgent = 'SandboxTester'
{header_lines}
try {{
    $response = $request.GetResponse()
    try {{
        $length = $response.ContentLength
        if ($length -lt 0) {{ $length = 0 }}
        $status = [int]$response.StatusCode
        Write-Output "provider={provider}; url={url}; status=$status; bytes=$length"
        exit 0
    }}
    finally {{
        $response.Close()
    }}
}}
catch [System.Net.WebException] {{
    if ($_.Exception.Response -ne $null) {{
        $response = $_.Exception.Response
        try {{
            $status = [int]$response.StatusCode
            Write-Output "provider={provider}; url={url}; status=$status; bytes=0"
            exit 0
        }}
        finally {{
            $response.Close()
        }}
    }}
}}
"""
        )

    script = (
        "$ErrorActionPreference = 'SilentlyContinue'\n"
        + "\n".join(probe_lines)
        + "\nWrite-Output 'No metadata endpoint responded.'\nexit 1\n"
    )
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _build_linux_metadata_shell_command(
    metadata_endpoint_url: str | None,
) -> list[str]:
    probes = _metadata_probes(metadata_endpoint_url)
    probe_lines = []

    for provider, url, headers in probes:
        quoted_url = _quote_shell_string(url)
        curl_headers = " ".join(
            f"-H {_quote_shell_string(f'{name}: {value}')}"
            for name, value in headers.items()
        )
        wget_headers = " ".join(
            f"--header={_quote_shell_string(f'{name}: {value}')}"
            for name, value in headers.items()
        )
        curl_command = (
            "curl -sS -o /dev/null "
            f"-m {_METADATA_TIMEOUT_SECONDS} "
            "-w '%{http_code}' "
            f"{curl_headers} {quoted_url} "
            "2>/dev/null || true"
        )
        wget_command = (
            "wget -q -O /dev/null "
            f"-T {_METADATA_TIMEOUT_SECONDS} "
            f"--server-response {wget_headers} {quoted_url} "
            "2>&1 | awk '/HTTP\\// { code=$2 } END { print code }'"
        )
        probe_lines.append(
            f"""
if command -v curl >/dev/null 2>&1; then
    status=$({curl_command})
elif command -v wget >/dev/null 2>&1; then
    status=$({wget_command})
else
    echo 'curl/wget not found'
    exit {_NO_SHELL_CANDIDATE_EXIT_CODE}
fi
if [ -n "$status" ] && [ "$status" != "000" ]; then
    echo 'provider={provider}; url={url}; status='"$status"'; bytes=0'
    exit 0
fi
"""
        )

    script = (
        "set -u\n"
        + "\n".join(probe_lines)
        + "\necho 'No metadata endpoint responded.'\nexit 1\n"
    )
    return ["sh", "-c", script]


def _build_windows_dns_shell_command() -> list[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
$udp = nslookup -type=A {_DNS_TEST_DOMAIN} {_DNS_TEST_SERVER}
if ($LASTEXITCODE -ne 0) {{
    throw 'UDP DNS query failed.'
}}
$tcp = nslookup -vc -type=A {_DNS_TEST_DOMAIN} {_DNS_TEST_SERVER}
if ($LASTEXITCODE -ne 0) {{
    throw 'TCP DNS query failed.'
}}
"server={_DNS_TEST_SERVER}; domain={_DNS_TEST_DOMAIN}; udp=True; tcp=True"
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _build_linux_dns_shell_command() -> list[str]:
    script = f"""
set -u
if command -v dig >/dev/null 2>&1; then
    dig +time=2 +tries=1 @{_DNS_TEST_SERVER} {_DNS_TEST_DOMAIN} A >/dev/null
    udp_status=$?
    dig +tcp +time=2 +tries=1 @{_DNS_TEST_SERVER} {_DNS_TEST_DOMAIN} A >/dev/null
    tcp_status=$?
elif command -v nslookup >/dev/null 2>&1; then
    nslookup -type=A {_DNS_TEST_DOMAIN} {_DNS_TEST_SERVER} >/dev/null
    udp_status=$?
    nslookup -vc -type=A {_DNS_TEST_DOMAIN} {_DNS_TEST_SERVER} >/dev/null
    tcp_status=$?
else
    echo 'dig/nslookup not found'
    exit 127
fi
if [ "$udp_status" -eq 0 ] && [ "$tcp_status" -eq 0 ]; then
    echo 'server={_DNS_TEST_SERVER}; domain={_DNS_TEST_DOMAIN}; udp=True; tcp=True'
    exit 0
fi
echo "udp_status=$udp_status; tcp_status=$tcp_status"
exit 1
"""
    return ["sh", "-c", script]


def _run_udp_echo_with_python() -> str:
    payload = b"sandbox-tester-udp"
    received_payload = b""
    server_ready = threading.Event()
    server_error: list[BaseException] = []
    port_holder: list[int] = []

    def run_server() -> None:
        nonlocal received_payload

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
                server.bind(("127.0.0.1", 0))
                server.settimeout(5)
                port_holder.append(server.getsockname()[1])
                server_ready.set()
                received_payload, _address = server.recvfrom(1024)
        except BaseException as error:
            server_error.append(error)
            server_ready.set()

    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    server_ready.wait(timeout=5)

    if server_error:
        raise server_error[0]

    if not port_holder:
        raise TimeoutError("UDP server did not report a port.")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.sendto(payload, ("127.0.0.1", port_holder[0]))

    server_thread.join(timeout=5)

    if received_payload != payload:
        raise RuntimeError("UDP payload was not received.")

    return f"port={port_holder[0]}; bytes={len(received_payload)}"


def _create_raw_icmp_socket() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP):
        return "family=AF_INET; type=SOCK_RAW; protocol=IPPROTO_ICMP"


def _query_dns_with_python(use_tcp: bool) -> int:
    query = _build_dns_query_packet(_DNS_TEST_DOMAIN)

    if use_tcp:
        response = _query_dns_tcp(query)
    else:
        response = _query_dns_udp(query)

    return _read_dns_answer_count(response)


def _query_dns_udp(query: bytes) -> bytes:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.settimeout(5)
        client.sendto(query, (_DNS_TEST_SERVER, _DNS_TEST_PORT))
        response, _address = client.recvfrom(4096)

    return response


def _query_dns_tcp(query: bytes) -> bytes:
    with socket.create_connection(
        (_DNS_TEST_SERVER, _DNS_TEST_PORT),
        timeout=5,
    ) as client:
        client.sendall(struct.pack("!H", len(query)) + query)
        length_prefix = _recv_exactly(client, 2)
        response_length = struct.unpack("!H", length_prefix)[0]
        return _recv_exactly(client, response_length)


def _build_dns_query_packet(domain: str) -> bytes:
    transaction_id = random.randint(0, 65535)
    header = struct.pack("!HHHHHH", transaction_id, 0x0100, 1, 0, 0, 0)
    question = b"".join(
        bytes([len(label)]) + label.encode("ascii") for label in domain.split(".")
    )
    question += b"\x00"
    question += struct.pack("!HH", 1, 1)
    return header + question


def _read_dns_answer_count(response: bytes) -> int:
    if len(response) < 12:
        raise RuntimeError("DNS response was too short.")

    answer_count = struct.unpack("!H", response[6:8])[0]

    if answer_count < 1:
        raise RuntimeError("DNS response contained no answers.")

    return answer_count


def _recv_exactly(client: socket.socket, byte_count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = byte_count

    while remaining > 0:
        chunk = client.recv(remaining)

        if not chunk:
            raise ConnectionError("Socket closed before enough data was received.")

        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)


def _probe_metadata_endpoints_with_python(
    metadata_endpoint_url: str | None,
) -> str:
    errors: list[str] = []

    for provider, url, headers in _metadata_probes(metadata_endpoint_url):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SandboxTester",
                **headers,
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=_METADATA_TIMEOUT_SECONDS,
            ) as response:
                content_length = response.headers.get("Content-Length")
                bytes_count = int(content_length) if content_length else 0
                status = response.status
                return _metadata_evidence(provider, url, status, bytes_count)
        except urllib.error.HTTPError as error:
            return _metadata_evidence(provider, url, error.code, 0)
        except urllib.error.URLError as error:
            errors.append(f"{provider}:{error.reason!r}")
        except TimeoutError as error:
            errors.append(f"{provider}:{error!r}")

    raise OSError("; ".join(errors) or "No metadata endpoint responded.")


def _connect_to_intranet_target_with_python(target: str) -> str:
    host, ports = _parse_intranet_target(target)
    errors: list[str] = []

    for port in ports:
        try:
            with socket.create_connection(
                (host, port),
                timeout=_INTRANET_CONNECT_TIMEOUT_SECONDS,
            ):
                return f"host={host}; port={port}; connected=True"
        except OSError as error:
            errors.append(f"{port}:{error.__class__.__name__}")

    raise OSError(
        f"host={host}; ports={ports}; connected=False; errors=[{','.join(errors)}]"
    )


def _listen_with_python(bind_address: str) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((bind_address, 0))
        server.listen(1)
        port = server.getsockname()[1]

        return f"bind_address={bind_address}; port={port}; listening=True"


def _bind_privileged_port_with_python() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(
            (
                _LINUX_PRIVILEGED_BIND_ADDRESS,
                _LINUX_PRIVILEGED_BIND_PORT,
            )
        )
        server.listen(1)

        return (
            f"bind_address={_LINUX_PRIVILEGED_BIND_ADDRESS}; "
            f"port={_LINUX_PRIVILEGED_BIND_PORT}; "
            "listening=True"
        )


def _detect_proxy_configuration_with_python(
    operating_system: OperatingSystem,
) -> str:
    proxy_names = [
        name for name in _PROXY_ENVIRONMENT_VARIABLES if os.environ.get(name)
    ]

    if operating_system == OperatingSystem.WINDOWS:
        winhttp_available, winhttp_proxy_present = _detect_winhttp_proxy()
    else:
        winhttp_available = False
        winhttp_proxy_present = False

    return (
        f"env_proxy_names=[{','.join(proxy_names)}]; "
        f"env_proxy_count={len(proxy_names)}; "
        f"winhttp_proxy_present={winhttp_proxy_present}; "
        f"netsh_available={winhttp_available}"
    )


def _detect_winhttp_proxy() -> tuple[bool, bool]:
    completed = subprocess.run(
        ["netsh", "winhttp", "show", "proxy"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        return False, False

    output = f"{completed.stdout}\n{completed.stderr}".lower()
    proxy_present = "direct access" not in output and "no proxy server" not in output

    return True, proxy_present


def _parse_intranet_target(target: str) -> tuple[str, list[int]]:
    normalized_target = target.strip()

    if "://" in normalized_target:
        parsed_url = urllib.parse.urlparse(normalized_target)
        host = parsed_url.hostname

        if host is None:
            raise ValueError(f"Could not parse intranet target: {target!r}")

        if parsed_url.port is not None:
            return host, [parsed_url.port]

        if parsed_url.scheme == "http":
            return host, [80]

        if parsed_url.scheme == "https":
            return host, [443]

        return host, list(_DEFAULT_INTRANET_PORTS)

    if normalized_target.count(":") == 1:
        host, port_text = normalized_target.rsplit(":", maxsplit=1)

        if port_text.isdigit():
            return host, [int(port_text)]

    return normalized_target, list(_DEFAULT_INTRANET_PORTS)


def _metadata_probes(
    metadata_endpoint_url: str | None,
) -> list[tuple[str, str, dict[str, str]]]:
    if metadata_endpoint_url is not None and metadata_endpoint_url.strip():
        return [("Configured", metadata_endpoint_url.strip(), {})]

    return list(_DEFAULT_METADATA_PROBES)


def _metadata_evidence(
    provider: str,
    url: str,
    status: int,
    bytes_count: int,
) -> str:
    return f"provider={provider}; url={url}; status={status}; bytes={bytes_count}"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _target_is_unconfigured(target: str | None) -> bool:
    return target is None or target.strip() == ""


def _is_address_in_use(error: OSError) -> bool:
    return error.errno in {
        48,
        98,
        10048,
    }


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
