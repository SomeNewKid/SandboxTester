"""Group 16: Database and structured data access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G16",
        title="Database and structured data access",
        tests=[],
    )
