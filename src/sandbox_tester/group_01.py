"""Group 01: Runtime identity and execution context."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G01",
        title="Runtime identity and execution context",
        tests=[],
    )
