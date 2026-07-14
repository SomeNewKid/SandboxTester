"""Tests for network capability probes."""

import asyncio
import subprocess
import urllib.error
from email.message import Message

from sandbox_tester.group_09 import G09_T07
from sandbox_tester.models import Outcome


def test_raw_ip_shell_denies_unsuccessful_http_status() -> None:
    """Verify raw IP shell probes deny proxy-generated HTTP failures."""
    capability = G09_T07()

    capability._run_shell_command = lambda: subprocess.CompletedProcess(
        args=["curl"],
        returncode=0,
        stdout="HTTP/1.1 403 Forbidden\nServer: squid/6.13\n",
        stderr="",
    )

    result = asyncio.run(capability.run_shell())

    assert result.outcome == Outcome.DENIED


def test_raw_ip_tool_denies_unsuccessful_http_status() -> None:
    """Verify raw IP Python probes deny proxy-generated HTTP failures."""
    capability = G09_T07()

    def raise_http_error() -> None:
        raise urllib.error.HTTPError(
            url="http://1.1.1.1",
            code=403,
            msg="Forbidden",
            hdrs=Message(),
            fp=None,
        )

    capability._open_url = raise_http_error

    result = asyncio.run(capability.run_tool())

    assert result.outcome == Outcome.DENIED
