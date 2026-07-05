"""Group 06: Program and executable invocation."""

from .testing import CapabilityContext, CapabilityGroup


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G06",
        title="Program and executable invocation",
        tests=[],
    )
