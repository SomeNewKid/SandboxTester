"""Group 23: Model and tool access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G23",
        title="Model and tool access",
        tests=[],
    )
