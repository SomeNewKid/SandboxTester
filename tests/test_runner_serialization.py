"""Tests for Sandbox Tester report serialization."""

from typing import Any, cast

from sandbox_tester.models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    CapabilityGroupResult,
    CapabilityResult,
    InvocationResult,
    Outcome,
)
from sandbox_tester.runner import _results_to_json_data


def test_results_to_json_data_removes_evidence_by_default() -> None:
    """Serialized report data should omit captured evidence by default."""
    data = _results_to_json_data([_build_group_result()])

    capability = _first_capability(data)

    assert capability["shell"]["evidence"] == "[REMOVED]"
    assert capability["tool"]["evidence"] == "[REMOVED]"
    assert capability["alternates"]["attempts"][0]["evidence"] == "[REMOVED]"


def test_results_to_json_data_can_serialize_evidence() -> None:
    """Serialized report data should include evidence when explicitly requested."""
    data = _results_to_json_data(
        [_build_group_result()],
        serialize_evidence=True,
    )

    capability = _first_capability(data)

    assert capability["shell"]["evidence"] == "shell evidence"
    assert capability["tool"]["evidence"] == "tool evidence"
    assert capability["alternates"]["attempts"][0]["evidence"] == "alternate evidence"


def _build_group_result() -> CapabilityGroupResult:
    return CapabilityGroupResult(
        id="G01",
        title="Group",
        capabilities=[
            CapabilityResult(
                id="T01",
                title="Capability",
                shell=InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell summary",
                    evidence="shell evidence",
                ),
                tool=InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Tool summary",
                    evidence="tool evidence",
                ),
                alternates=AlternateInvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Alternate summary",
                    attempts=[
                        AlternateAttemptResult(
                            id="A01",
                            title="Alternate",
                            outcome=Outcome.ALLOWED,
                            bypass_class="alternate",
                            command_family="shell",
                            evidence="alternate evidence",
                        )
                    ],
                ),
            )
        ],
    )


def _first_capability(data: list[dict[str, object]]) -> dict[str, Any]:
    capabilities = cast(list[dict[str, Any]], data[0]["capabilities"])
    return capabilities[0]
