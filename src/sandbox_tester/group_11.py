"""Group 11: Inter-process communication."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G11",
        title="Inter-process communication",
        tests=[],
    )
