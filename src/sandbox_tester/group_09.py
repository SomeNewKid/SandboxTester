"""Group 09: Network access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G09",
        title="Network access",
        tests=[],
    )
