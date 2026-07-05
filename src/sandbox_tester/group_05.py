"""Group 05: Environment variables and secrets exposure."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G05",
        title="Environment variables and secrets exposure",
        tests=[],
    )
