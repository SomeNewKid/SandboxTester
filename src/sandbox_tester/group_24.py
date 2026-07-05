"""Group 24: Human communication and external messaging."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G24",
        title="Human communication and external messaging",
        tests=[],
    )
