"""Group 23: Sandbox Identity."""

from __future__ import annotations

import asyncio
import os
import platform
import socket
import subprocess
from pathlib import Path

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_LINUX_CONTAINER_MARKERS = [
    Path("/.dockerenv"),
    Path("/run/.containerenv"),
]
_LINUX_CGROUP_PATH = Path("/proc/1/cgroup")
_LINUX_SELF_CGROUP_PATH = Path("/proc/self/cgroup")
_LINUX_SELF_STATUS_PATH = Path("/proc/self/status")
_LINUX_SELF_NAMESPACE_DIRECTORY = Path("/proc/self/ns")
_LINUX_APPARMOR_CURRENT_PATH = Path("/proc/self/attr/current")
_LINUX_SELINUX_ENFORCE_PATH = Path("/sys/fs/selinux/enforce")
_LINUX_PRODUCT_NAME_PATH = Path("/sys/class/dmi/id/product_name")
_LINUX_PRODUCT_VERSION_PATH = Path("/sys/class/dmi/id/product_version")
_LINUX_MACHINE_ID_PATHS = [
    Path("/etc/machine-id"),
    Path("/var/lib/dbus/machine-id"),
]
_LINUX_DOMAIN_PATHS = [
    Path("/etc/resolv.conf"),
    Path("/etc/krb5.conf"),
    Path("/etc/sssd/sssd.conf"),
    Path("/etc/samba/smb.conf"),
]
_NO_SHELL_CANDIDATE_EXIT_CODE = 127
_LINUX_CAPABILITY_NAMES = {
    0: "CAP_CHOWN",
    1: "CAP_DAC_OVERRIDE",
    2: "CAP_DAC_READ_SEARCH",
    3: "CAP_FOWNER",
    4: "CAP_FSETID",
    5: "CAP_KILL",
    6: "CAP_SETGID",
    7: "CAP_SETUID",
    8: "CAP_SETPCAP",
    9: "CAP_LINUX_IMMUTABLE",
    10: "CAP_NET_BIND_SERVICE",
    11: "CAP_NET_BROADCAST",
    12: "CAP_NET_ADMIN",
    13: "CAP_NET_RAW",
    14: "CAP_IPC_LOCK",
    15: "CAP_IPC_OWNER",
    16: "CAP_SYS_MODULE",
    17: "CAP_SYS_RAWIO",
    18: "CAP_SYS_CHROOT",
    19: "CAP_SYS_PTRACE",
    20: "CAP_SYS_PACCT",
    21: "CAP_SYS_ADMIN",
    22: "CAP_SYS_BOOT",
    23: "CAP_SYS_NICE",
    24: "CAP_SYS_RESOURCE",
    25: "CAP_SYS_TIME",
    26: "CAP_SYS_TTY_CONFIG",
    27: "CAP_MKNOD",
    28: "CAP_LEASE",
    29: "CAP_AUDIT_WRITE",
    30: "CAP_AUDIT_CONTROL",
    31: "CAP_SETFCAP",
    32: "CAP_MAC_OVERRIDE",
    33: "CAP_MAC_ADMIN",
    34: "CAP_SYSLOG",
    35: "CAP_WAKE_ALARM",
    36: "CAP_BLOCK_SUSPEND",
    37: "CAP_AUDIT_READ",
    38: "CAP_PERFMON",
    39: "CAP_BPF",
    40: "CAP_CHECKPOINT_RESTORE",
}
_CLOUD_ENVIRONMENT_PREFIXES = [
    "AWS_",
    "AZURE_",
    "GOOGLE_CLOUD_",
    "GCP_",
]
_CLOUD_ENVIRONMENT_NAMES = [
    "CLOUD_RUN_JOB",
    "CLOUD_RUN_SERVICE",
    "FUNCTIONS_WORKER_RUNTIME",
    "KUBERNETES_SERVICE_HOST",
    "WEBSITE_SITE_NAME",
]


class G23_T01:
    id = "T01"
    title = "Detect container / VM / cloud runtime markers"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_runtime_marker_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected sandbox identity runtime markers.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not detect sandbox identity runtime markers.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell sandbox identity marker detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell sandbox identity marker detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _detect_runtime_markers_with_python,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected sandbox identity runtime markers.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime sandbox identity marker detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G23_T02:
    id = "T02"
    title = "Read Linux cgroup and namespace status"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_cgroup_namespace_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux cgroup and namespace status.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux cgroup and namespace status is not applicable.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read Linux cgroup and namespace status.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell cgroup and namespace detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell cgroup and namespace detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux cgroup and namespace status is not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(
                _detect_cgroup_namespace_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read Linux cgroup and namespace status.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime cgroup and namespace detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G23_T03:
    id = "T03"
    title = "Read Linux confinement status"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_confinement_status_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux confinement status.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux confinement status is not applicable.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read Linux confinement status.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell confinement status detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell confinement status detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Linux confinement status is not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(_detect_confinement_with_python)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read Linux confinement status.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime confinement status detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G23_T04:
    id = "T04"
    title = "Detect effective Linux capabilities"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_linux_capability_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected effective Linux capabilities.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Effective Linux capabilities are not applicable.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not detect effective Linux capabilities.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Linux capability detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Linux capability detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Effective Linux capabilities are not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(
                _detect_linux_capabilities_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected effective Linux capabilities.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime Linux capability detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G23_T05:
    id = "T05"
    title = "Detect Windows integrity and containment status"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_windows_identity_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected Windows integrity and containment status.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary=(
                        "Windows integrity and containment status is not "
                        "applicable."
                    ),
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not detect Windows integrity and containment "
                    "status."
                ),
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Windows identity detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Windows identity detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system == OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=(
                    "Windows integrity and containment status is not applicable."
                ),
            )

        try:
            evidence = await asyncio.to_thread(
                _detect_windows_identity_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime detected Windows integrity and containment "
                    "status."
                ),
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime Windows identity detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G23_T06:
    id = "T06"
    title = "Detect host identity and domain visibility"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_host_identity_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected host identity and domain visibility.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not detect host identity and domain visibility."
                ),
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell host identity detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell host identity detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(
                _detect_host_identity_with_python,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime detected host identity and domain visibility."
                ),
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime host identity detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G23",
        title="Sandbox Identity",
        tests=[
            G23_T01(capability_context),
            G23_T02(capability_context),
            G23_T03(capability_context),
            G23_T04(capability_context),
            G23_T05(capability_context),
            G23_T06(capability_context),
        ],
    )


def _run_shell_runtime_marker_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_runtime_marker_command()
    else:
        command = _build_linux_runtime_marker_command()

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _run_shell_cgroup_namespace_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _not_applicable_completed_process(
            "Linux cgroup and namespace status is not applicable."
        )

    return subprocess.run(
        _build_linux_cgroup_namespace_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _run_shell_confinement_status_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _not_applicable_completed_process(
            "Linux confinement status is not applicable."
        )

    return subprocess.run(
        _build_linux_confinement_status_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _run_shell_linux_capability_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return _not_applicable_completed_process(
            "Effective Linux capabilities are not applicable."
        )

    return subprocess.run(
        _build_linux_capability_detection_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _run_shell_windows_identity_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.LINUX:
        return _not_applicable_completed_process(
            "Windows integrity and containment status is not applicable."
        )

    return subprocess.run(
        _build_windows_identity_detection_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _run_shell_host_identity_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_host_identity_command()
    else:
        command = _build_linux_host_identity_command()

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_windows_runtime_marker_command() -> list[str]:
    script = """
$ErrorActionPreference = 'Stop'
$computer = Get-CimInstance Win32_ComputerSystem
$bios = Get-CimInstance Win32_BIOS
$cloudNames = @(
    'AWS_',
    'AZURE_',
    'GOOGLE_CLOUD_',
    'GCP_',
    'CLOUD_RUN_JOB',
    'CLOUD_RUN_SERVICE',
    'FUNCTIONS_WORKER_RUNTIME',
    'KUBERNETES_SERVICE_HOST',
    'WEBSITE_SITE_NAME'
)
$cloudMarkers = @()
foreach ($name in [Environment]::GetEnvironmentVariables().Keys) {
    foreach ($candidate in $cloudNames) {
        if ($name -eq $candidate -or $name.StartsWith($candidate)) {
            $cloudMarkers += $name
        }
    }
}
$parts = @(
    "manufacturer=$($computer.Manufacturer)",
    "model=$($computer.Model)",
    "bios_serial_present=$([bool]$bios.SerialNumber)",
    "cloud_env_count=$($cloudMarkers.Count)",
    "cloud_env=[$($cloudMarkers -join ',')]"
)
Write-Output ($parts -join '; ')
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _build_windows_host_identity_command() -> list[str]:
    script = """
$ErrorActionPreference = 'Stop'
$computer = Get-CimInstance Win32_ComputerSystem
$machineGuid = ''
$machineGuidPresent = $false
try {
    $machineGuid = (
        Get-ItemProperty `
            -Path 'HKLM:\\SOFTWARE\\Microsoft\\Cryptography' `
            -Name MachineGuid `
            -ErrorAction Stop
    ).MachineGuid
    $machineGuidPresent = [bool]$machineGuid
}
catch {
    $machineGuidPresent = $false
}
$parts = @(
    "hostname=$env:COMPUTERNAME",
    "dns_hostname=$($computer.DNSHostName)",
    "domain=$($computer.Domain)",
    "workgroup=$($computer.Workgroup)",
    "part_of_domain=$($computer.PartOfDomain)",
    "machine_guid_present=$machineGuidPresent"
)
Write-Output ($parts -join '; ')
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _build_windows_identity_detection_command() -> list[str]:
    script = """
$ErrorActionPreference = 'Stop'
$languageMode = $ExecutionContext.SessionState.LanguageMode
$mandatoryLabel = whoami /groups |
    Select-String 'Mandatory Label' |
    Select-Object -First 1
$integrity = ''
if ($null -ne $mandatoryLabel) {
    $integrity = ($mandatoryLabel.Line -replace '^\\s+', '')
}
$source = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

public static class SandboxTesterToken {
    [DllImport("advapi32.dll", SetLastError=true)]
    private static extern bool OpenProcessToken(
        IntPtr ProcessHandle,
        UInt32 DesiredAccess,
        out IntPtr TokenHandle);

    [DllImport("advapi32.dll", SetLastError=true)]
    private static extern bool GetTokenInformation(
        IntPtr TokenHandle,
        int TokenInformationClass,
        out int TokenInformation,
        int TokenInformationLength,
        out int ReturnLength);

    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool CloseHandle(IntPtr handle);

    public static bool IsAppContainer() {
        const UInt32 TOKEN_QUERY = 0x0008;
        const int TokenIsAppContainer = 29;
        IntPtr tokenHandle;
        if (!OpenProcessToken(
            Process.GetCurrentProcess().Handle,
            TOKEN_QUERY,
            out tokenHandle)) {
            throw new System.ComponentModel.Win32Exception();
        }

        try {
            int isAppContainer;
            int returnLength;
            if (!GetTokenInformation(
                tokenHandle,
                TokenIsAppContainer,
                out isAppContainer,
                sizeof(int),
                out returnLength)) {
                throw new System.ComponentModel.Win32Exception();
            }

            return isAppContainer != 0;
        }
        finally {
            CloseHandle(tokenHandle);
        }
    }
}
'@
Add-Type -TypeDefinition $source
$isAppContainer = [SandboxTesterToken]::IsAppContainer()
$parts = @(
    "integrity=$integrity",
    "app_container=$isAppContainer",
    "powershell_language_mode=$languageMode"
)
Write-Output ($parts -join '; ')
"""
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def _build_linux_runtime_marker_command() -> list[str]:
    cloud_pattern = (
        "^(AWS_|AZURE_|GOOGLE_CLOUD_|GCP_|CLOUD_RUN_JOB|"
        "CLOUD_RUN_SERVICE|FUNCTIONS_WORKER_RUNTIME|"
        "KUBERNETES_SERVICE_HOST|WEBSITE_SITE_NAME)"
    )
    printf_format = (
        "container_markers=[%s]; cgroup=%s; product_name=%s; "
        "product_version=%s; virt=%s; cloud_env_count=%s; cloud_env=[%s]\\n"
    )
    script = """
set -u
markers=""
for marker in /.dockerenv /run/.containerenv; do
    if [ -e "$marker" ]; then
        markers="${markers}${marker},"
    fi
done
cgroup=""
if [ -r /proc/1/cgroup ]; then
    cgroup=$(head -n 5 /proc/1/cgroup | tr '\\n' '|' | cut -c 1-200)
fi
product_name=""
if [ -r /sys/class/dmi/id/product_name ]; then
    product_name=$(head -n 1 /sys/class/dmi/id/product_name)
fi
product_version=""
if [ -r /sys/class/dmi/id/product_version ]; then
    product_version=$(head -n 1 /sys/class/dmi/id/product_version)
fi
virt=""
if command -v systemd-detect-virt >/dev/null 2>&1; then
    virt=$(systemd-detect-virt 2>/dev/null || true)
fi
cloud_env=$(env | cut -d= -f1 | grep -E __CLOUD_PATTERN__ | paste -sd, -)
cloud_count=0
if [ -n "$cloud_env" ]; then
    cloud_count=$(printf '%s' "$cloud_env" | tr ',' '\\n' | wc -l)
fi
printf __PRINTF_FORMAT__ \
    "$markers" \
    "$cgroup" \
    "$product_name" \
    "$product_version" \
    "$virt" \
    "$cloud_count" \
    "$cloud_env"
"""
    script = script.replace("__CLOUD_PATTERN__", repr(cloud_pattern))
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _build_linux_host_identity_command() -> list[str]:
    printf_format = (
        "hostname=%s; fqdn=%s; machine_id_present=%s; "
        "domain_config_present=[%s]\\n"
    )
    script = """
set -u
hostname_value=$(hostname 2>/dev/null || true)
fqdn_value=$(hostname -f 2>/dev/null || true)
machine_id_present=False
if [ -r /etc/machine-id ] || [ -r /var/lib/dbus/machine-id ]; then
    machine_id_present=True
fi
domain_config=""
for path in /etc/resolv.conf /etc/krb5.conf /etc/sssd/sssd.conf /etc/samba/smb.conf; do
    if [ -r "$path" ]; then
        domain_config="${domain_config}${path},"
    fi
done
printf __PRINTF_FORMAT__ \
    "$hostname_value" \
    "$fqdn_value" \
    "$machine_id_present" \
    "$domain_config"
"""
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _build_linux_capability_detection_command() -> list[str]:
    printf_format = (
        "cap_eff=%s; decoded=%s; capsh_available=%s; "
        "cap_sys_admin_present=%s; cap_net_raw_present=%s\\n"
    )
    script = """
set -u
if [ ! -r /proc/self/status ]; then
    exit 1
fi
cap_eff=$(awk '/^CapEff:/ {print $2}' /proc/self/status)
decoded=""
capsh_available=False
cap_sys_admin_present=unknown
cap_net_raw_present=unknown
if command -v capsh >/dev/null 2>&1; then
    capsh_available=True
    decoded=$(capsh --decode="$cap_eff" 2>/dev/null || true)
    case "$decoded" in
        *cap_sys_admin*) cap_sys_admin_present=True ;;
        *) cap_sys_admin_present=False ;;
    esac
    case "$decoded" in
        *cap_net_raw*) cap_net_raw_present=True ;;
        *) cap_net_raw_present=False ;;
    esac
fi
printf __PRINTF_FORMAT__ \
    "$cap_eff" \
    "$decoded" \
    "$capsh_available" \
    "$cap_sys_admin_present" \
    "$cap_net_raw_present"
"""
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _build_linux_cgroup_namespace_command() -> list[str]:
    printf_format = "cgroup=%s; namespaces=[%s]\\n"
    script = """
set -u
cgroup=""
if [ -r /proc/self/cgroup ]; then
    cgroup=$(head -n 10 /proc/self/cgroup | tr '\\n' '|' | cut -c 1-300)
fi
namespaces=""
if [ -d /proc/self/ns ]; then
    for namespace in /proc/self/ns/*; do
        name=$(basename "$namespace")
        target=$(readlink "$namespace" 2>/dev/null || true)
        namespaces="${namespaces}${name}:${target},"
    done
fi
printf __PRINTF_FORMAT__ "$cgroup" "$namespaces"
"""
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _build_linux_confinement_status_command() -> list[str]:
    printf_format = (
        "apparmor=%s; selinux_enforce=%s; seccomp=%s; "
        "seccomp_filters=%s; jail=not_applicable\\n"
    )
    script = """
set -u
apparmor=""
if [ -r /proc/self/attr/current ]; then
    apparmor=$(head -n 1 /proc/self/attr/current)
fi
selinux_enforce=""
if [ -r /sys/fs/selinux/enforce ]; then
    selinux_enforce=$(head -n 1 /sys/fs/selinux/enforce)
fi
seccomp=""
seccomp_filters=""
if [ -r /proc/self/status ]; then
    seccomp=$(awk '/^Seccomp:/ {print $2}' /proc/self/status)
    seccomp_filters=$(awk '/^Seccomp_filters:/ {print $2}' /proc/self/status)
fi
printf __PRINTF_FORMAT__ \
    "$apparmor" \
    "$selinux_enforce" \
    "$seccomp" \
    "$seccomp_filters"
"""
    script = script.replace("__PRINTF_FORMAT__", repr(printf_format))
    return ["sh", "-c", script]


def _detect_runtime_markers_with_python(
    operating_system: OperatingSystem,
) -> str:
    cloud_environment_names = _detect_cloud_environment_names()

    if operating_system == OperatingSystem.WINDOWS:
        return _detect_windows_runtime_markers(cloud_environment_names)

    return _detect_linux_runtime_markers(cloud_environment_names)


def _detect_windows_runtime_markers(cloud_environment_names: list[str]) -> str:
    computer_name = os.environ.get("COMPUTERNAME", "")
    processor_identifier = os.environ.get("PROCESSOR_IDENTIFIER", "")

    return (
        f"computer_name_present={bool(computer_name)}; "
        f"processor_identifier_present={bool(processor_identifier)}; "
        f"cloud_env_count={len(cloud_environment_names)}; "
        f"cloud_env=[{','.join(cloud_environment_names)}]"
    )


def _detect_linux_runtime_markers(cloud_environment_names: list[str]) -> str:
    container_markers = [
        str(path)
        for path in _LINUX_CONTAINER_MARKERS
        if path.exists()
    ]
    cgroup_sample = _read_text_sample(_LINUX_CGROUP_PATH)
    product_name = _read_text_sample(_LINUX_PRODUCT_NAME_PATH)
    product_version = _read_text_sample(_LINUX_PRODUCT_VERSION_PATH)

    return (
        f"container_markers=[{','.join(container_markers)}]; "
        f"cgroup={cgroup_sample}; "
        f"product_name={product_name}; "
        f"product_version={product_version}; "
        f"cloud_env_count={len(cloud_environment_names)}; "
        f"cloud_env=[{','.join(cloud_environment_names)}]"
    )


def _detect_cgroup_namespace_with_python() -> str:
    cgroup_sample = _read_text_sample(_LINUX_SELF_CGROUP_PATH)
    namespaces = _read_linux_namespaces()
    namespace_evidence = ",".join(
        f"{name}:{target}"
        for name, target in namespaces.items()
    )

    return f"cgroup={cgroup_sample}; namespaces=[{namespace_evidence}]"


def _detect_confinement_with_python() -> str:
    apparmor = _read_text_sample(_LINUX_APPARMOR_CURRENT_PATH).strip()
    selinux_enforce = _read_text_sample(_LINUX_SELINUX_ENFORCE_PATH).strip()
    status_values = _read_linux_status_values(
        ["Seccomp", "Seccomp_filters"],
    )
    seccomp = status_values.get("Seccomp", "")
    seccomp_filters = status_values.get("Seccomp_filters", "")

    return (
        f"apparmor={apparmor}; "
        f"selinux_enforce={selinux_enforce}; "
        f"seccomp={seccomp}; "
        f"seccomp_filters={seccomp_filters}; "
        "jail=not_applicable"
    )


def _detect_linux_capabilities_with_python() -> str:
    status_values = _read_linux_status_values(["CapEff"])
    cap_eff = status_values.get("CapEff", "")

    if cap_eff == "":
        raise RuntimeError("Could not read CapEff from /proc/self/status.")

    capability_names = _decode_linux_capabilities(cap_eff)
    capability_set = set(capability_names)

    return (
        f"cap_eff={cap_eff}; "
        f"capability_count={len(capability_names)}; "
        f"cap_sys_admin_present={'CAP_SYS_ADMIN' in capability_set}; "
        f"cap_net_raw_present={'CAP_NET_RAW' in capability_set}; "
        f"capabilities=[{','.join(capability_names)}]"
    )


def _detect_windows_identity_with_python() -> str:
    token = _open_current_process_token()

    try:
        integrity_rid = _read_windows_integrity_rid(token)
        integrity_level = _map_windows_integrity_level(integrity_rid)
        app_container = _read_windows_app_container_status(token)
    finally:
        _close_windows_handle(token)

    return (
        f"integrity={integrity_level}; "
        f"integrity_rid={integrity_rid}; "
        f"app_container={app_container}; "
        "powershell_language_mode=not_applicable_to_python"
    )


def _open_current_process_token() -> int:
    import ctypes

    token_query = 0x0008
    token = ctypes.c_void_p()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    advapi32.OpenProcessToken.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi32.OpenProcessToken.restype = ctypes.c_bool
    process_handle = kernel32.GetCurrentProcess()
    opened = advapi32.OpenProcessToken(
        process_handle,
        token_query,
        ctypes.byref(token),
    )

    if not opened:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "OpenProcessToken failed")

    if token.value is None:
        raise OSError("OpenProcessToken returned an empty token handle.")

    return int(token.value)


def _read_windows_integrity_rid(token: int) -> int:
    import ctypes

    token_integrity_level = 25
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi32.GetTokenInformation.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    advapi32.GetTokenInformation.restype = ctypes.c_bool
    return_length = ctypes.c_uint32()
    advapi32.GetTokenInformation(
        ctypes.c_void_p(token),
        token_integrity_level,
        None,
        0,
        ctypes.byref(return_length),
    )
    buffer = ctypes.create_string_buffer(return_length.value)
    succeeded = advapi32.GetTokenInformation(
        ctypes.c_void_p(token),
        token_integrity_level,
        buffer,
        return_length,
        ctypes.byref(return_length),
    )

    if not succeeded:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "GetTokenInformation(TokenIntegrityLevel) failed")

    class _SidAndAttributes(ctypes.Structure):
        _fields_ = [
            ("sid", ctypes.c_void_p),
            ("attributes", ctypes.c_uint32),
        ]

    class _TokenMandatoryLabel(ctypes.Structure):
        _fields_ = [("label", _SidAndAttributes)]

    token_label = ctypes.cast(
        buffer,
        ctypes.POINTER(_TokenMandatoryLabel),
    ).contents
    sid = token_label.label.sid
    advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
    advapi32.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
    advapi32.GetSidSubAuthority.restype = ctypes.POINTER(ctypes.c_uint32)
    advapi32.GetSidSubAuthority.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    sub_authority_count = advapi32.GetSidSubAuthorityCount(sid).contents.value
    integrity_rid = advapi32.GetSidSubAuthority(
        sid,
        sub_authority_count - 1,
    ).contents.value

    return int(integrity_rid)


def _read_windows_app_container_status(token: int) -> bool:
    import ctypes

    token_is_app_container = 29
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi32.GetTokenInformation.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    advapi32.GetTokenInformation.restype = ctypes.c_bool
    is_app_container = ctypes.c_uint32()
    return_length = ctypes.c_uint32()
    succeeded = advapi32.GetTokenInformation(
        ctypes.c_void_p(token),
        token_is_app_container,
        ctypes.byref(is_app_container),
        ctypes.sizeof(is_app_container),
        ctypes.byref(return_length),
    )

    if not succeeded:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "GetTokenInformation(TokenIsAppContainer) failed")

    return is_app_container.value != 0


def _close_windows_handle(handle: int) -> None:
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_bool
    kernel32.CloseHandle(ctypes.c_void_p(handle))


def _map_windows_integrity_level(integrity_rid: int) -> str:
    if integrity_rid >= 0x5000:
        return "protected"
    if integrity_rid >= 0x4000:
        return "system"
    if integrity_rid >= 0x3000:
        return "high"
    if integrity_rid >= 0x2000:
        return "medium"
    if integrity_rid >= 0x1000:
        return "low"

    return "untrusted"


def _detect_host_identity_with_python(
    operating_system: OperatingSystem,
) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return _detect_windows_host_identity_with_python()

    return _detect_linux_host_identity_with_python()


def _detect_windows_host_identity_with_python() -> str:
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    computer_name = os.environ.get("COMPUTERNAME", "")
    user_domain = os.environ.get("USERDOMAIN", "")
    logon_server_present = bool(os.environ.get("LOGONSERVER", ""))
    machine_guid_present = _windows_machine_guid_is_readable()

    return (
        f"hostname={hostname}; "
        f"fqdn={fqdn}; "
        f"computer_name={computer_name}; "
        f"user_domain={user_domain}; "
        f"logon_server_present={logon_server_present}; "
        f"machine_guid_present={machine_guid_present}"
    )


def _detect_linux_host_identity_with_python() -> str:
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    node = platform.uname().node
    machine_id_present = any(path.exists() for path in _LINUX_MACHINE_ID_PATHS)
    readable_machine_id = any(
        path.is_file() and os.access(path, os.R_OK)
        for path in _LINUX_MACHINE_ID_PATHS
    )
    readable_domain_config = [
        str(path)
        for path in _LINUX_DOMAIN_PATHS
        if path.is_file() and os.access(path, os.R_OK)
    ]

    return (
        f"hostname={hostname}; "
        f"fqdn={fqdn}; "
        f"node={node}; "
        f"machine_id_present={machine_id_present}; "
        f"machine_id_readable={readable_machine_id}; "
        f"domain_config_present=[{','.join(readable_domain_config)}]"
    )


def _windows_machine_guid_is_readable() -> bool:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            machine_guid, _value_type = winreg.QueryValueEx(key, "MachineGuid")

        return bool(machine_guid)
    except OSError:
        return False


def _decode_linux_capabilities(capability_hex: str) -> list[str]:
    capability_value = int(capability_hex, 16)
    capability_names: list[str] = []

    for bit, name in _LINUX_CAPABILITY_NAMES.items():
        if capability_value & (1 << bit):
            capability_names.append(name)

    return capability_names


def _read_linux_namespaces() -> dict[str, str]:
    namespaces: dict[str, str] = {}

    if not _LINUX_SELF_NAMESPACE_DIRECTORY.exists():
        return namespaces

    for path in sorted(_LINUX_SELF_NAMESPACE_DIRECTORY.iterdir()):
        namespaces[path.name] = os.readlink(path)

    return namespaces


def _read_linux_status_values(keys: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}

    if not _LINUX_SELF_STATUS_PATH.exists():
        return values

    with _LINUX_SELF_STATUS_PATH.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:
        for line in file:
            name, separator, value = line.partition(":")

            if separator and name in keys:
                values[name] = value.strip()

    return values


def _detect_cloud_environment_names() -> list[str]:
    names: list[str] = []

    for name in os.environ:
        if name in _CLOUD_ENVIRONMENT_NAMES:
            names.append(name)
            continue

        if any(name.startswith(prefix) for prefix in _CLOUD_ENVIRONMENT_PREFIXES):
            names.append(name)

    return sorted(names)


def _read_text_sample(path: Path) -> str:
    if not path.exists():
        return ""

    with path.open("r", encoding="utf-8", errors="replace") as file:
        return file.read(200).replace("\n", "|")


def _not_applicable_completed_process(
    message: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
        stdout="",
        stderr=message,
    )


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
