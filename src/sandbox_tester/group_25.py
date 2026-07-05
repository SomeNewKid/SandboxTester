"""Group 25: Destructive and irreversible actions."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G25",
        title="Destructive and irreversible actions",
        tests=[],
    )
