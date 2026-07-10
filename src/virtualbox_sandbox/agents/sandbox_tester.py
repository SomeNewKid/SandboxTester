"""Sandbox Tester agent profile."""

from pathlib import Path

from virtualbox_sandbox.models import PythonAgentProfile

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_SANDBOX_TESTER_SOURCE_DIRECTORY = _REPOSITORY_ROOT / "src" / "sandbox_tester"
_ENTRY_SCRIPT = """
import json
import sandbox_tester

message = {
    "message": "sandbox_tester imported",
    "module_file": sandbox_tester.__file__,
}
print(json.dumps(message))
"""


def get_profile() -> PythonAgentProfile:
    """Return the Sandbox Tester Python agent profile."""
    return PythonAgentProfile(
        name="sandbox_tester",
        source_directory=_SANDBOX_TESTER_SOURCE_DIRECTORY,
        package_directory_name="sandbox_tester",
        dependencies=[
            "paramiko",
            "pillow",
            "pymysql",
        ],
        entry_script=_ENTRY_SCRIPT,
        exclude_patterns=[
            "__pycache__",
            "*.pyc",
        ],
    )
