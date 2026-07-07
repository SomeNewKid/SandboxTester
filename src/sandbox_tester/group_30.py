"""Group 30: Reserved Group 30."""

from __future__ import annotations

from .testing import CapabilityContext, CapabilityGroup


def get_group(_capability_context: CapabilityContext) -> CapabilityGroup:
    """Get the capability group."""
    return CapabilityGroup(
        id="G30",
        title="Reserved Group 30",
        tests=[],
    )
