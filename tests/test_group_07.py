"""Tests for process control capability probes."""

import asyncio

from sandbox_tester.group_07 import G07_T02
from sandbox_tester.models import Outcome
from sandbox_tester.testing import CapabilityContext, OperatingSystem


def test_child_process_listing_reports_denied_child_creation(
    tmp_path,
    monkeypatch,
) -> None:
    """Verify denied child-process creation does not abort the test run."""
    context = CapabilityContext(
        working_directory=tmp_path,
        allowed_directory=tmp_path,
        denied_directory=tmp_path / "denied",
        runtime_user_directory=tmp_path,
        runtime_temp_directory=tmp_path,
        mounted_shared_directory=None,
        operating_system=OperatingSystem.LINUX,
    )
    capability = G07_T02(context)

    def deny_child_process():
        raise PermissionError("Process spawning is denied by sandbox profile")

    monkeypatch.setattr(capability, "_start_child_process", deny_child_process)

    shell_result = asyncio.run(capability.run_shell())
    tool_result = asyncio.run(capability.run_tool())
    alternate_result = asyncio.run(capability.run_alternates())

    assert shell_result.outcome == Outcome.DENIED
    assert tool_result.outcome == Outcome.DENIED
    assert alternate_result.outcome == Outcome.DENIED
