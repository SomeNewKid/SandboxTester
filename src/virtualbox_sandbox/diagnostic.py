"""Print Python environment diagnostics as JSON."""

from __future__ import annotations

import json
import os
import platform
import site
import subprocess
import sys
import sysconfig
from typing import Any

_SENSITIVE_ENVIRONMENT_TERMS = (
    "api_key",
    "apikey",
    "credential",
    "password",
    "secret",
    "token",
)


def main() -> int:
    """Print diagnostic information about the current Python environment."""
    diagnostics = _create_diagnostics()
    diagnostics_json = json.dumps(diagnostics, indent=2, sort_keys=True)
    print(diagnostics_json)
    return 0


def _create_diagnostics() -> dict[str, Any]:
    return {
        "environment": _get_environment(),
        "executable": sys.executable,
        "implementation": platform.python_implementation(),
        "installed_packages": _get_installed_packages(),
        "path": sys.path,
        "platform": {
            "architecture": platform.architecture(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "release": platform.release(),
            "system": platform.system(),
            "version": platform.version(),
        },
        "prefix": {
            "base_prefix": sys.base_prefix,
            "base_exec_prefix": sys.base_exec_prefix,
            "exec_prefix": sys.exec_prefix,
            "prefix": sys.prefix,
        },
        "site": _get_site_data(),
        "sysconfig": sysconfig.get_config_vars(),
        "version": sys.version,
        "version_info": list(sys.version_info),
    }


def _get_environment() -> dict[str, str]:
    return {
        key: _redact_environment_value(key, value)
        for key, value in sorted(os.environ.items())
    }


def _redact_environment_value(key: str, value: str) -> str:
    lower_key = key.lower()

    if any(term in lower_key for term in _SENSITIVE_ENVIRONMENT_TERMS):
        return "<redacted>"

    return value


def _get_installed_packages() -> list[dict[str, Any]] | dict[str, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        capture_output=True,
        check=False,
        encoding="utf-8",
        timeout=30,
    )

    if result.returncode != 0:
        return {
            "error": result.stderr.strip(),
        }

    return json.loads(result.stdout)


def _get_site_data() -> dict[str, Any]:
    data: dict[str, Any] = {
        "user_base": site.getuserbase(),
        "user_site": site.getusersitepackages(),
    }

    if hasattr(site, "getsitepackages"):
        data["site_packages"] = site.getsitepackages()

    return data


if __name__ == "__main__":
    raise SystemExit(main())
