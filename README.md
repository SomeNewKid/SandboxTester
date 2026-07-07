# Sandbox Tester

Sandbox Tester is a Python command-line workbench for testing what an AI agent
runtime can do inside its current execution environment. It probes filesystem,
process, network, tool, identity, desktop, browser, cloud, and policy
capabilities, then prints a Markdown report showing whether each capability was
allowed, denied, not applicable, or errored.

> [!WARNING]
> This is an experimental project and should not be considered production-ready.

The project was created to make sandbox boundaries visible. Run it once on an
unrestricted local machine, run it again inside a hardened sandbox, container,
VM, microVM, or cloud agent environment, and compare the reports to confirm or
dispute what the sandbox actually permits.

## What It Does

The CLI prepares a controlled allowed workspace, builds a capability context for
the current deployment, runs every capability group, and prints a report.

Each capability is tested through two invocation paths:

- shell invocation, where the capability is attempted through a local command
- tool invocation, where the capability is attempted through Python/tool code

The result for each path is classified as:

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
- system administration, hardware, scheduling, logging, model/tool, messaging,
  destructive action, and approval-policy capabilities

## Requirements

- Python 3.11.
- PowerShell on Windows.
- An `OPENAI_API_KEY` environment variable for agent-mediated OpenAI model
  checks.
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

The command prints a Markdown report such as:

```text
# Sandbox Report

## G02. Basic filesystem read access

| Shell | Tool | ID | Title |
| --- | --- | --- | --- |
| Allowed | Allowed | T01 | Read a known allowed test file |
| Allowed | Allowed | T02 | List current directory |
```

The test runner creates a allowed directory before the run. Depending on the
configuration in `src/test_runner/cli.py`, that directory can either be deleted
after the run or retained for inspection.

## Configuration

Runtime configuration is currently centralized in `src/test_runner/cli.py`.
This includes:

- verbose versus quiet progress reporting
- whether the allowed directory is deleted after a run
- the mounted/shared directory used by mounted-storage probes

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
  testing.py      Capability context, allowed directory setup, protocols, and group runner
  reporter.py     Console and quiet progress reporters
  manager.py      Ordered capability group registration and execution
  utilities.py    Markdown report rendering
  group_01.py     Runtime identity and execution context tests
  ...
  group_26.py     Policy and approval enforcement tests

src/test_runner/
  __main__.py     Package entry point for python -m test_runner
  cli.py          Deployment configuration and command-line entry point

tests/
  test_smoke.py

scripts/
  setup-dev.ps1
  check.ps1
```

`Proposed tests.md` contains the working catalogue of capability groups and test
IDs. The implemented group and test identifiers are intended to match that
catalogue.

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
