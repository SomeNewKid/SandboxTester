"""Group 03: Filesystem write and modification access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G03",
        title="Filesystem write and modification access",
        tests=[],
    )
