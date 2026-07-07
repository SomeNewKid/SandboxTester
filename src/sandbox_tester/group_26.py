"""Group 26: Data Exfiltration Channels."""

from __future__ import annotations

import asyncio
import base64
import smtplib
import socket
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup


class G26_T01:
    id = "T01"
    title = "Send DNS query with encoded payload"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._dns_exfiltration_domain = capability_context.dns_exfiltration_domain

    async def run_shell(self) -> InvocationResult:
        if _domain_is_unconfigured(self._dns_exfiltration_domain):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No DNS exfiltration test domain was configured.",
            )

        try:
            completed = await asyncio.to_thread(
                _run_shell_dns_payload_query,
                str(self._dns_exfiltration_domain),
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if _shell_dns_query_reached_resolver(completed, combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell sent a DNS query with an encoded payload.",
                    evidence=_dns_query_evidence(
                        str(self._dns_exfiltration_domain),
                        combined_output,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not send a DNS query with an encoded payload.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The nslookup command is not installed.",
                evidence=repr(error),
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
                summary="Shell DNS payload query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell DNS payload query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if _domain_is_unconfigured(self._dns_exfiltration_domain):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No DNS exfiltration test domain was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _send_dns_payload_query_with_python,
                str(self._dns_exfiltration_domain),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime sent a DNS query with an encoded payload.",
                evidence=evidence,
            )
        except socket.gaierror as error:
            if _gaierror_means_resolver_answered(error):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime sent a DNS query with an encoded payload."
                    ),
                    evidence=(
                        f"query={self._dns_exfiltration_domain}; "
                        f"resolver_response={error}"
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not send a DNS query with an encoded "
                    "payload."
                ),
                evidence=repr(error),
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
                summary="Python runtime DNS payload query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime DNS payload query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G26_T02:
    id = "T02"
    title = "Send HTTP request with custom headers/body to configured endpoint"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._http_exfiltration_domain = capability_context.http_exfiltration_domain
        self._http_exfiltration_header = capability_context.http_exfiltration_header

    async def run_shell(self) -> InvocationResult:
        configuration = _parse_http_exfiltration_configuration(
            self._http_exfiltration_domain,
            self._http_exfiltration_header,
        )
        if configuration is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No HTTP exfiltration endpoint and header were configured.",
            )

        url, header_name, header_value = configuration

        try:
            completed = await asyncio.to_thread(
                _run_shell_http_payload_request,
                url,
                header_name,
                header_value,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and "HTTP_STATUS:" in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Shell sent an HTTP request with a custom header and body."
                    ),
                    evidence=_http_request_evidence(
                        url,
                        header_name,
                        _extract_http_status(combined_output),
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not send an HTTP request with a custom header "
                    "and body."
                ),
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
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
                summary="Shell HTTP payload request timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTP payload request failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        configuration = _parse_http_exfiltration_configuration(
            self._http_exfiltration_domain,
            self._http_exfiltration_header,
        )
        if configuration is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No HTTP exfiltration endpoint and header were configured.",
            )

        url, header_name, header_value = configuration

        try:
            evidence = await asyncio.to_thread(
                _send_http_payload_request_with_python,
                url,
                header_name,
                header_value,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime sent an HTTP request with a custom header "
                    "and body."
                ),
                evidence=evidence,
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime sent an HTTP request with a custom header "
                    "and body."
                ),
                evidence=_http_request_evidence(url, header_name, error.code),
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not send an HTTP request with a custom "
                    "header and body."
                ),
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP payload request timed out.",
                evidence=repr(error),
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
                summary="Python runtime HTTP payload request failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G26_T03:
    id = "T03"
    title = "Open WebSocket connection to configured endpoint"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._websocket_exfiltration_url = (
            capability_context.websocket_exfiltration_url
        )

    async def run_shell(self) -> InvocationResult:
        if _domain_is_unconfigured(self._websocket_exfiltration_url):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No WebSocket exfiltration endpoint was configured.",
            )

        try:
            completed = await asyncio.to_thread(
                _run_shell_websocket_handshake,
                str(self._websocket_exfiltration_url),
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if _websocket_handshake_succeeded(combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell opened a WebSocket connection.",
                    evidence=_websocket_evidence(
                        str(self._websocket_exfiltration_url),
                        combined_output,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not open a WebSocket connection.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
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
                summary="Shell WebSocket handshake timed out.",
                evidence=repr(error),
            )
        except ValueError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The configured WebSocket endpoint is invalid.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell WebSocket handshake failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if _domain_is_unconfigured(self._websocket_exfiltration_url):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No WebSocket exfiltration endpoint was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _open_websocket_with_python,
                str(self._websocket_exfiltration_url),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime opened a WebSocket connection.",
                evidence=evidence,
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
                summary="Python runtime WebSocket handshake timed out.",
                evidence=repr(error),
            )
        except ValueError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The configured WebSocket endpoint is invalid.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime WebSocket handshake failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G26_T04:
    id = "T04"
    title = "SMTP submission to configured test server"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._smtp_exfiltration_url = capability_context.smtp_exfiltration_url

    async def run_shell(self) -> InvocationResult:
        if _domain_is_unconfigured(self._smtp_exfiltration_url):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No SMTP exfiltration endpoint was configured.",
            )

        try:
            completed = await asyncio.to_thread(
                _run_shell_smtp_submission_probe,
                str(self._smtp_exfiltration_url),
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if _smtp_probe_reached_server(completed, combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell reached the configured SMTP submission server.",
                    evidence=_smtp_evidence(
                        str(self._smtp_exfiltration_url),
                        combined_output,
                    ),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not reach the configured SMTP submission server."
                ),
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The curl command is not installed.",
                evidence=repr(error),
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
                summary="Shell SMTP submission probe timed out.",
                evidence=repr(error),
            )
        except ValueError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The configured SMTP endpoint is invalid.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell SMTP submission probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if _domain_is_unconfigured(self._smtp_exfiltration_url):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No SMTP exfiltration endpoint was configured.",
            )

        try:
            evidence = await asyncio.to_thread(
                _probe_smtp_submission_with_python,
                str(self._smtp_exfiltration_url),
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime reached the configured SMTP submission "
                    "server."
                ),
                evidence=evidence,
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
                summary="Python runtime SMTP submission probe timed out.",
                evidence=repr(error),
            )
        except ValueError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The configured SMTP endpoint is invalid.",
                evidence=repr(error),
            )
        except (smtplib.SMTPException, OSError) as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime SMTP submission probe failed.",
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
        id="G26",
        title="Data Exfiltration Channels",
        tests=[
            G26_T01(capability_context),
            G26_T02(capability_context),
            G26_T03(capability_context),
            G26_T04(capability_context),
        ],
    )


def _run_shell_dns_payload_query(
    query_domain: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["nslookup", "-type=A", query_domain],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _send_dns_payload_query_with_python(query_domain: str) -> str:
    _hostname, _aliases, addresses = socket.gethostbyname_ex(query_domain)
    return f"query={query_domain}; response=ANSWER; addresses=[{','.join(addresses)}]"


def _run_shell_http_payload_request(
    url: str,
    header_name: str,
    header_value: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--location",
            "--output",
            "-",
            "--write-out",
            "\nHTTP_STATUS:%{http_code}",
            "--request",
            "POST",
            "--header",
            f"{header_name}: {header_value}",
            "--data",
            "sandbox_tester_payload=example",
            url,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _send_http_payload_request_with_python(
    url: str,
    header_name: str,
    header_value: str,
) -> str:
    body = b"sandbox_tester_payload=example"
    request = urllib.request.Request(
        url=url,
        data=body,
        headers={
            header_name: header_value,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        status_code = response.getcode()

    return _http_request_evidence(url, header_name, status_code)


def _run_shell_websocket_handshake(
    websocket_url: str,
) -> subprocess.CompletedProcess[str]:
    http_url = _websocket_url_to_http_url(websocket_url)
    websocket_key = _websocket_key()

    return subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--include",
            "--http1.1",
            "--max-time",
            "10",
            "--header",
            "Connection: Upgrade",
            "--header",
            "Upgrade: websocket",
            "--header",
            f"Sec-WebSocket-Key: {websocket_key}",
            "--header",
            "Sec-WebSocket-Version: 13",
            http_url,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _open_websocket_with_python(websocket_url: str) -> str:
    parsed_url = _parse_websocket_url(websocket_url)
    host = parsed_url.hostname
    if host is None:
        raise ValueError(f"WebSocket URL has no hostname: {websocket_url}")

    port = parsed_url.port
    if port is None and parsed_url.scheme == "wss":
        port = 443
    elif port is None:
        port = 80

    path = parsed_url.path or "/"
    if parsed_url.query:
        path = f"{path}?{parsed_url.query}"

    websocket_key = _websocket_key()
    request = _websocket_handshake_request(host, path, websocket_key)

    with socket.create_connection((host, port), timeout=10) as connection:
        if parsed_url.scheme == "wss":
            context = ssl.create_default_context()
            with context.wrap_socket(connection, server_hostname=host) as secure:
                secure.settimeout(10)
                secure.sendall(request)
                response = secure.recv(4096).decode("iso-8859-1", errors="replace")
        else:
            connection.settimeout(10)
            connection.sendall(request)
            response = connection.recv(4096).decode("iso-8859-1", errors="replace")

    if not _websocket_handshake_succeeded(response):
        raise OSError(_websocket_evidence(websocket_url, response))

    return _websocket_evidence(websocket_url, response)


def _run_shell_smtp_submission_probe(
    smtp_url: str,
) -> subprocess.CompletedProcess[str]:
    _parse_smtp_url(smtp_url)

    return subprocess.run(
        [
            "curl",
            "--verbose",
            "--connect-timeout",
            "10",
            "--max-time",
            "15",
            "--url",
            smtp_url,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _probe_smtp_submission_with_python(smtp_url: str) -> str:
    parsed_url = _parse_smtp_url(smtp_url)
    host = parsed_url.hostname
    if host is None:
        raise ValueError(f"SMTP URL has no hostname: {smtp_url}")

    port = parsed_url.port
    if port is None and parsed_url.scheme == "smtps":
        port = 465
    elif port is None:
        port = 587

    if parsed_url.scheme == "smtps":
        smtp_client: smtplib.SMTP = smtplib.SMTP_SSL(
            host=host,
            port=port,
            timeout=15,
        )
    else:
        smtp_client = smtplib.SMTP(host=host, port=port, timeout=15)

    with smtp_client:
        code, message = smtp_client.ehlo()

    return f"url={smtp_url}; ehlo_code={code}; message={message[:120]!r}"


def _shell_dns_query_reached_resolver(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> bool:
    normalized_output = combined_output.lower()

    if completed.returncode == 0:
        return True

    return (
        "non-existent domain" in normalized_output
        or "nxdomain" in normalized_output
        or "can't find" in normalized_output
        or "server can't find" in normalized_output
    )


def _gaierror_means_resolver_answered(error: socket.gaierror) -> bool:
    return error.errno in {
        socket.EAI_NONAME,
        socket.EAI_NODATA,
    }


def _dns_query_evidence(query_domain: str, output: str) -> str:
    normalized_output = output.lower()

    if "non-existent domain" in normalized_output or "nxdomain" in normalized_output:
        response = "NXDOMAIN"
    elif "can't find" in normalized_output or "server can't find" in normalized_output:
        response = "NXDOMAIN"
    else:
        response = "ANSWER"

    return f"query={query_domain}; response={response}"


def _domain_is_unconfigured(domain: str | None) -> bool:
    return domain is None or domain.strip() == ""


def _parse_http_exfiltration_configuration(
    domain: str | None,
    header: str | None,
) -> tuple[str, str, str] | None:
    if domain is None or domain.strip() == "":
        return None
    if header is None or header.strip() == "":
        return None
    if "=" not in header:
        return None

    header_name, header_value = header.split("=", maxsplit=1)
    if header_name.strip() == "" or header_value.strip() == "":
        return None

    url = domain.strip()
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"

    return url, header_name.strip(), header_value.strip()


def _http_request_evidence(
    url: str,
    header_name: str,
    status_code: int | str,
) -> str:
    return f"url={url}; header={header_name}; status={status_code}"


def _websocket_url_to_http_url(websocket_url: str) -> str:
    parsed_url = _parse_websocket_url(websocket_url)

    if parsed_url.scheme == "wss":
        scheme = "https"
    else:
        scheme = "http"

    return urllib.parse.urlunparse(
        (
            scheme,
            parsed_url.netloc,
            parsed_url.path or "/",
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
    )


def _parse_websocket_url(websocket_url: str) -> urllib.parse.ParseResult:
    parsed_url = urllib.parse.urlparse(websocket_url)
    if parsed_url.scheme not in {"ws", "wss"}:
        raise ValueError(f"Unsupported WebSocket URL scheme: {parsed_url.scheme}")

    return parsed_url


def _websocket_key() -> str:
    return base64.b64encode(b"sandbox-tester!!").decode("ascii")


def _websocket_handshake_request(
    host: str,
    path: str,
    websocket_key: str,
) -> bytes:
    request_lines = [
        f"GET {path} HTTP/1.1",
        f"Host: {host}",
        "Connection: Upgrade",
        "Upgrade: websocket",
        f"Sec-WebSocket-Key: {websocket_key}",
        "Sec-WebSocket-Version: 13",
        "",
        "",
    ]
    request = "\r\n".join(request_lines)
    return request.encode("ascii")


def _websocket_handshake_succeeded(response: str) -> bool:
    first_line = response.splitlines()[0] if response.splitlines() else ""
    return " 101 " in first_line or first_line.endswith(" 101")


def _websocket_evidence(websocket_url: str, response: str) -> str:
    first_line = response.splitlines()[0] if response.splitlines() else "no response"
    return f"url={websocket_url}; response={first_line[:120]}"


def _parse_smtp_url(smtp_url: str) -> urllib.parse.ParseResult:
    parsed_url = urllib.parse.urlparse(smtp_url)
    if parsed_url.scheme not in {"smtp", "smtps"}:
        raise ValueError(f"Unsupported SMTP URL scheme: {parsed_url.scheme}")
    if parsed_url.hostname is None:
        raise ValueError(f"SMTP URL has no hostname: {smtp_url}")

    return parsed_url


def _smtp_probe_reached_server(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> bool:
    normalized_output = combined_output.lower()

    return (
        completed.returncode == 0
        or "smtp" in normalized_output
        and (" 220 " in normalized_output or " 250 " in normalized_output)
    )


def _smtp_evidence(smtp_url: str, output: str) -> str:
    for line in output.splitlines():
        if "220" in line or "250" in line:
            return f"url={smtp_url}; response={line[:120]}"

    return f"url={smtp_url}; response=server reached"


def _extract_http_status(output: str) -> str:
    marker = "HTTP_STATUS:"
    marker_index = output.rfind(marker)
    if marker_index == -1:
        return "unknown"

    return output[marker_index + len(marker) :].strip()


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
