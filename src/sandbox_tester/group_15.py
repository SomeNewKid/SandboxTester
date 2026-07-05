"""Group 15: Source control access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G15",
        title="Source control access",
        tests=[],
    )
