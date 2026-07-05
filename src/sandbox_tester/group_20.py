"""Group 20: Hardware and device access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G20",
        title="Hardware and device access",
        tests=[],
    )
