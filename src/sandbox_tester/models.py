"""Models for the Sandbox Tester."""

from dataclasses import dataclass
from enum import StrEnum


class Outcome(StrEnum):
    ALLOWED = "Allowed"
    DENIED = "Denied"
    ERROR = "Error"
    NOT_APPLICABLE = "N/A"


@dataclass(frozen=True)
class InvocationResult:
    outcome: Outcome
    summary: str
    evidence: str = ""


@dataclass(frozen=True)
class CapabilityResult:
    id: str
    title: str
    shell: InvocationResult
    tool: InvocationResult


@dataclass(frozen=True)
class CapabilityGroupResult:
    id: str
    title: str
    capabilities: list[CapabilityResult]
