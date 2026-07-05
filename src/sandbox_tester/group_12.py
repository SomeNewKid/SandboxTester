"""Group 12: User interface and desktop automation."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G12",
        title="User interface and desktop automation",
        tests=[],
    )
