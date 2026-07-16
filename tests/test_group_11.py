"""Tests for inter-process communication capability probes."""

from sandbox_tester.group_11 import _build_shared_memory_reader_python_code


def test_shared_memory_reader_does_not_unregister_parent_owned_segment() -> None:
    """Verify child readers avoid noisy resource-tracker unregister calls."""
    code = _build_shared_memory_reader_python_code("psm_test", 4)

    assert "resource_tracker.unregister" not in code
    assert "original_register = resource_tracker.register" in code
    assert "resource_type == 'shared_memory'" in code
