"""Tests for system configuration capability probes."""

import subprocess

from sandbox_tester.group_19 import (
    _build_installed_software_alternate_attempts,
    _run_system_alternate_attempts,
)
from sandbox_tester.models import Outcome
from sandbox_tester.testing import OperatingSystem


def test_installed_software_alternate_reports_missing_apt_as_not_applicable(
    monkeypatch,
) -> None:
    """Verify missing apt is not reported as installed software access."""
    attempts = _build_installed_software_alternate_attempts(OperatingSystem.LINUX)

    def run_missing_apt(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=127,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr("sandbox_tester.group_19.subprocess.run", run_missing_apt)

    result = _run_system_alternate_attempts(attempts)

    assert result.outcome == Outcome.NOT_APPLICABLE
    assert result.attempts[0].outcome == Outcome.NOT_APPLICABLE
