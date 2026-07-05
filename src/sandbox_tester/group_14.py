"""Group 14: Package, dependency, and supply-chain access."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G14",
        title="Package, dependency, and supply-chain access",
        tests=[],
    )
