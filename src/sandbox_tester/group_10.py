"""Group 10: Local service and metadata access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G10",
        title="Local service and metadata access",
        tests=[],
    )
