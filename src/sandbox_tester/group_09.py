"""Group 09: Network access."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .group_25 import (
    G25_T01,
    G25_T02,
    G25_T03,
    G25_T04,
    G25_T05,
    G25_T06,
    G25_T07,
    G25_T08,
    G25_T09,
    G25_T10,
)
from .group_26 import G26_T01, G26_T02, G26_T03, G26_T04
from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


class G09_T01:
    id = "T01"
    title = "Resolve DNS name"

    _DOMAIN_NAME = "examplemalwaredomain.com"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}"

            if self._has_valid_non_authoritative_answer(combined_output):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell resolved the DNS name.",
                    evidence=combined_output.strip()[:500],
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary=(
                        "Shell DNS lookup succeeded, but no valid non-authoritative "
                        "IP address was found."
                    ),
                    evidence=completed.stdout[:500],
                )

            if self._is_nslookup_missing(completed.stderr):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The nslookup command is not installed.",
                    evidence=completed.stderr[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell DNS lookup failed.",
                evidence=completed.stderr[:500],
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
                summary="Shell DNS lookup timed out.",
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
            _hostname, _aliases, ip_addresses = await asyncio.to_thread(
                socket.gethostbyname_ex,
                self._DOMAIN_NAME,
            )
            valid_ip_addresses = [
                ip_address
                for ip_address in ip_addresses
                if self._is_valid_ip_address(ip_address)
            ]

            if valid_ip_addresses:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime resolved the DNS name.",
                    evidence=", ".join(valid_ip_addresses[:10]),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Python runtime did not return a valid IP address.",
                evidence=", ".join(ip_addresses[:10]),
            )
        except socket.gaierror as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime DNS lookup failed.",
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
                summary="Python runtime DNS lookup timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = ["nslookup", self._DOMAIN_NAME]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _has_valid_non_authoritative_answer(self, output: str) -> bool:
        lines = output.splitlines()
        has_non_authoritative_answer = any(
            line.strip().startswith("Non-authoritative answer") for line in lines
        )

        if not has_non_authoritative_answer:
            return False

        for line in lines:
            normalized_line = line.strip()
            if normalized_line.startswith("Address:"):
                _label, _separator, value = normalized_line.partition(":")
                if self._is_valid_ip_address(value.strip()):
                    return True

            if normalized_line.startswith("Addresses:"):
                _label, _separator, value = normalized_line.partition(":")
                if self._is_valid_ip_address(value.strip()):
                    return True

            if self._is_valid_ip_address(normalized_line):
                return True

        return False

    def _is_valid_ip_address(self, value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    def _is_nslookup_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T02:
    id = "T02"
    title = "Connect to known HTTP endpoint"

    _URL = "http://gov.uk"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the known HTTP endpoint.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTP connection failed.",
                evidence=combined_output[:500],
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
                summary="Shell HTTP connection timed out.",
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
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the known HTTP endpoint.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the HTTP endpoint.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP connection failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP connection timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._URL,
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        return urllib.request.urlopen(request, timeout=10)

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T03:
    id = "T03"
    title = "Connect to known HTTPS endpoint"

    _URL = "https://gov.uk"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the known HTTPS endpoint.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTPS connection failed.",
                evidence=combined_output[:500],
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
                summary="Shell HTTPS connection timed out.",
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
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the known HTTPS endpoint.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the HTTPS endpoint.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTPS connection failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTPS connection timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._URL,
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        return urllib.request.urlopen(request, timeout=10)

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T05:
    id = "T05"
    title = "Connect to allowlisted domain"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._domain_name = capability_context.allowed_domain

    async def run_shell(self) -> InvocationResult:
        if self._is_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowlisted domain was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the configured allowlisted domain.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowlisted domain failed.",
                evidence=combined_output[:500],
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
                summary="Shell connection to allowlisted domain timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowlisted domain was configured.",
            )

        try:
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowlisted domain.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the allowlisted domain.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowlisted domain failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowlisted domain timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._get_url(),
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._get_url(),
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        return urllib.request.urlopen(request, timeout=10)

    def _get_url(self) -> str:
        if self._domain_name is None:
            raise RuntimeError("No allowlisted domain was configured.")

        domain_name = self._domain_name.strip()
        if domain_name.startswith("http://") or domain_name.startswith("https://"):
            return domain_name

        return f"https://{domain_name}"

    def _is_domain_unconfigured(self) -> bool:
        return self._domain_name is None or not self._domain_name.strip()

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T06:
    id = "T06"
    title = "Connect to blocked test domain"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._domain_name = capability_context.denied_domain

    async def run_shell(self) -> InvocationResult:
        if self._is_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No blocked test domain was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the configured blocked test domain.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to blocked test domain failed.",
                evidence=combined_output[:500],
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
                summary="Shell connection to blocked test domain timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No blocked test domain was configured.",
            )

        try:
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the blocked test domain.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the blocked test domain.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to blocked test domain failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to blocked test domain timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._get_url(),
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._get_url(),
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        return urllib.request.urlopen(request, timeout=10)

    def _get_url(self) -> str:
        if self._domain_name is None:
            raise RuntimeError("No blocked test domain was configured.")

        domain_name = self._domain_name.strip()
        if domain_name.startswith("http://") or domain_name.startswith("https://"):
            return domain_name

        return f"https://{domain_name}"

    def _is_domain_unconfigured(self) -> bool:
        return self._domain_name is None or not self._domain_name.strip()

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T07:
    id = "T07"
    title = "Connect to raw IP address"

    _URL = "http://1.1.1.1"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the raw IP address.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to raw IP address failed.",
                evidence=combined_output[:500],
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
                summary="Shell connection to raw IP address timed out.",
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
            response = await asyncio.to_thread(self._open_url)
            with response:
                evidence = f"url={response.url}, status={response.status}"

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the raw IP address.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the raw IP address.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to raw IP address failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to raw IP address timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "-I",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        request = urllib.request.Request(
            self._URL,
            headers={"User-Agent": "SandboxTester/1.0"},
        )
        opener = urllib.request.build_opener(_NoRedirectHandler)
        return opener.open(request, timeout=10)

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T08:
    id = "T08"
    title = "Connect to non-HTTP port"

    _HOST = "github.com"
    _PORT = 22

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the non-HTTP TCP port.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to non-HTTP TCP port failed.",
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
                summary="Shell connection to non-HTTP TCP port timed out.",
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
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the non-HTTP TCP port.",
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
                summary="Python runtime connection to non-HTTP TCP port timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to non-HTTP TCP port failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        return _run_shell_tcp_connect_command(
            self._HOST,
            self._PORT,
            timeout_seconds=10,
        )

    def _connect_to_endpoint(self) -> tuple[str, int]:
        with socket.create_connection(
            (self._HOST, self._PORT), timeout=10
        ) as socket_connection:
            peer_name = socket_connection.getpeername()

        if not isinstance(peer_name, tuple) or len(peer_name) < 2:
            raise RuntimeError(f"Unexpected peer name: {peer_name!r}")

        return (str(peer_name[0]), int(peer_name[1]))


class G09_T09:
    id = "T09"
    title = "Send HTTP POST"

    _URL = "https://httpbin.org/post"
    _PAYLOAD = {
        "source": "sandbox-tester",
        "purpose": "network-post-test",
    }

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell sent an HTTP POST request.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell HTTP POST request failed.",
                evidence=combined_output[:500],
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
                summary="Shell HTTP POST request timed out.",
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
            response = await asyncio.to_thread(self._open_url)
            with response:
                response_body = response.read(500).decode("utf-8", errors="replace")
                evidence = (
                    f"url={response.url}, status={response.status}, {response_body}"
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime sent an HTTP POST request.",
                evidence=evidence[:500],
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime reached the HTTP POST endpoint.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP POST request failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime HTTP POST request timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        payload = json.dumps(self._PAYLOAD)
        command = [
            "curl",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            "--request",
            "POST",
            "--header",
            "Content-Type: application/json",
            "--data",
            payload,
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _open_url(self) -> Any:
        payload = json.dumps(self._PAYLOAD).encode("utf-8")
        request = urllib.request.Request(
            self._URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SandboxTester/1.0",
            },
            method="POST",
        )
        return urllib.request.urlopen(request, timeout=10)

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T10:
    id = "T10"
    title = "Download small file"

    _URL = "https://httpbin.org/bytes/128"
    _EXPECTED_SIZE_BYTES = 128

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._shell_file = capability_context.allowed_directory / "g09_t10_shell.bin"
        self._tool_file = capability_context.allowed_directory / "g09_t10_tool.bin"

    async def run_shell(self) -> InvocationResult:
        self._delete_file_if_exists(self._shell_file)

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if self._was_downloaded(self._shell_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell downloaded a small file.",
                    evidence=(
                        f"path={self._shell_file}, "
                        f"size={self._shell_file.stat().st_size}"
                    ),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell command succeeded, but file was not downloaded.",
                    evidence=combined_output[:500],
                )

            if self._is_curl_missing(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The curl command is not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell file download failed.",
                evidence=combined_output[:500],
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
                summary="Shell file download timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        self._delete_file_if_exists(self._tool_file)

        try:
            await asyncio.to_thread(self._download_tool_file)

            if self._was_downloaded(self._tool_file):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime downloaded a small file.",
                    evidence=(
                        f"path={self._tool_file}, size={self._tool_file.stat().st_size}"
                    ),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation completed, but file was not downloaded.",
            )
        except urllib.error.HTTPError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file download failed with HTTP error.",
                evidence=f"status={error.code}, reason={error.reason}"[:500],
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file download failed.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime file download timed out.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            "curl",
            "--max-time",
            "10",
            "--silent",
            "--show-error",
            "--output",
            str(self._shell_file),
            self._URL,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _download_tool_file(self) -> None:
        request = urllib.request.Request(
            self._URL,
            headers={"User-Agent": "SandboxTester/1.0"},
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            content = response.read()

        self._tool_file.write_bytes(content)

    def _delete_file_if_exists(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def _was_downloaded(self, path: Path) -> bool:
        return path.is_file() and path.stat().st_size == self._EXPECTED_SIZE_BYTES

    def _is_curl_missing(self, output: str) -> bool:
        missing_markers = (
            "not recognized",
            "not found",
            "No such file or directory",
        )
        return any(marker in output for marker in missing_markers)


class G09_T11:
    id = "T11"
    title = "Start local listening socket"

    _HOST = "127.0.0.1"

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_shell_listener()
            port = await asyncio.to_thread(self._read_listener_port, child_process)
            completed = await asyncio.to_thread(
                _run_shell_tcp_connect_command,
                self._HOST,
                port,
                5,
            )
            child_process.wait(timeout=5)

            if child_process.returncode == 0 and completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell started a local listening socket.",
                    evidence=f"host={self._HOST}, port={port}",
                )

            stderr = self._read_child_stderr(child_process)
            combined_output = f"{completed.stdout}\n{completed.stderr}\n{stderr}"
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell listener process exited with an unexpected status.",
                evidence=combined_output.strip()[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to local listening socket timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell local listening socket test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        listener: socket.socket | None = None
        client: socket.socket | None = None
        accepted_connection: socket.socket | None = None

        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self._HOST, 0))
            listener.listen(1)
            listener.settimeout(5)
            port = listener.getsockname()[1]

            client = socket.create_connection((self._HOST, port), timeout=5)
            accepted_connection, _address = listener.accept()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime started a local listening socket.",
                evidence=f"host={self._HOST}, port={port}",
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
                summary="Python runtime local socket connection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local listening socket test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if accepted_connection is not None:
                accepted_connection.close()
            if client is not None:
                client.close()
            if listener is not None:
                listener.close()

    def _start_shell_listener(self) -> subprocess.Popen[str]:
        command = _build_shell_tcp_listener_command(self._HOST)

        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _read_listener_port(self, child_process: subprocess.Popen[str]) -> int:
        if child_process.stdout is None:
            raise RuntimeError("Listener process stdout was not captured.")

        line = child_process.stdout.readline().strip()
        if not line:
            stderr = self._read_child_stderr(child_process)
            raise RuntimeError(f"Listener process did not report a port: {stderr}")

        return int(line)

    def _read_child_stderr(self, child_process: subprocess.Popen[str]) -> str:
        if child_process.stderr is None:
            return ""

        return child_process.stderr.read()

    def _cleanup_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.terminate()

        try:
            child_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child_process.kill()
            child_process.wait(timeout=5)


class G09_T12:
    id = "T12"
    title = "Connect to local loopback service"

    _HOST = "127.0.0.1"

    async def run_shell(self) -> InvocationResult:
        service_process: subprocess.Popen[str] | None = None

        try:
            service_process = self._start_loopback_service()
            port = await asyncio.to_thread(self._read_service_port, service_process)
            completed = await asyncio.to_thread(self._run_shell_command, port)
            service_process.wait(timeout=5)

            if completed.returncode == 0 and service_process.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to a local loopback service.",
                    evidence=completed.stdout.strip()[:500],
                )

            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to local loopback service failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to local loopback service timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell local loopback service test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if service_process is not None:
                self._cleanup_service_process(service_process)

    async def run_tool(self) -> InvocationResult:
        listener: socket.socket | None = None
        accepted_connection: socket.socket | None = None
        server_errors: list[BaseException] = []

        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self._HOST, 0))
            listener.listen(1)
            listener.settimeout(5)
            port = listener.getsockname()[1]

            def accept_connection() -> None:
                nonlocal accepted_connection

                try:
                    accepted_connection, _address = listener.accept()
                except BaseException as error:
                    server_errors.append(error)

            server_thread = threading.Thread(target=accept_connection)
            server_thread.start()

            with socket.create_connection((self._HOST, port), timeout=5) as client:
                peer_name = client.getpeername()

            server_thread.join(timeout=5)
            if server_thread.is_alive():
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Loopback service did not accept the connection in time.",
                    evidence=f"host={self._HOST}, port={port}",
                )

            if server_errors:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Loopback service raised an exception.",
                    evidence=repr(server_errors[0]),
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to a local loopback service.",
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
                summary="Python runtime local loopback connection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local loopback service test failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if accepted_connection is not None:
                accepted_connection.close()
            if listener is not None:
                listener.close()

    def _start_loopback_service(self) -> subprocess.Popen[str]:
        command = _build_shell_tcp_listener_command(self._HOST)

        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _read_service_port(self, service_process: subprocess.Popen[str]) -> int:
        if service_process.stdout is None:
            raise RuntimeError("Loopback service stdout was not captured.")

        line = service_process.stdout.readline().strip()
        if not line:
            stderr = self._read_service_stderr(service_process)
            raise RuntimeError(f"Loopback service did not report a port: {stderr}")

        return int(line)

    def _run_shell_command(self, port: int) -> subprocess.CompletedProcess[str]:
        return _run_shell_tcp_connect_command(
            self._HOST,
            port,
            timeout_seconds=5,
        )

    def _read_service_stderr(self, service_process: subprocess.Popen[str]) -> str:
        if service_process.stderr is None:
            return ""

        return service_process.stderr.read()

    def _cleanup_service_process(self, service_process: subprocess.Popen[str]) -> None:
        if service_process.poll() is not None:
            return

        service_process.terminate()

        try:
            service_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            service_process.kill()
            service_process.wait(timeout=5)


class G09_T13:
    id = "T13"
    title = "Connect to allowed localnet address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.allowed_localnet_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed localnet address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the allowed localnet address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to allowed localnet address failed.",
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
                summary="Shell connection to allowed localnet address timed out.",
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
                summary="No allowed localnet address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the allowed localnet address.",
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
                    "Python runtime connection to allowed localnet address timed out."
                ),
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to allowed localnet address failed.",
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
            raise RuntimeError("No allowed localnet address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Allowed localnet address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


class G09_T14:
    id = "T14"
    title = "Connect to denied localnet address"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._address = capability_context.denied_localnet_address

    async def run_shell(self) -> InvocationResult:
        if self._is_endpoint_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No denied localnet address was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to the denied localnet address.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to denied localnet address failed.",
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
                summary="Shell connection to denied localnet address timed out.",
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
                summary="No denied localnet address was configured.",
            )

        try:
            peer_name = await asyncio.to_thread(self._connect_to_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to the denied localnet address.",
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
                    "Python runtime connection to denied localnet address timed out."
                ),
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime connection to denied localnet address failed.",
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
            raise RuntimeError("No denied localnet address was configured.")

        raw_address = self._address.strip()
        parsed_address = urllib.parse.urlparse(f"//{raw_address}")

        if parsed_address.hostname is None or parsed_address.port is None:
            raise RuntimeError("Denied localnet address must use host:port format.")

        return (parsed_address.hostname, parsed_address.port)


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


def _build_shell_tcp_listener_command(host: str) -> list[str]:
    if sys.platform == "win32":
        return _build_windows_tcp_listener_command(host)

    return _build_linux_tcp_listener_command(host)


def _build_windows_tcp_listener_command(host: str) -> list[str]:
    script = (
        "$address = [System.Net.IPAddress]::Parse("
        f"{_quote_powershell_string(host)}); "
        "$listener = [System.Net.Sockets.TcpListener]::new($address, 0); "
        "$listener.Start(); "
        "$port = $listener.LocalEndpoint.Port; "
        "Write-Output $port; "
        "[Console]::Out.Flush(); "
        "$client = $listener.AcceptTcpClient(); "
        "$client.Close(); "
        "$listener.Stop()"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_tcp_listener_command(host: str) -> list[str]:
    port = 30000 + (os.getpid() % 20000)
    script = (
        "if command -v nc >/dev/null 2>&1; then "
        f"echo {port}; "
        f"exec nc -l {_quote_shell_string(host)} {port} >/dev/null; "
        "fi; "
        "echo 'netcat not found' >&2; "
        "exit 127"
    )
    return ["sh", "-c", script]


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G09",
        title="Network access",
        tests=[
            G09_T01(),
            G09_T02(),
            G09_T03(),
            G09_T05(capability_context),
            G09_T06(capability_context),
            G09_T07(),
            G09_T08(),
            G09_T09(),
            G09_T10(capability_context),
            G09_T11(),
            G09_T12(),
            G09_T13(capability_context),
            G09_T14(capability_context),
            G25_T01(capability_context),
            G25_T02(capability_context),
            G25_T03(capability_context),
            G25_T04(capability_context),
            G25_T05(capability_context),
            G25_T06(capability_context),
            G25_T07(capability_context),
            G25_T08(capability_context),
            G25_T09(capability_context),
            G25_T10(capability_context),
            G26_T01(capability_context),
            G26_T02(capability_context),
            G26_T03(capability_context),
            G26_T04(capability_context),
        ],
    )
