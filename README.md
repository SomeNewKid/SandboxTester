# Sandbox Tester

Sandbox Tester is a Python command-line workbench for testing what an AI agent
runtime can do inside its current execution environment. It probes filesystem,
process, network, tool, identity, desktop, browser, cloud, credential, hardware,
scheduling, and logging capabilities, then writes structured output showing
whether each capability was allowed, denied, not applicable, or errored.

> [!WARNING]
> This is an experimental project and should not be considered production-ready.

The project was created to make sandbox boundaries visible. Run it once on an
unrestricted local machine, run it again inside a hardened sandbox, container,
VM, microVM, or cloud agent environment, and compare the reports to confirm or
dispute what the sandbox actually permits.

## What It Does

The CLI prepares controlled test fixtures, builds a capability context for the
current deployment, runs every capability group, writes run artifacts, saves a
JSON report, and optionally prints a Markdown report.

Each capability is tested through three invocation paths:

- shell invocation, where the capability is attempted through a local command
- tool invocation, where the capability is attempted through Python/tool code
- alternate shell invocation, where related shell approaches probe for bypasses
  around simple policy guards

The result for each invocation path is classified as:

- `Allowed`: the action succeeded
- `Denied`: the action appears to have been blocked
- `N/A`: the action was not configured or not meaningful in this deployment
- `Error`: the probe failed in a way that prevents a confident conclusion

The capability groups cover:

- runtime identity and execution context
- filesystem read, write, modification, and persistence behavior
- environment variable and secret exposure
- program execution and process control
- resource limits
- network, local service, and metadata access
- inter-process communication
- desktop UI and browser session access
- package, source control, database, cloud, and credential access
- system administration, hardware, scheduling, and logging capabilities

The current implementation registers groups G01 through G22.

## Requirements

- Python 3.11.
- PowerShell on Windows.
- Any deployment-specific test resources configured in `src/test_runner/cli.py`,
  such as a mounted/shared directory.

## Setup

Create the virtual environment and install the project with development
dependencies:

```powershell
.\scripts\setup-dev.ps1
```

The setup script expects Python 3.11 at the path configured in
`scripts\setup-dev.ps1`.

## Running

Run the sandbox tester from the repository root:

```powershell
.\.venv\Scripts\python.exe -m test_runner
```

The command creates a timestamped run directory under `.runs`, writes live and
final output files, copies the JSON report to `.reports`, and prints a Markdown
summary when enabled in `src/test_runner/cli.py`.

The file protocol for each run is:

```text
.runs/run-YYYY-mm-dd-HH-MM-SS/
  input/
    capability-context.json
  output/
    status.ndjson
    report.json
    done.json
```

The Markdown output looks like:

```text
# Sandbox Report

## G02. Basic filesystem read access

| Shell | Tool | Alternate Shell | ID | Title |
| --- | --- | --- | --- | --- |
| Allowed | Allowed | N/A | T01 | Read a known allowed test file |
| Allowed | Allowed | N/A | T02 | List current directory |
```

The test runner creates allowed and denied fixture directories before the run.
Depending on the configuration in `src/test_runner/cli.py`, scratch directories
and run artifacts can either be deleted after the run or retained for inspection.

## Architecture

The project is split into two packages:

- `sandbox_tester`: the sandbox-side test engine. It owns the capability
  context model, result models, reporters, capability group registration,
  individual probes, file-based runner, and Markdown rendering.
- `test_runner`: the host-side orchestration harness. It prepares directories,
  builds and serializes the capability context, invokes the tester, copies the
  final report, and handles cleanup.

The current runner still invokes `sandbox_tester` locally as the current user.
The file-based boundary between `test_runner` and `sandbox_tester` is intended
to support future launchers where a privileged orchestrator prepares fixtures
and a lower-privilege sandbox identity runs the tester.

## Configuration

Runtime configuration is currently centralized in `src/test_runner/cli.py`.
This includes:

- verbose versus quiet progress reporting
- whether scratch directories and run artifacts are deleted after a run
- the mounted/shared directory used by mounted-storage probes
- allowed and denied targets for network, local service, database, browser,
  source control, hardware, and credential-related probes

The sandbox engine receives this deployment-specific information through
`CapabilityContext`, so capability tests do not need to discover global paths on
their own.

## Development Checks

Run formatting, linting, type checking, and tests:

```powershell
.\scripts\check.ps1
```

This runs:

- `ruff format .`
- `ruff check .`
- `pyright`
- `pytest`

## Project Structure

```text
src/sandbox_tester/
  models.py       Shared result dataclasses and outcome enum
  testing.py      Capability context, fixture setup, protocols, and group runner
  runner.py       File-based entry point for serialized test runs
  reporter.py     Console, quiet, status-file, and composite reporters
  manager.py      Ordered capability group registration and execution
  utilities.py    Markdown report rendering
  group_01.py     Runtime identity and execution context tests
  ...
  group_22.py     Logging, telemetry, and audit visibility tests

src/test_runner/
  __main__.py     Package entry point for python -m test_runner
  cli.py          Deployment configuration and command-line entry point

tests/
  test_smoke.py

scripts/
  setup-dev.ps1
  check.ps1
```

## Notes

This project is a sandbox evaluation tool, not a security proof. A result of
`Denied` means the specific probe did not succeed in the current deployment; it
does not prove that no alternate route exists. A result of `Allowed` means the
tested invocation path succeeded and should be reviewed in the context of the
deployment's intended security boundary.

Some probes are intentionally configuration-driven. For example, mounted/shared
storage tests should use an explicit configured path rather than guessing from
platform-specific mount locations.

Agent-mediated checks may make OpenAI API calls and may incur usage costs.
Deterministic shell and tool probes should remain the primary source of the
capability report, with model-driven checks used where agent behavior itself is
being evaluated.

## Third-Party Notices

This project has a direct runtime dependency on the `openai-agents` Python
package (MIT). See the package's PyPI license metadata for full license and
notice terms.

## License

GNU General Public License v3.0. See the `LICENSE` file for details.
