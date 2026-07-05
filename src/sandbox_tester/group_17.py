"""Group 17: Cloud and external account access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G17",
        title="Cloud and external account access",
        tests=[],
    )
