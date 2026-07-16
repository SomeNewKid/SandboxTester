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

The project now has five related command-line paths:

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
- `qemu_sandbox` is the QEMU harness. It copies a prepared Ubuntu qcow2 base
  image to a disposable run disk, starts QEMU with user-mode SSH port
  forwarding, uploads and runs the selected Python agent, downloads Sandbox
  Tester artifacts, and stops the VM by default.
- `docker_sandbox` is the Docker harness. It creates a reusable Playwright
  Python base image if needed, starts a disposable Ubuntu-based Linux
  container, prepares container fixtures, runs `sandbox_tester`, saves run
  artifacts under `.docker_sandbox/runs`, and removes the container by default.

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
- local AI agent behavior

The current implementation registers groups G01 through G22, plus G30 for
local AI agent behavior. G30 currently probes whether Python tool code can
collect local environment details and receive a remote LLM summary through the
OpenAI Responses API. Evidence is still captured inside result objects while
tests run, but serialized reports replace `evidence` values with `"[REMOVED]"`
unless `sandbox_tester` is run with `--serialize-evidence`.

## Requirements

- Python 3.11.
- PowerShell on Windows.
- Oracle VirtualBox, when using `virtualbox_sandbox`.
- QEMU for Windows, when using `qemu_sandbox`.
- Docker Desktop with Linux containers enabled, when using `docker_sandbox`.
- An Ubuntu Server ISO, when creating a new VirtualBox base VM. The
  `virtualbox_sandbox` CLI accepts `--iso`, checks `SANDBOX_TESTER_ISO`, and
  then checks the Downloads directory.
- A prepared Ubuntu qcow2 base image at
  `.qemu_sandbox/ubuntu-24.04-sandbox-base-16g.compact.qcow2`, when using
  `qemu_sandbox`.
- Network access to pull the Playwright Python Docker base image, when the
  `docker_sandbox` image is first created.
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

## Running In QEMU

The QEMU workflow currently assumes a manually prepared Ubuntu qcow2 base image
with OpenSSH, Python, Playwright dependencies, and Chromium already installed.
The default base image path is:

```text
.qemu_sandbox/ubuntu-24.04-sandbox-base-16g.compact.qcow2
```

Run the `sandbox_tester` agent in a disposable QEMU VM:

```powershell
.\.venv\Scripts\python.exe -m qemu_sandbox --agent sandbox_tester
```

Run the same agent with QEMU's `microvm` machine type:

```powershell
.\.venv\Scripts\python.exe -m qemu_sandbox --machine microvm --agent sandbox_tester
```

To serialize captured evidence from the guest report:

```powershell
.\.venv\Scripts\python.exe -m qemu_sandbox --agent sandbox_tester --serialize-evidence
```

For each disposable run, `qemu_sandbox` copies the base qcow2 image into
`.qemu_sandbox/runs/run-...`, starts QEMU using automatic accelerator selection,
waits for SSH, prepares a guest run directory under `/tmp/sandbox-tester`,
uploads the Python agent source, runs it, downloads artifacts, then shuts down
the VM and removes the copied run disk. Use `--keep-vm` to leave the VM running
and retain its copied disk for inspection after setup or execution.

The default `q35` mode uses normal PC-style QEMU devices. The `microvm` mode
uses direct Linux boot with `.qemu_sandbox/kernel/vmlinuz`,
`.qemu_sandbox/kernel/initrd.img`, the prepared base image root UUID, and
virtio-mmio block/network devices.

The file protocol for each QEMU run is:

```text
.qemu_sandbox/runs/run-YYYY-mm-dd-HH-MM-SS/
  config.json
  report.json
  stderr.txt
  stdout.txt
  run-metadata.json
  serial.log                    # when run with --machine microvm
  playwright_shell_screenshot.png
  playwright_tool_screenshot.png
  ubuntu-24.04-sandbox-run.qcow2  # only retained with --keep-vm
```

## Running In Docker

The Docker workflow uses a reusable base image and a disposable container for
each Sandbox Tester run. If the selected profile image does
not exist, the harness builds it from
`src/docker_sandbox/dockerfile/Dockerfile`. The image is based on the
Playwright Python Ubuntu image so Chromium-based browser probes can run inside
the container. The image contains runtime dependencies, while the current
project `src` tree is mounted into each disposable container as read-only source
so code changes do not require rebuilding the image.

Run the `sandbox_tester` agent in a disposable Docker container:

```powershell
.\.venv\Scripts\python.exe -m docker_sandbox
```

To serialize captured evidence from the container report:

```powershell
.\.venv\Scripts\python.exe -m docker_sandbox --serialize-evidence
```

Run the first read-only filesystem hardening profile:

```powershell
.\.venv\Scripts\python.exe -m docker_sandbox --profile readonly-fs
```

For each run, `docker_sandbox` creates a timestamped run directory under
`.docker_sandbox/runs`, writes a Linux `CapabilityContext` to `config.json`,
starts a named disposable container, bind-mounts the run directory at
`/sandbox-output`, creates the profile's configured allowed and denied fixture
directories, runs `sandbox_tester`, saves stdout, stderr, metadata, and
generated report artifacts, then removes the container. Use
`--keep-container` to leave the container available for inspection after
execution.

The Docker harness forwards configured environment variables into the container.
Currently `OPENAI_API_KEY` is configured as `[local]`, which means the value is
copied from the host environment when present. The Docker command records only
the variable name, not the secret value, in run metadata.

The `baseline` profile uses `sandbox-tester/docker-sandbox:baseline` and keeps
the original Docker runtime behavior. The `readonly-fs` profile uses
`sandbox-tester/docker-sandbox:readonly-fs`, starts the container with a
read-only root filesystem, keeps `/sandbox-output` writable through the run
artifact bind mount, provides writable `/tmp`-backed HOME and XDG runtime
directories for Python, Playwright, and Chromium, moves the writable work and
allowed fixture tree to `/sandbox-work`, and mounts the denied fixture at
`/sandbox-denied` as read-only. The writable tmpfs data mounts `/tmp` and
`/sandbox-work` are mounted with `noexec` so newly written native executables
or shell scripts cannot be launched directly from those paths. The profile also
starts `sandbox_tester` through a Landlock launcher that applies a
container-side path policy: trusted runtime and source paths are readable, image
runtime paths are executable, writable data paths are not executable, and the
denied fixture is not granted read or write access.

The `network-egress` profile starts from the same Docker runtime options,
fixture layout, and Landlock policy as `readonly-fs`, but uses the separate
image tag `sandbox-tester/docker-sandbox:network-egress` so network egress
controls can be introduced and measured independently. It creates a per-run
internal Docker network, starts a Squid sidecar gateway container, connects the
gateway to both Docker's normal bridge network and the internal run network,
and starts the sandbox container only on the internal network with HTTP and
HTTPS proxy environment variables pointing at the gateway. The Squid
configuration is generated into the run directory from the profile's allowed
domain list and the network-relevant values in the generated
`CapabilityContext`.

The `ambient-services` profile starts from the same read-only filesystem,
Landlock, and Squid proxy sidecar settings as `network-egress`, but uses the
separate image tag `sandbox-tester/docker-sandbox:ambient-services` so local
service and IPC isolation controls can be introduced and measured independently.
It runs with a private IPC namespace instead of host IPC and gives Chromium a
bounded private shared-memory area through Docker's `--shm-size` setting.
The profile also inherits opt-out Docker guards that drop all Linux
capabilities, set `no-new-privileges`, use a private cgroup namespace, and
limit the number of container processes.
Host service sockets, such as Docker runtime sockets or SSH agent sockets, are
not mounted by default; future exceptions are intended to be declared as
explicit profile socket mounts. SSH and GPG agent sockets are also explicit
profile opt-ins: when configured, the harness mounts only the declared socket
and injects the matching container-side `SSH_AUTH_SOCK` or `GNUPGHOME` value.
Browser debugging surfaces are disabled by default: no debugging URL, direct
browser executable, or existing browser profile is advertised to
`sandbox_tester` unless the profile explicitly opts in.
The profile also scrubs common ambient session variables such as SSH agent,
GPG agent, D-Bus, X11, and Wayland hints, while giving GPG tooling an isolated
temporary home inside the container.
GPG, SSH, D-Bus, and Linux service-management command-line tools are denied by
profile-controlled bind-mounted stubs unless a future profile opts back in.

The `execution-control` profile starts from the same Docker runtime options,
Landlock policy, Squid proxy sidecar, ambient-service controls, and default
denied service tools as `ambient-services`, but uses the separate image tag
`sandbox-tester/docker-sandbox:execution-control` so process and executable
controls can be added and measured independently. It expands the profile's
bind-mounted executable denial list to cover common package managers,
source-control tools, admin and namespace tools, scheduling helpers, extra
interpreters, and background-process helpers while leaving Python, `/bin/sh`,
Playwright, and Chromium available for the tester itself.

The `syscall-control` profile starts from the same Docker runtime options,
Landlock policy, Squid proxy sidecar, ambient-service controls, and executable
denial list as `execution-control`, but uses the separate image tag
`sandbox-tester/docker-sandbox:syscall-control` so seccomp and other syscall
controls can be added and measured independently. Its first seccomp policy
keeps the normal Python, Playwright, Chromium, and OpenAI API workload
available while denying syscall families for mounts, namespace attachment,
keyrings, ptrace and process memory inspection, kernel module loading, BPF,
performance events, and other low-level privileged operations.

The `resource-limits` profile starts from the same Docker runtime options,
Landlock policy, Squid proxy sidecar, executable denial list, and seccomp
policy as `syscall-control`, but uses the separate image tag
`sandbox-tester/docker-sandbox:resource-limits` so explicit CPU, memory,
process, and file-descriptor limits can be added and measured independently.
Its first resource policy limits the container to 2 CPUs, 2 GB of memory with
no extra swap allowance, 512 processes, and bounded `nofile` and `nproc`
ulimits while leaving enough room for Python, Playwright, Chromium, and the
OpenAI API probe.

The `browser-surface` profile starts from the same Docker runtime options,
Landlock policy, Squid proxy sidecar, executable denial list, seccomp policy,
and resource limits as `resource-limits`, but uses the separate image tag
`sandbox-tester/docker-sandbox:browser-surface` so browser-adjacent hardening
can be added and measured independently. Its first browser-surface policy
passes explicit hardened Chromium flags to the Playwright screenshot probes,
including flags that disable sync, background networking, extensions, component
updates, password-store integration, external media routing, audio output, and
GPU acceleration. It also keeps browser debugging surfaces unadvertised,
continues to use fresh temporary browser profiles, and disables configured
camera and microphone capture by default while keeping the Playwright screenshot
probes working.

The `dns-proxy-control` profile starts from the same Docker runtime options,
Landlock policy, Squid proxy sidecar, executable denial list, seccomp policy,
resource limits, and browser-surface controls as `browser-surface`, but uses the
separate image tag `sandbox-tester/docker-sandbox:dns-proxy-control` so DNS and
proxy-bypass hardening can be added and measured independently. Its first DNS
policy points the sandbox container at the gateway address as its DNS server,
which keeps ordinary HTTP and HTTPS traffic on the proxy path while making
direct DNS lookups fail closed because the gateway is not a general DNS
resolver. It also uses short DNS timeouts and maps Docker host shortcut names
such as `host.docker.internal` to `0.0.0.0` inside the sandbox container.

The `minimized-image` profile starts from the same runtime hardening as
`dns-proxy-control`, but uses the separate image tag
`sandbox-tester/docker-sandbox:minimized-image` and passes the Dockerfile build
argument `SANDBOX_MINIMIZE_IMAGE=true`. The shared Dockerfile uses that flag to
remove or purge obvious nonessential command-line tools from the image after the
Python, Playwright, Chromium, font, and runtime dependencies have been prepared.
This includes package-management entry points, SSH/GPG tools, Git, Perl, service
management tools, namespace/admin helpers, and other command families already
blocked by the runtime denial-stub policy. The runtime stubs remain in place as
defense in depth, but the image now also attempts to make those tools absent
before the container starts.

The `filesystem-visibility` profile starts from the same minimized image and
runtime hardening as `minimized-image`, but uses the separate image tag
`sandbox-tester/docker-sandbox:filesystem-visibility` so filesystem and runtime
metadata exposure can be reduced and measured independently. Its first policy
keeps `/proc` readable for Python and Chromium compatibility, but explicitly
relies on Docker's default private PID and UTS namespaces, masks selected
existing `/proc` and `/sys` surfaces with small tmpfs mounts, removes broad
Landlock read access to `/sys`, keeps `/dev` available for Python and Chromium
compatibility, and adds a process file-size ulimit as a coarse output growth
guard.

The `runtime-control` profile starts from the same runtime hardening as
`filesystem-visibility`, but uses the separate image tag
`sandbox-tester/docker-sandbox:runtime-control` so Python runtime controls can
be added and measured independently. Its first image policy passes the
Dockerfile build argument `SANDBOX_REMOVE_PYTHON_PACKAGING=true`, which removes
`pip`, `setuptools`, `wheel`, and their package metadata from the virtualenv
and global Python paths after the image's Python dependencies have already been
installed. It also removes related packaging support such as `ensurepip`,
`pkg_resources`, setuptools' `_distutils_hack`, and global packaging command
entry points. It writes a small `sitecustomize.py` guard that denies imports of
`pip`, `ensurepip`, `setuptools`, and `wheel`, so `python -m pip` fails even if
packaging files are accidentally reintroduced. The same guard denies
`ctypes` imports to block direct native operating-system API calls from Python,
and denies Python script execution and module imports from writable data paths
such as `/sandbox-work`, `/sandbox-output`, and `/tmp`. This is intended to
deny runtime package installation, direct Python native API calls, and newly
written Python code execution while keeping Python, Playwright, Chromium, and
the OpenAI Responses API runtime available.

The `network-socket-control` profile starts from the same runtime hardening as
`runtime-control`, but uses the separate image tag
`sandbox-tester/docker-sandbox:network-socket-control` so socket-level network
controls can be added and measured independently. It enables runtime guards
that deny Python UDP sockets, deny Python binds to all network interfaces, and
deny Python connections to common link-local metadata endpoints. It also sets
Docker's `net.ipv4.ip_unprivileged_port_start` sysctl back to `1024`, expands
`NO_PROXY` for metadata endpoint names so proxy 403 responses are not mistaken
for successful metadata access, and maps `metadata.google.internal` to
`0.0.0.0` alongside the other blocked Docker host shortcut names.

The `desktop-channel-control` profile starts from the same runtime hardening as
`network-socket-control`, but uses the separate image tag
`sandbox-tester/docker-sandbox:desktop-channel-control` so desktop automation
channel controls can be added and measured independently. Desktop automation
channels are denied by default for Docker profiles: the harness removes display,
Wayland, D-Bus, and X authority environment hints, and this profile's image
removes common desktop query tools such as `gdbus`, `qdbus`, `wmctrl`, and
`xdotool`. Future profiles can explicitly opt back in to desktop automation
channel access by enabling the profile's desktop automation flag and building
from an image that keeps the required tools.

The `system-config-control` profile starts from the same runtime hardening as
`desktop-channel-control`, but uses the separate image tag
`sandbox-tester/docker-sandbox:system-config-control` so system configuration
and administration controls can be added and measured independently. Its image
removes package-manager metadata such as the dpkg and apt databases after the
runtime dependencies are installed, reducing the installed-software inventory
available to the agent. The profile also mounts common user autostart
directories as read-only, so startup-item probes cannot create autostart
entries while the broader temporary home and config directories remain
available for Python, Playwright, and Chromium.

The `hardware-device-control` profile starts from the same runtime hardening as
`system-config-control`, but uses the separate image tag
`sandbox-tester/docker-sandbox:hardware-device-control` so hardware and
peripheral visibility controls can be added and measured independently. It
enables a runtime guard that denies camera, microphone, printer, USB, serial,
and Bluetooth enumeration paths used by the Sandbox Tester probes, while
leaving GPU detail probing available for separate measurement. This keeps the
normal Python, Playwright, Chromium, and OpenAI API workload available without
advertising most host peripheral surfaces to the agent.

The file protocol for each Docker run is:

```text
.docker_sandbox/runs/run-YYYY-mm-dd-HH-MM-SS/
  config.json
  report.json
  stderr.txt
  stdout.txt
  status.ndjson
  done.json
  run-metadata.json
  playwright_shell_screenshot.png
  playwright_tool_screenshot.png
```

## Architecture

The project is split into five packages:

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
- `qemu_sandbox`: the QEMU orchestration harness. It manages disposable run disk
  creation from a prepared qcow2 base image, QEMU process lifecycle, guest
  credentials, user-mode SSH port forwarding, agent execution, artifact
  download, and VM teardown.
- `docker_sandbox`: the Docker orchestration harness. It manages Docker image
  creation, disposable container execution, container fixture setup, environment
  variable forwarding, mounted artifact output, run metadata, and container
  teardown.

`local_sandbox` still invokes `sandbox_tester` locally as the current user.
`virtualbox_sandbox` and `qemu_sandbox` exercise the same file-based boundary
across an SSH connection into a disposable Ubuntu guest, so the host prepares
the guest environment and the guest agent tests the capabilities available
inside that VM. `docker_sandbox` exercises a similar file-based boundary inside
a disposable Linux container using a bind-mounted artifact directory.

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

For QEMU runs, VM configuration is exposed through `src/qemu_sandbox/cli.py`
flags such as `--base-directory`, `--base-image`, `--kernel`, `--initrd`,
`--kernel-append`, `--qemu`, `--machine`, `--accelerator`, `--cpu`,
`--memory-mb`, `--cpus`, `--guest-user`, `--keep-vm`, `--agent`, `--verbose`,
and `--serialize-evidence`. The implementation uses the existing Python agent
profile and guest runner shared with `virtualbox_sandbox`.

For Docker runs, configuration is exposed through `src/docker_sandbox/cli.py`
flags such as `--base-directory`, `--profile`, `--dockerfile`, `--guest-user`,
`--keep-container`, `--verbose`, and `--serialize-evidence`. Each profile owns
its Docker image tag; the default `baseline` profile uses
`sandbox-tester/docker-sandbox:baseline`. The default base directory is
`.docker_sandbox`, and the default container user is `sandbox`.

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
  group_30.py     Local AI agent tests

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

src/qemu_sandbox/
  __main__.py                 Package entry point for python -m qemu_sandbox
  cli.py                      QEMU command-line orchestration
  qemu_machine_factory.py     Run disk, SSH port, QEMU command, and teardown
  virtual_machine_setup.py    SSH setup, guest preparation, execution, artifacts
  credentials.py              Local guest credential creation/loading
  run_results.py              Local run artifact persistence
  models.py                   QEMU orchestration dataclasses

src/docker_sandbox/
  __main__.py                 Package entry point for python -m docker_sandbox
  cli.py                      Docker command-line orchestration
  container_factory.py        Docker image inspection and build operations
  sandbox_container.py        Disposable container execution and fixture setup
  run_results.py              Local run artifact persistence
  models.py                   Docker orchestration dataclasses
  dockerfile/Dockerfile       Playwright Python image used for container runs

tests/
  test_smoke.py
  test_redaction.py
  test_runner_serialization.py
  test_docker_sandbox.py

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
