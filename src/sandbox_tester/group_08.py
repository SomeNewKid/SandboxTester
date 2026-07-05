"""Group 08: Resource limits."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G08",
        title="Resource limits",
        tests=[],
    )
