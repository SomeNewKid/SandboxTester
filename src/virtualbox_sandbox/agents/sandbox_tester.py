"""Sandbox Tester agent profile."""

from pathlib import Path

from virtualbox_sandbox.models import PythonAgentProfile

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_SANDBOX_TESTER_SOURCE_DIRECTORY = _REPOSITORY_ROOT / "src" / "sandbox_tester"
_ENTRY_SCRIPT = """
import os

from sandbox_tester.cli import main

config_path = os.environ["SANDBOX_TESTER_CONFIG_PATH"]
arguments = ["--config", config_path]
if os.environ.get("SANDBOX_TESTER_VERBOSE") == "1":
    arguments.append("--verbose")
if os.environ.get("SANDBOX_TESTER_SERIALIZE_EVIDENCE") == "1":
    arguments.append("--serialize-evidence")
raise SystemExit(main(arguments))
"""


def get_profile() -> PythonAgentProfile:
    """Return the Sandbox Tester Python agent profile."""
    return PythonAgentProfile(
        name="sandbox_tester",
        source_directory=_SANDBOX_TESTER_SOURCE_DIRECTORY,
        package_directory_name="sandbox_tester",
        dependencies=[
            "openai",
            "paramiko",
            "pillow",
            "playwright",
            "pymysql",
        ],
        entry_script=_ENTRY_SCRIPT,
        exclude_patterns=[
            "__pycache__",
            "*.pyc",
        ],
        post_install_commands=[
            "{python} -m playwright install chromium",
        ],
        environment_variables={
            "OPENAI_API_KEY": "[local]",
        },
    )
