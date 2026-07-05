"""Group 07: Process control."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G07",
        title="Process control",
        tests=[],
    )
