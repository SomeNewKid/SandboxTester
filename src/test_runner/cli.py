"""Command-line interface for the application."""

from __future__ import annotations

import asyncio
from pathlib import Path

from sandbox_tester.manager import run_all_groups
from sandbox_tester.reporter import ConsoleReporter, QuietReporter
from sandbox_tester.testing import (
    CapabilityContext,
    create_scratch_directory,
    delete_scratch_directory,
)
from sandbox_tester.utilities import render_markdown_report

VERBOSE_LOGGING = False
DELETE_SCRATCH_DIRECTORY = False
MOUNTED_SHARED_DIRECTORY = Path("S:/")


def main() -> int:
    """Run the command-line interface."""
    scratch_directory = create_scratch_directory()
    capability_context = CapabilityContext.from_current_environment(
        working_directory=Path.cwd(),
        scratch_directory=scratch_directory,
        mounted_shared_directory=MOUNTED_SHARED_DIRECTORY,
    )

    reporter = ConsoleReporter() if VERBOSE_LOGGING else QuietReporter()
    results = asyncio.run(run_all_groups(capability_context, reporter))
    if results:
        markdown = render_markdown_report(results)
        print()
        print("-" * 40)
        print()
        print(markdown)
    else:
        print("No results.")

    if DELETE_SCRATCH_DIRECTORY:
        delete_scratch_directory(scratch_directory)
    else:
        print(f"Scratch directory retained at: {scratch_directory}")
    return 0
