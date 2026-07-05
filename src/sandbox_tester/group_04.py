"""Group 04: Filesystem persistence."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G04",
        title="Filesystem persistence",
        tests=[],
    )
