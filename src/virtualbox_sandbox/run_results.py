"""Persist VirtualBox sandbox run results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .models import GuestScriptResult, VmCloneResult

_STDOUT_FILE_NAME = "stdout.txt"
_STDERR_FILE_NAME = "stderr.txt"
_RESULT_FILE_NAME = "result.json"
_METADATA_FILE_NAME = "run-metadata.json"


def save_run_results(
    run_directory: Path,
    clone_result: VmCloneResult,
    script_result: GuestScriptResult,
) -> None:
    """Save guest script output and metadata to the local run directory."""
    run_directory.mkdir(parents=True, exist_ok=True)
    _write_text(run_directory / _STDOUT_FILE_NAME, script_result.stdout)
    _write_text(run_directory / _STDERR_FILE_NAME, script_result.stderr)
    _write_artifacts(run_directory, script_result.artifacts)
    _write_json(run_directory / _RESULT_FILE_NAME, _create_result_data(script_result))
    _write_json(
        run_directory / _METADATA_FILE_NAME,
        _create_metadata_data(clone_result),
    )


def _create_result_data(script_result: GuestScriptResult) -> dict[str, object]:
    return {
        "script_path": script_result.script_path,
        "source_path": script_result.source_path,
        "command": script_result.command,
        "exit_code": script_result.exit_code,
        "stdout_path": _STDOUT_FILE_NAME,
        "stderr_path": _STDERR_FILE_NAME,
        "artifact_paths": sorted(script_result.artifacts),
    }


def _create_metadata_data(clone_result: VmCloneResult) -> dict[str, object]:
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "base_vm_name": clone_result.base_vm_name,
        "run_vm_name": clone_result.run_vm_name,
        "ssh_host": clone_result.ssh_host,
        "ssh_port": clone_result.ssh_port,
    }


def _write_text(path: Path, text: str) -> None:
    path.write_text(f"{text}\n", encoding="utf-8")


def _write_artifacts(run_directory: Path, artifacts: dict[str, str | bytes]) -> None:
    for file_name, content in artifacts.items():
        path = run_directory / file_name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            _write_text(path, content)


def _write_json(path: Path, data: dict[str, object]) -> None:
    text = json.dumps(data, indent=2)
    path.write_text(f"{text}\n", encoding="utf-8")
