"""Resolve Python agent profiles by name."""

from .agents.sandbox_tester import get_profile as _get_sandbox_tester_profile
from .models import PythonAgentProfile

SANDBOX_TESTER_AGENT = "sandbox_tester"
SUPPORTED_AGENT_NAMES = [
    SANDBOX_TESTER_AGENT,
]


def get_python_agent_profile(agent_name: str) -> PythonAgentProfile:
    """Return a Python agent profile by name."""
    if agent_name == SANDBOX_TESTER_AGENT:
        return _get_sandbox_tester_profile()

    raise ValueError(f"Unsupported Python agent: {agent_name}")
