"""Tests for Sandbox Tester package capability probes."""

import asyncio
import subprocess

from sandbox_tester.group_14 import G14_T02
from sandbox_tester.models import Outcome
from sandbox_tester.testing import CapabilityContext, OperatingSystem


def test_g14_t02_alternates_report_venv_setup_failure(
    tmp_path,
    monkeypatch,
) -> None:
    """Verify failed alternate venv setup is reported instead of fatal."""
    context = CapabilityContext(
        working_directory=tmp_path,
        allowed_directory=tmp_path,
        denied_directory=tmp_path / "denied",
        runtime_user_directory=tmp_path,
        runtime_temp_directory=tmp_path,
        mounted_shared_directory=None,
        operating_system=OperatingSystem.LINUX,
    )
    capability = G14_T02(context)

    def raise_called_process_error(environment_directory):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["python", "-m", "venv", str(environment_directory)],
            stderr="ensurepip is not available",
        )

    monkeypatch.setattr(
        "sandbox_tester.group_14._build_environment_install_alternate_attempts",
        raise_called_process_error,
    )

    result = asyncio.run(capability.run_alternates())

    assert result.outcome == Outcome.DENIED
    assert len(result.attempts) == 1
    assert result.attempts[0].outcome == Outcome.DENIED
    assert result.attempts[0].command_family == "python/venv"
    assert "ensurepip is not available" in result.attempts[0].evidence
