"""Group 19: System configuration and administration."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G19",
        title="System configuration and administration",
        tests=[],
    )
