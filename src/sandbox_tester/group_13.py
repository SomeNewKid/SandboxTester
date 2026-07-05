"""Group 13: Browser and web session access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G13",
        title="Browser and web session access",
        tests=[],
    )
