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

The project now has three related command-line paths:

- `sandbox_tester` is the test engine. It accepts a serialized
  `CapabilityContext`, runs capability groups, writes `status.ndjson`,
  `report.json`, and `done.json`, and redacts serialized evidence by default.
- `local_sandbox` is the local host harness. It prepares local allowed and
  denied fixture directories, builds a `CapabilityContext` for the current
  Windows user/session, invokes `sandbox_tester`, copies the JSON report to
  `.local_sandbox/runs`, and optionally prints a Markdown report.
- `virtualbox_sandbox` is the VirtualBox harness. It creates and finalizes an
  Ubuntu 24.04 base VM, clones disposable run VMs, connects over SSH through NAT
  port forwarding, uploads scripts or Python agent source, prepares guest
  fixtures, runs the selected guest code, downloads run artifacts, and destroys
  the clone by default.

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

The `sandbox_tester` capability groups cover:

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

The current implementation registers groups G01 through G22. Evidence is still
captured inside result objects while tests run, but serialized reports replace
`evidence` values with `"[REMOVED]"` unless `sandbox_tester` is run with
`--serialize-evidence`.

## Requirements

- Python 3.11.
- PowerShell on Windows.
- Oracle VirtualBox, when using `virtualbox_sandbox`.
- An Ubuntu Server ISO, when creating a new VirtualBox base VM. The
  `virtualbox_sandbox` CLI accepts `--iso`, checks `SANDBOX_TESTER_ISO`, and
  then checks the Downloads directory.
- Any deployment-specific test resources configured in `src/local_sandbox/cli.py`,
  such as a mounted/shared directory.

## Setup

Create the virtual environment and install the project with development
dependencies:

```powershell
.\scripts\setup-dev.ps1
```

The setup script expects Python 3.11 at the path configured in
`scripts\setup-dev.ps1`.

## Running Locally

Run the local sandbox harness from the repository root:

```powershell
.\.venv\Scripts\python.exe -m local_sandbox
```

Add `--serialize-evidence` when you intentionally want `report.json` to contain
captured evidence instead of `"[REMOVED]"`:

```powershell
.\.venv\Scripts\python.exe -m local_sandbox --serialize-evidence
```

The command creates a timestamped run directory under `.local_sandbox/runs`,
writes live and final output files into that directory, and prints a Markdown
summary when enabled in `src/local_sandbox/cli.py`.

The file protocol for each run is:

```text
.local_sandbox/runs/run-YYYY-mm-dd-HH-MM-SS/
  config.json
  report.json
  stderr.txt
  stdout.txt
  status.ndjson
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

The local sandbox creates allowed and denied fixture directories before the run.
Depending on the configuration in `src/local_sandbox/cli.py`, scratch directories
and run artifacts can either be deleted after the run or retained for inspection.

## Running In VirtualBox

The VirtualBox workflow has a base VM phase and a disposable clone phase.

Create the base VM if it does not exist:

```powershell
.\.venv\Scripts\python.exe -m virtualbox_sandbox --iso C:\Path\To\ubuntu.iso
```

If the base VM is created, Ubuntu installation starts and the command exits with
instructions to wait for installation to complete, then shut down the base VM.
After the base VM is installed and stopped, finalize it once:

```powershell
.\.venv\Scripts\python.exe -m virtualbox_sandbox --finalize-base
```

Finalization starts the base VM, connects over a temporary SSH NAT forward,
installs packages needed for Python agent execution, shuts the base VM down, and
removes the temporary port forward.

Run a local Python script in a disposable clone:

```powershell
.\.venv\Scripts\python.exe -m virtualbox_sandbox --script .\src\virtualbox_sandbox\diagnostic.py
```

Run the `sandbox_tester` agent in a disposable clone:

```powershell
.\.venv\Scripts\python.exe -m virtualbox_sandbox --agent sandbox_tester
```

To serialize captured evidence from the guest report:

```powershell
.\.venv\Scripts\python.exe -m virtualbox_sandbox --agent sandbox_tester --serialize-evidence
```

For each disposable run, `virtualbox_sandbox` creates a clone, starts it,
waits for SSH, prepares a guest run directory under `/tmp/sandbox-tester`,
uploads the script or agent, runs it, saves local artifacts under
`.virtualbox_sandbox/runs/run-...`, then stops and removes the clone. Use
`--keep-vm` to leave the clone running for inspection after setup or execution.

## Architecture

The project is split into three packages:

- `sandbox_tester`: the sandbox-side test engine. It owns the capability
  context model, result models, reporters, capability group registration,
  individual probes, file-based runner, evidence redaction, evidence-removing
  JSON serialization, and Markdown rendering.
- `local_sandbox`: the host-side orchestration harness. It prepares directories,
  builds and serializes the capability context, invokes the tester, copies the
  final report, and handles cleanup.
- `virtualbox_sandbox`: the VirtualBox orchestration harness. It manages the
  base VM lifecycle, disposable clone lifecycle, guest credentials, NAT SSH port
  forwarding, guest run layout creation, script and source upload, Python
  dependency installation, remote execution, artifact download, and VM teardown.

`local_sandbox` still invokes `sandbox_tester` locally as the current user.
`virtualbox_sandbox` exercises the same file-based boundary across an SSH
connection into a disposable Ubuntu VM clone, so the host prepares the guest
environment and the guest agent tests the capabilities available inside that VM.

## Configuration

Runtime configuration is currently centralized in `src/local_sandbox/cli.py`.
This includes:

- verbose versus quiet progress reporting
- whether scratch directories and run artifacts are deleted after a run
- the mounted/shared directory used by mounted-storage probes
- allowed and denied targets for network, local service, database, browser,
  source control, hardware, and credential-related probes

The sandbox engine receives this deployment-specific information through
`CapabilityContext`, so capability tests do not need to discover global paths on
their own.

For VirtualBox runs, VM configuration is exposed through
`src/virtualbox_sandbox/cli.py` flags such as `--vm-name`, `--iso`,
`--base-directory`, `--disk-size-mb`, `--memory-mb`, `--cpus`, `--guest-user`,
`--hostname`, `--keep-vm`, `--script`, `--source-directory`, `--agent`,
`--verbose`, `--serialize-evidence`, and `--finalize-base`.

The `sandbox_tester` VirtualBox agent profile lives in
`src/virtualbox_sandbox/agents/sandbox_tester.py`. The guest fixture and
`CapabilityContext` JSON layout are created by
`src/virtualbox_sandbox/guest_run_layout.py`.

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

src/local_sandbox/
  __main__.py     Package entry point for python -m local_sandbox
  cli.py          Deployment configuration and command-line entry point

src/virtualbox_sandbox/
  __main__.py                 Package entry point for python -m virtualbox_sandbox
  cli.py                      VirtualBox command-line orchestration
  virtual_machine_factory.py  Base VM, clone, SSH forward, and teardown operations
  virtual_machine_setup.py    SSH setup, guest preparation, execution, artifacts
  guest_script_runner.py      Script/source upload and remote Python execution
  guest_run_layout.py         Guest fixture directories and CapabilityContext JSON
  agent_profiles.py           Supported Python agent profile lookup
  agents/sandbox_tester.py    Sandbox Tester guest agent profile
  credentials.py              Local guest credential creation/loading
  run_results.py              Local run artifact persistence
  diagnostic.py               Diagnostic guest Python script

tests/
  test_smoke.py
  test_redaction.py
  test_runner_serialization.py

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
