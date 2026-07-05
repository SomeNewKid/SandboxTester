"""Group 21: Time, scheduling, and persistence mechanisms."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G21",
        title="Time, scheduling, and persistence mechanisms",
        tests=[],
    )
