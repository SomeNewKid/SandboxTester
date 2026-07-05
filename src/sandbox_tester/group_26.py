"""Group 26: Policy and approval enforcement."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G26",
        title="Policy and approval enforcement",
        tests=[],
    )
