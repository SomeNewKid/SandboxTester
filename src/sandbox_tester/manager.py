"""Acts as the facade to the sandbox tester."""

from collections.abc import Callable

from .group_01 import get_group as get_group_01
from .group_04 import get_group as get_group_04
from .group_05 import get_group as get_group_05
from .group_07 import get_group as get_group_07
from .group_08 import get_group as get_group_08
from .group_17 import get_group as get_group_17
from .reporter import TestReporter
from .testing import (
    CapabilityContext,
    CapabilityGroup,
    CapabilityGroupResult,
    run_group,
)

GROUP_FACTORIES: list[Callable[[CapabilityContext], CapabilityGroup]] = [
    get_group_01,
    # get_group_02,
    # get_group_03,
    get_group_04,
    get_group_05,
    # get_group_06,
    get_group_07,
    get_group_08,
    # get_group_09,
    # get_group_10,
    # get_group_11,
    # get_group_12,
    # get_group_13,
    # get_group_14,
    # get_group_15,
    # get_group_16,
    get_group_17,
    # get_group_18,
    # get_group_19,
    # get_group_20,
    # get_group_21,
    # get_group_22,
]


async def run_all_groups(
    capability_context: CapabilityContext,
    reporter: TestReporter,
) -> list[CapabilityGroupResult]:
    all_group_results: list[CapabilityGroupResult] = []

    for group_factory in GROUP_FACTORIES:
        group = group_factory(capability_context)
        group_result = await run_group(group, reporter)
        all_group_results.append(group_result)

    return all_group_results
