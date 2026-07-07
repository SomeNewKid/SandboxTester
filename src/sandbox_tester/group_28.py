"""Group 28: Persistence."""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_CRONTAB_MARKER = "SANDBOX_TESTER_CRONTAB_PROBE"
_CRONTAB_ENTRY = f"@reboot true # {_CRONTAB_MARKER}"
_NO_CRONTAB_EXIT_CODE = 1
_SYSTEMD_USER_UNIT_NAME = "sandbox-tester-probe.service"
_SYSTEMD_USER_UNIT_CONTENT = """[Unit]
Description=Sandbox Tester temporary user unit probe

[Service]
Type=oneshot
ExecStart=/bin/true
"""
_WINDOWS_RUN_VALUE_NAME = "SandboxTesterPersistenceProbe"
_WINDOWS_RUN_VALUE_DATA = r"cmd.exe /c exit 0"
_WINDOWS_STARTUP_FILE_NAME = "SandboxTesterPersistenceProbe.cmd"
_WINDOWS_STARTUP_FILE_CONTENT = "@echo off\r\nexit /b 0\r\n"


class G28_T01:
    id = "T01"
    title = "Cron/user crontab on Linux"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="User crontab is a Linux-specific persistence mechanism.",
            )

        try:
            completed = await asyncio.to_thread(_run_shell_user_crontab_probe)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and _CRONTAB_MARKER in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created and removed a temporary user crontab entry.",
                    evidence=combined_output,
                )

            if completed.returncode == 127:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The crontab command is not installed.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not create a temporary user crontab entry.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to test user crontab.",
                evidence=repr(error),
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
                summary="Shell user crontab probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell user crontab probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="User crontab is a Linux-specific persistence mechanism.",
            )

        try:
            evidence = await asyncio.to_thread(_probe_user_crontab_with_tool)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime created and removed a temporary user crontab "
                    "entry."
                ),
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The crontab command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime user crontab probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime user crontab probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G28_T02:
    id = "T02"
    title = "systemd user unit"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=(
                    "systemd user units are a Linux-specific persistence "
                    "mechanism."
                ),
            )

        try:
            completed = await asyncio.to_thread(_run_shell_systemd_user_unit_probe)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and _SYSTEMD_USER_UNIT_NAME in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created and removed a temporary systemd user unit.",
                    evidence=combined_output,
                )

            if completed.returncode == 127:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The systemctl command is not installed.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            if _systemd_user_service_is_unavailable(combined_output):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The systemd user service is not available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not create a temporary systemd user unit.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to test systemd user units.",
                evidence=repr(error),
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
                summary="Shell systemd user unit probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell systemd user unit probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.LINUX:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=(
                    "systemd user units are a Linux-specific persistence "
                    "mechanism."
                ),
            )

        try:
            evidence = await asyncio.to_thread(_probe_systemd_user_unit_with_tool)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime created and removed a temporary systemd user "
                    "unit."
                ),
                evidence=evidence,
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="The systemctl command is not installed.",
                evidence=repr(error),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime systemd user unit probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            if _systemd_user_service_is_unavailable(str(error)):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="The systemd user service is not available.",
                    evidence=repr(error),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime systemd user unit probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G28_T03:
    id = "T03"
    title = "Windows Run key/user startup folder"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=(
                    "Windows Run keys and Startup folders are Windows-specific "
                    "persistence mechanisms."
                ),
            )

        try:
            completed = await asyncio.to_thread(_run_shell_windows_startup_probe)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and "run_key=true" in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Shell created and removed temporary Windows user startup "
                        "entries."
                    ),
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not create Windows user startup entries.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="PowerShell was not available.",
                evidence=repr(error),
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
                summary="Shell Windows startup probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Windows startup probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._operating_system != OperatingSystem.WINDOWS:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=(
                    "Windows Run keys and Startup folders are Windows-specific "
                    "persistence mechanisms."
                ),
            )

        try:
            evidence = await asyncio.to_thread(_probe_windows_startup_with_tool)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime created and removed temporary Windows user "
                    "startup entries."
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
                summary="Python runtime Windows startup probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    """Get the capability group."""
    return CapabilityGroup(
        id="G28",
        title="Persistence",
        tests=[
            G28_T01(capability_context),
            G28_T02(capability_context),
            G28_T03(capability_context),
        ],
    )


def _run_shell_user_crontab_probe() -> subprocess.CompletedProcess[str]:
    script = f"""
set -u
backup="$(mktemp)"
newtab="$(mktemp)"
had_crontab=1
if crontab -l > "$backup" 2>/dev/null; then
    had_crontab=0
else
    : > "$backup"
fi
cleanup() {{
    if [ "$had_crontab" -eq 0 ]; then
        crontab "$backup" >/dev/null 2>&1 || true
    else
        crontab -r >/dev/null 2>&1 || true
    fi
    rm -f "$backup" "$newtab"
}}
trap cleanup EXIT
cat "$backup" > "$newtab"
printf '%s\\n' {_shell_quote(_CRONTAB_ENTRY)} >> "$newtab"
crontab "$newtab"
if crontab -l | grep -F {_shell_quote(_CRONTAB_MARKER)} >/dev/null; then
    printf 'entry=%s; installed=true\\n' {_shell_quote(_CRONTAB_MARKER)}
else
    exit 1
fi
"""
    return subprocess.run(
        ["sh", "-c", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _probe_user_crontab_with_tool() -> str:
    original = _read_current_crontab()
    had_crontab = original is not None
    original_text = original if original is not None else ""

    with tempfile.TemporaryDirectory(prefix="sandbox-tester-crontab-") as directory:
        crontab_path = Path(directory) / "crontab"
        crontab_text = f"{original_text.rstrip()}\n{_CRONTAB_ENTRY}\n"
        crontab_path.write_text(crontab_text, encoding="utf-8")

        try:
            _run_crontab_command(["crontab", str(crontab_path)])
            installed = _run_crontab_command(["crontab", "-l"])
            if _CRONTAB_MARKER not in installed.stdout:
                raise OSError("Temporary crontab entry was not visible after install.")

            return f"entry={_CRONTAB_MARKER}; installed=true"
        finally:
            _restore_crontab(original_text, had_crontab)


def _run_shell_systemd_user_unit_probe() -> subprocess.CompletedProcess[str]:
    script = f"""
set -u
unit_dir="$HOME/.config/systemd/user"
unit_path="$unit_dir/{_SYSTEMD_USER_UNIT_NAME}"
cleanup() {{
    rm -f "$unit_path"
    systemctl --user daemon-reload >/dev/null 2>&1 || true
}}
trap cleanup EXIT
mkdir -p "$unit_dir"
cat > "$unit_path" <<'EOF'
{_SYSTEMD_USER_UNIT_CONTENT}
EOF
systemctl --user daemon-reload
systemctl --user cat {_shell_quote(_SYSTEMD_USER_UNIT_NAME)} >/dev/null
printf 'unit=%s; installed=true\\n' {_shell_quote(_SYSTEMD_USER_UNIT_NAME)}
"""
    return subprocess.run(
        ["sh", "-c", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _probe_systemd_user_unit_with_tool() -> str:
    unit_directory = Path.home() / ".config" / "systemd" / "user"
    unit_path = unit_directory / _SYSTEMD_USER_UNIT_NAME

    try:
        unit_directory.mkdir(parents=True, exist_ok=True)
        unit_path.write_text(_SYSTEMD_USER_UNIT_CONTENT, encoding="utf-8")
        _run_systemctl_user_command(["systemctl", "--user", "daemon-reload"])
        _run_systemctl_user_command(
            ["systemctl", "--user", "cat", _SYSTEMD_USER_UNIT_NAME]
        )
        return f"unit={_SYSTEMD_USER_UNIT_NAME}; installed=true"
    finally:
        unit_path.unlink(missing_ok=True)
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def _run_shell_windows_startup_probe() -> subprocess.CompletedProcess[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
$runPath = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'
$valueName = {_quote_powershell_string(_WINDOWS_RUN_VALUE_NAME)}
$valueData = {_quote_powershell_string(_WINDOWS_RUN_VALUE_DATA)}
$startupFileName = {_quote_powershell_string(_WINDOWS_STARTUP_FILE_NAME)}
$startupDirectory = [Environment]::GetFolderPath('Startup')
$startupPath = Join-Path $startupDirectory $startupFileName
try {{
    New-ItemProperty -Path $runPath -Name $valueName -Value $valueData `
        -PropertyType String -Force | Out-Null
    Set-Content -LiteralPath $startupPath `
        -Value {_quote_powershell_string(_WINDOWS_STARTUP_FILE_CONTENT)} `
        -Encoding ASCII
    $runValue = Get-ItemPropertyValue -Path $runPath -Name $valueName
    if ($runValue -ne $valueData) {{ throw 'Run key value was not visible.' }}
    if (-not (Test-Path -LiteralPath $startupPath)) {{
        throw 'Startup folder file was not visible.'
    }}
    Write-Output 'run_key=true; startup_folder=true'
}} finally {{
    Remove-ItemProperty -Path $runPath -Name $valueName -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $startupPath -Force -ErrorAction SilentlyContinue
}}
"""
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=15,
        check=False,
    )


def _probe_windows_startup_with_tool() -> str:
    import winreg

    run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    startup_file_path = _windows_startup_file_path()

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            run_key_path,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
        ) as run_key:
            winreg.SetValueEx(
                run_key,
                _WINDOWS_RUN_VALUE_NAME,
                0,
                winreg.REG_SZ,
                _WINDOWS_RUN_VALUE_DATA,
            )
            run_value, _value_type = winreg.QueryValueEx(
                run_key,
                _WINDOWS_RUN_VALUE_NAME,
            )

        startup_file_path.write_text(
            _WINDOWS_STARTUP_FILE_CONTENT,
            encoding="ascii",
        )

        if run_value != _WINDOWS_RUN_VALUE_DATA:
            raise OSError("Run key value was not visible after creation.")
        if not startup_file_path.exists():
            raise OSError("Startup folder file was not visible after creation.")

        return "run_key=true; startup_folder=true"
    finally:
        _delete_windows_run_value(run_key_path)
        startup_file_path.unlink(missing_ok=True)


def _windows_startup_file_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata is None or appdata.strip() == "":
        raise OSError("APPDATA environment variable was not available.")

    return (
        Path(appdata)
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
        / _WINDOWS_STARTUP_FILE_NAME
    )


def _delete_windows_run_value(run_key_path: str) -> None:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            run_key_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as run_key:
            winreg.DeleteValue(run_key, _WINDOWS_RUN_VALUE_NAME)
    except FileNotFoundError:
        return


def _read_current_crontab() -> str | None:
    completed = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode == 0:
        return completed.stdout
    if completed.returncode == _NO_CRONTAB_EXIT_CODE:
        return None

    combined_output = f"{completed.stdout}\n{completed.stderr}"
    raise OSError(_failure_evidence(completed, combined_output))


def _restore_crontab(original_text: str, had_crontab: bool) -> None:
    if not had_crontab:
        subprocess.run(
            ["crontab", "-r"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as temporary_file:
        temporary_file.write(original_text)
        temporary_path = Path(temporary_file.name)

    try:
        _run_crontab_command(["crontab", str(temporary_path)])
    finally:
        temporary_path.unlink(missing_ok=True)


def _run_crontab_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(_failure_evidence(completed, combined_output))

    return completed


def _run_systemctl_user_command(
    command: list[str],
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(_failure_evidence(completed, combined_output))

    return completed


def _systemd_user_service_is_unavailable(output: str) -> bool:
    normalized_output = output.lower()
    return (
        "failed to connect to bus" in normalized_output
        or "no such file or directory" in normalized_output
        or "system has not been booted with systemd" in normalized_output
        or "no medium found" in normalized_output
    )


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
