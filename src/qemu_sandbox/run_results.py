"""Persist QEMU sandbox run results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from virtualbox_sandbox.models import GuestScriptResult

from .models import QemuRunResult

_STDOUT_FILE_NAME = "stdout.txt"
_STDERR_FILE_NAME = "stderr.txt"
_METADATA_FILE_NAME = "run-metadata.json"


def save_run_results(
    run_directory: Path,
    run_result: QemuRunResult,
    script_result: GuestScriptResult,
) -> None:
    """Save guest script output and metadata to the local run directory."""
    run_directory.mkdir(parents=True, exist_ok=True)
    _write_text(run_directory / _STDOUT_FILE_NAME, script_result.stdout)
    _write_text(run_directory / _STDERR_FILE_NAME, script_result.stderr)
    _write_artifacts(run_directory, script_result.artifacts)
    _write_json(
        run_directory / _METADATA_FILE_NAME,
        _create_metadata_data(run_result),
    )


def _create_metadata_data(run_result: QemuRunResult) -> dict[str, object]:
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "base_image_path": str(run_result.base_image_path),
        "qemu_path": str(run_result.qemu_path),
        "run_disk_path": str(run_result.run_disk_path),
        "ssh_host": run_result.ssh_host,
        "ssh_port": run_result.ssh_port,
        "command": run_result.command,
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
