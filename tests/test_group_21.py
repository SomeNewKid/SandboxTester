"""Tests for scheduling and persistence capability probes."""

import asyncio
import subprocess

from sandbox_tester.group_21 import G21_T09, _g28_systemd_user_unit_probe_outcome
from sandbox_tester.models import Outcome
from sandbox_tester.testing import CapabilityContext, OperatingSystem


def test_systemd_user_unit_shell_denies_readonly_unit_write(
    tmp_path,
    monkeypatch,
) -> None:
    """Verify a failed unit write is not reported as successful persistence."""
    context = CapabilityContext(
        working_directory=tmp_path,
        allowed_directory=tmp_path,
        denied_directory=tmp_path / "denied",
        runtime_user_directory=tmp_path,
        runtime_temp_directory=tmp_path,
        mounted_shared_directory=None,
        operating_system=OperatingSystem.LINUX,
    )
    capability = G21_T09(context)
    capability_output = (
        "unit=sandbox-tester-probe.service; installed=true\n\n"
        "sh: 11: cannot create "
        "/tmp/sandbox-home/.config/systemd/user/sandbox-tester-probe.service: "
        "Read-only file system\n"
        "sh: 20: systemctl: not found\n"
        "sh: 21: systemctl: not found"
    )

    capability_result = subprocess.CompletedProcess(
        args=["sh", "-c"],
        returncode=2,
        stdout="",
        stderr=capability_output,
    )
    monkeypatch.setattr(
        "sandbox_tester.group_21._g28_run_shell_systemd_user_unit_probe",
        lambda: capability_result,
    )

    result = asyncio.run(capability.run_shell())
    alternate_outcome = _g28_systemd_user_unit_probe_outcome(
        capability_result,
        capability_output,
    )

    assert result.outcome == Outcome.DENIED
    assert alternate_outcome == Outcome.DENIED
