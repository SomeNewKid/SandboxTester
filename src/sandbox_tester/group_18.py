"""Group 18: Identity, authentication, and credential stores."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G18",
        title="Identity, authentication, and credential stores",
        tests=[],
    )
