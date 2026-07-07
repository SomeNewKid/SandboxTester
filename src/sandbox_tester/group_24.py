"""Group 24: Namespace And Escape-Relevant Surfaces."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
from pathlib import Path

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_NO_SHELL_CANDIDATE_EXIT_CODE = 127
_LINUX_SURFACE_DIRECTORIES = [
    Path("/proc"),
    Path("/sys"),
    Path("/dev"),
    Path("/run"),
    Path("/mnt"),
    Path("/media"),
]
_LINUX_PROCESS_NAMESPACE_DIRECTORY = Path("/proc/self/ns")
_LINUX_SERVICE_ACCOUNT_PATHS = [
    Path("/var/run/secrets/kubernetes.io"),
    Path("/run/secrets/kubernetes.io"),
    Path("/run/secrets"),
    Path("/var/run/secrets"),
]
_LINUX_MOUNTINFO_PATH = Path("/proc/self/mountinfo")
_LINUX_CONTAINER_RUNTIME_SOCKET_PATHS = [
    Path("/run/containerd/containerd.sock"),
    Path("/var/run/containerd/containerd.sock"),
    Path("/run/crio/crio.sock"),
    Path("/var/run/crio/crio.sock"),
    Path("/run/podman/podman.sock"),
    Path("/var/run/podman/podman.sock"),
]


class G24_T01:
    id = "T01"
    title = "Read Linux namespace surface directories"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_surface_directory_listing,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux namespace surface directories.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux namespace surface directories are not applicable.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read all Linux namespace surface directories.",
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
                summary="Shell namespace surface directory listing timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell namespace surface directory listing failed.",
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
                summary="Linux namespace surface directories are not applicable.",
            )

        try:
            all_readable, evidence = await asyncio.to_thread(
                _read_surface_directories_with_python,
            )

            if all_readable:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime read Linux namespace surface directories.",
                    evidence=evidence,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not read all Linux namespace surface "
                    "directories."
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
                summary="Python runtime namespace surface directory listing failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G24_T02:
    id = "T02"
    title = "Read Linux process namespace links"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_process_namespace_link_read,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux process namespace links.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux process namespace links are not applicable.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read Linux process namespace links.",
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
                summary="Shell process namespace link read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell process namespace link read failed.",
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
                summary="Linux process namespace links are not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(
                _read_process_namespace_links_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read Linux process namespace links.",
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
                summary="Python runtime process namespace link read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G24_T03:
    id = "T03"
    title = "Read Linux service account secret files"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_service_account_secret_read,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read Linux service account secret file metadata.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux service account secret files were not present.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read Linux service account secret files.",
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
                summary="Shell service account secret file read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell service account secret file read failed.",
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
                summary="Linux service account secret files were not present.",
            )

        try:
            result = await asyncio.to_thread(
                _read_service_account_secret_metadata_with_python,
            )

            if result[0] == Outcome.ALLOWED:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime read Linux service account secret file "
                        "metadata."
                    ),
                    evidence=result[1],
                )

            if result[0] == Outcome.NOT_APPLICABLE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux service account secret files were not present.",
                    evidence=result[1],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not read Linux service account secret "
                    "files."
                ),
                evidence=result[1],
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
                summary="Python runtime service account secret file read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G24_T04:
    id = "T04"
    title = "Detect Linux mounted host paths and writable volumes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_mount_surface_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected Linux mount and volume surfaces.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux mount and volume surfaces are not applicable.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not detect Linux mount and volume surfaces.",
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
                summary="Shell mount surface detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell mount surface detection failed.",
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
                summary="Linux mount and volume surfaces are not applicable.",
            )

        try:
            evidence = await asyncio.to_thread(
                _detect_mount_surfaces_with_python,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime detected Linux mount and volume surfaces.",
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
                summary="Python runtime mount surface detection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G24_T05:
    id = "T05"
    title = "Access Linux container runtime Unix sockets"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_container_runtime_socket_access,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell accessed a Linux container runtime Unix socket.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux container runtime Unix sockets were not present.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not access Linux container runtime Unix sockets."
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
                summary="Shell container runtime socket access timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell container runtime socket access failed.",
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
                summary="Linux container runtime Unix sockets were not present.",
            )

        try:
            outcome, evidence = await asyncio.to_thread(
                _access_container_runtime_sockets_with_python,
            )

            if outcome == Outcome.ALLOWED:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime accessed a Linux container runtime Unix "
                        "socket."
                    ),
                    evidence=evidence,
                )

            if outcome == Outcome.NOT_APPLICABLE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Linux container runtime Unix sockets were not present.",
                    evidence=evidence,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not access Linux container runtime Unix "
                    "sockets."
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
                summary="Python runtime container runtime socket access failed.",
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
        id="G24",
        title="Namespace And Escape-Relevant Surfaces",
        tests=[
            G24_T01(capability_context),
            G24_T02(capability_context),
            G24_T03(capability_context),
            G24_T04(capability_context),
            G24_T05(capability_context),
        ],
    )


def _run_shell_surface_directory_listing(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux namespace surface directories are not applicable.",
        )

    return subprocess.run(
        _build_linux_surface_directory_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _run_shell_process_namespace_link_read(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux process namespace links are not applicable.",
        )

    return subprocess.run(
        _build_linux_process_namespace_link_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _run_shell_service_account_secret_read(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux service account secret files are not applicable.",
        )

    return subprocess.run(
        _build_linux_service_account_secret_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _run_shell_mount_surface_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux mount and volume surfaces are not applicable.",
        )

    return subprocess.run(
        _build_linux_mount_surface_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _run_shell_container_runtime_socket_access(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        return subprocess.CompletedProcess(
            args=[],
            returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="Linux container runtime Unix sockets are not applicable.",
        )

    return subprocess.run(
        _build_linux_container_runtime_socket_command(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_linux_surface_directory_command() -> list[str]:
    paths = " ".join(str(path) for path in _LINUX_SURFACE_DIRECTORIES)
    script = f"""
set -u
denied=0
evidence=""
for path in {paths}; do
    if [ ! -e "$path" ]; then
        evidence="${{evidence}}$path:missing;"
        continue
    fi
    if [ ! -d "$path" ]; then
        evidence="${{evidence}}$path:not_directory;"
        denied=1
        continue
    fi
    sample=$(ls -A "$path" 2>/dev/null | head -n 5 | paste -sd, -)
    status=$?
    if [ "$status" -eq 0 ]; then
        evidence="${{evidence}}$path:readable:sample=[$sample];"
    else
        evidence="${{evidence}}$path:denied;"
        denied=1
    fi
done
printf '%s\\n' "$evidence"
exit "$denied"
"""
    return ["sh", "-c", script]


def _build_linux_container_runtime_socket_command() -> list[str]:
    paths = " ".join(
        str(path)
        for path in _linux_container_runtime_socket_paths()
    )
    script = f"""
set -u
present=0
connected=0
denied=0
evidence=""
if command -v socat >/dev/null 2>&1; then
    client=socat
elif command -v nc >/dev/null 2>&1; then
    client=nc
else
    client=""
fi
for path in {paths}; do
    if [ ! -e "$path" ]; then
        continue
    fi
    if [ ! -S "$path" ]; then
        evidence="${{evidence}}$path:not_socket;"
        present=1
        denied=$((denied + 1))
        continue
    fi
    present=1
    if [ -z "$client" ]; then
        evidence="${{evidence}}$path:present:no_shell_socket_client;"
        continue
    fi
    if [ "$client" = "socat" ]; then
        timeout 2 sh -c "printf '' | socat - UNIX-CONNECT:'$path'" \
            >/dev/null 2>&1
        status=$?
    else
        timeout 2 nc -U -z "$path" >/dev/null 2>&1
        status=$?
    fi
    if [ "$status" -eq 0 ]; then
        connected=$((connected + 1))
        evidence="${{evidence}}$path:connected;"
    else
        denied=$((denied + 1))
        evidence="${{evidence}}$path:denied_or_unreachable:status=$status;"
    fi
done
if [ "$present" -eq 0 ]; then
    echo "present=False"
    exit 127
fi
printf 'present=True; connected_count=%s; denied_count=%s; sockets=[%s]\\n' \
    "$connected" \
    "$denied" \
    "$evidence"
if [ "$connected" -gt 0 ]; then
    exit 0
fi
if [ -z "$client" ]; then
    exit 127
fi
exit 1
"""
    return ["sh", "-c", script]


def _build_linux_mount_surface_command() -> list[str]:
    script = """
set -u
if [ ! -r /proc/self/mountinfo ]; then
    echo '/proc/self/mountinfo:unreadable'
    exit 1
fi
mount_count=$(wc -l < /proc/self/mountinfo)
rw_count=$(
    awk '{
        split($6, options, ",")
        for (i in options) {
            if (options[i] == "rw") {
                count += 1
                break
            }
        }
    } END { print count + 0 }' /proc/self/mountinfo
)
bind_like_count=$(
    awk '$0 ~ / - (overlay|9p|virtiofs|fuse|fuse\\.|nfs|cifs|drvfs|vboxsf|vmhgfs) / {
        count += 1
    } END { print count + 0 }' /proc/self/mountinfo
)
sample=$(awk '{
    separator = 0
    for (i = 1; i <= NF; i++) {
        if ($i == "-") {
            separator = i
            break
        }
    }
    if (separator > 0) {
        print $5 ":" $(separator + 1) ":" $(separator + 2) ":" $6
    }
}' /proc/self/mountinfo | head -n 8 | paste -sd, -)
printf 'mount_count=%s; rw_option_count=%s; bind_like_count=%s; sample=[%s]\\n' \
    "$mount_count" \
    "$rw_count" \
    "$bind_like_count" \
    "$sample"
"""
    return ["sh", "-c", script]


def _build_linux_service_account_secret_command() -> list[str]:
    paths = " ".join(str(path) for path in _LINUX_SERVICE_ACCOUNT_PATHS)
    script = f"""
set -u
present=0
readable=0
denied=0
evidence=""
for root in {paths}; do
    if [ ! -e "$root" ]; then
        continue
    fi
    present=1
    if [ -f "$root" ]; then
        size=$(wc -c < "$root" 2>/dev/null || true)
        if [ -n "$size" ]; then
            readable=$((readable + 1))
            evidence="${{evidence}}$root:file:size=$size;"
        else
            denied=$((denied + 1))
            evidence="${{evidence}}$root:file:denied;"
        fi
        continue
    fi
    if [ -d "$root" ]; then
        while IFS= read -r file; do
            [ -n "$file" ] || continue
            size=$(wc -c < "$file" 2>/dev/null || true)
            if [ -n "$size" ]; then
                readable=$((readable + 1))
                evidence="${{evidence}}$file:file:size=$size;"
            else
                denied=$((denied + 1))
                evidence="${{evidence}}$file:file:denied;"
            fi
        done <<EOF
$(find "$root" -maxdepth 3 -type f 2>/dev/null)
EOF
    fi
done
if [ "$present" -eq 0 ]; then
    echo "present=False"
    exit 127
fi
printf 'present=True; readable_count=%s; denied_count=%s; files=[%s]\\n' \\
    "$readable" \\
    "$denied" \\
    "$evidence"
if [ "$readable" -gt 0 ]; then
    exit 0
fi
exit 1
"""
    return ["sh", "-c", script]


def _build_linux_process_namespace_link_command() -> list[str]:
    script = """
set -u
if [ ! -d /proc/self/ns ]; then
    echo '/proc/self/ns:missing'
    exit 1
fi
evidence=""
for namespace in /proc/self/ns/*; do
    name=$(basename "$namespace")
    target=$(readlink "$namespace" 2>/dev/null || true)
    if [ -n "$target" ]; then
        evidence="${evidence}${name}:${target},"
    else
        evidence="${evidence}${name}:denied,"
        exit_code=1
    fi
done
printf '%s\\n' "$evidence"
exit "${exit_code:-0}"
"""
    return ["sh", "-c", script]


def _read_surface_directories_with_python() -> tuple[bool, str]:
    all_readable = True
    entries: list[str] = []

    for path in _LINUX_SURFACE_DIRECTORIES:
        if not path.exists():
            entries.append(f"{path}:missing")
            continue

        if not path.is_dir():
            entries.append(f"{path}:not_directory")
            all_readable = False
            continue

        try:
            sample = [
                child.name
                for child in list(path.iterdir())[:5]
            ]
            entries.append(f"{path}:readable:sample=[{','.join(sample)}]")
        except PermissionError:
            entries.append(f"{path}:denied")
            all_readable = False

    return all_readable, ";".join(entries)


def _read_process_namespace_links_with_python() -> str:
    if not _LINUX_PROCESS_NAMESPACE_DIRECTORY.exists():
        raise FileNotFoundError(_LINUX_PROCESS_NAMESPACE_DIRECTORY)

    entries: list[str] = []

    for path in sorted(_LINUX_PROCESS_NAMESPACE_DIRECTORY.iterdir()):
        target = path.readlink()
        entries.append(f"{path.name}:{target}")

    return ",".join(entries)


def _read_service_account_secret_metadata_with_python() -> tuple[Outcome, str]:
    candidates = _collect_service_account_secret_files()

    if not candidates:
        return Outcome.NOT_APPLICABLE, "present=False"

    readable_count = 0
    denied_count = 0
    entries: list[str] = []

    for path in candidates:
        try:
            size = path.stat().st_size
            readable_count += 1
            entries.append(f"{path}:file:size={size}")
        except PermissionError:
            denied_count += 1
            entries.append(f"{path}:file:denied")

    evidence = (
        "present=True; "
        f"readable_count={readable_count}; "
        f"denied_count={denied_count}; "
        f"files=[{';'.join(entries)}]"
    )

    if readable_count > 0:
        return Outcome.ALLOWED, evidence

    return Outcome.DENIED, evidence


def _detect_mount_surfaces_with_python() -> str:
    mounts = _read_linux_mountinfo()
    rw_option_count = 0
    writable_mountpoint_count = 0
    bind_like_mounts: list[dict[str, str]] = []

    for mount in mounts:
        options = mount["options"].split(",")

        if "rw" in options:
            rw_option_count += 1

        if os.access(mount["mount_point"], os.W_OK):
            writable_mountpoint_count += 1

        if _is_bind_like_mount(mount):
            bind_like_mounts.append(mount)

    sample_mounts = bind_like_mounts[:8]

    if not sample_mounts:
        sample_mounts = mounts[:8]

    sample = ",".join(
        (
            f"{mount['mount_point']}:{mount['filesystem_type']}:"
            f"{mount['mount_source']}:{mount['options']}"
        )
        for mount in sample_mounts
    )

    return (
        f"mount_count={len(mounts)}; "
        f"rw_option_count={rw_option_count}; "
        f"writable_mountpoint_count={writable_mountpoint_count}; "
        f"bind_like_count={len(bind_like_mounts)}; "
        f"sample=[{sample}]"
    )


def _read_linux_mountinfo() -> list[dict[str, str]]:
    mounts: list[dict[str, str]] = []

    with _LINUX_MOUNTINFO_PATH.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:
        for line in file:
            fields = line.strip().split()

            if "-" not in fields:
                continue

            separator_index = fields.index("-")

            if separator_index + 3 > len(fields):
                continue

            mount = {
                "mount_point": _decode_mountinfo_field(fields[4]),
                "options": fields[5],
                "filesystem_type": fields[separator_index + 1],
                "mount_source": _decode_mountinfo_field(
                    fields[separator_index + 2]
                ),
            }
            mounts.append(mount)

    return mounts


def _decode_mountinfo_field(value: str) -> str:
    return (
        value.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def _is_bind_like_mount(mount: dict[str, str]) -> bool:
    filesystem_type = mount["filesystem_type"]
    mount_source = mount["mount_source"]
    mount_point = mount["mount_point"]
    bind_like_filesystems = {
        "9p",
        "cifs",
        "drvfs",
        "fuse",
        "fuse.vmhgfs-fuse",
        "nfs",
        "overlay",
        "virtiofs",
        "vboxsf",
        "vmhgfs",
    }

    if filesystem_type in bind_like_filesystems:
        return True

    return (
        mount_source.startswith("/")
        and not mount_point.startswith("/proc")
        and not mount_point.startswith("/sys")
        and not mount_point.startswith("/dev")
    )


def _access_container_runtime_sockets_with_python() -> tuple[Outcome, str]:
    candidates = [
        path
        for path in _linux_container_runtime_socket_paths()
        if path.exists()
    ]

    if not candidates:
        return Outcome.NOT_APPLICABLE, "present=False"

    connected_count = 0
    denied_count = 0
    entries: list[str] = []

    for path in candidates:
        if not path.is_socket():
            denied_count += 1
            entries.append(f"{path}:not_socket")
            continue

        try:
            unix_socket_family = socket.AF_UNIX  # type: ignore[attr-defined]

            with socket.socket(unix_socket_family, socket.SOCK_STREAM) as client:
                client.settimeout(2)
                client.connect(str(path))

            connected_count += 1
            entries.append(f"{path}:connected")
        except OSError as error:
            denied_count += 1
            entries.append(
                f"{path}:denied_or_unreachable:{error.__class__.__name__}"
            )

    evidence = (
        "present=True; "
        f"connected_count={connected_count}; "
        f"denied_count={denied_count}; "
        f"sockets=[{';'.join(entries)}]"
    )

    if connected_count > 0:
        return Outcome.ALLOWED, evidence

    return Outcome.DENIED, evidence


def _linux_container_runtime_socket_paths() -> list[Path]:
    paths = list(_LINUX_CONTAINER_RUNTIME_SOCKET_PATHS)
    runtime_directory = os.environ.get("XDG_RUNTIME_DIR")

    if runtime_directory:
        paths.append(Path(runtime_directory) / "podman" / "podman.sock")
    else:
        getuid = os.getuid  # type: ignore[attr-defined]
        paths.append(Path("/run/user") / str(getuid()) / "podman/podman.sock")

    return paths


def _collect_service_account_secret_files() -> list[Path]:
    files: list[Path] = []

    for path in _LINUX_SERVICE_ACCOUNT_PATHS:
        if not path.exists():
            continue

        if path.is_file():
            files.append(path)
            continue

        if path.is_dir():
            files.extend(
                child
                for child in path.rglob("*")
                if child.is_file()
            )

    return sorted(set(files))


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
