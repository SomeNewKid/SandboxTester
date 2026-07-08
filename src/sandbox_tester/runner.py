"""Run the sandbox tester from serialized input files."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .manager import run_all_groups
from .models import CapabilityGroupResult
from .reporter import TestReporter
from .testing import read_capability_context


async def run_from_files(
    context_path: Path,
    output_directory: Path,
    reporter: TestReporter,
) -> list[CapabilityGroupResult]:
    """Run tests from a serialized capability context and write output files."""
    output_directory.mkdir(parents=True, exist_ok=True)
    context = read_capability_context(context_path)
    results = await run_all_groups(context, reporter)

    report_path = output_directory / "report.json"
    done_path = output_directory / "done.json"
    _write_json_atomically(report_path, _results_to_json_data(results))
    _write_json_atomically(
        done_path,
        {
            "outcome": "completed",
            "report_path": str(report_path),
        },
    )

    return results


def _results_to_json_data(
    results: list[CapabilityGroupResult],
) -> list[dict[str, object]]:
    return [dataclasses.asdict(result) for result in results]


def _write_json_atomically(path: Path, data: object) -> None:
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    json_text = json.dumps(data, indent=2, default=str)
    temporary_path.write_text(f"{json_text}\n", encoding="utf-8")
    temporary_path.replace(path)
