"""Group 27: Code Loading And Execution."""

from __future__ import annotations

import asyncio
import ctypes
import importlib.util
import shlex
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_RUNTIME_MODULE_SENTINEL = "sandbox-tester-runtime-import"


class G27_T01:
    id = "T12"
    title = "Load system native library"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_native_library_load,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell loaded a system native library.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not load a system native library.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to load a native library.",
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
                summary="Shell native library load timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell native library load failed.",
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
                _load_system_native_library_with_python,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime loaded a system native library.",
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
                summary="Python runtime native library load failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G27_T02:
    id = "T13"
    title = "Create and import Python module in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        module_name = _runtime_module_name()
        module_path = self._allowed_directory / f"{module_name}.py"

        try:
            completed = await asyncio.to_thread(
                _run_shell_create_and_import_python_module,
                self._operating_system,
                module_path,
                module_name,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if (
                completed.returncode == 0
                and f"value={_RUNTIME_MODULE_SENTINEL}" in combined_output
            ):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created and imported a Python module.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not create and import a Python module.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to create a Python module.",
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
                summary="Shell runtime module import timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell runtime module import failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            _delete_runtime_module_artifacts(module_path)

    async def run_tool(self) -> InvocationResult:
        module_name = _runtime_module_name()
        module_path = self._allowed_directory / f"{module_name}.py"

        try:
            evidence = await asyncio.to_thread(
                _create_and_import_python_module_with_tool,
                module_path,
                module_name,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime created and imported a Python module.",
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
                summary="Python runtime module import failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            _delete_runtime_module_artifacts(module_path)


class G27_T03:
    id = "T14"
    title = "Call OS API with ctypes"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_os_api_call,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and "process_id=" in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell called an operating system API.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not call an operating system API.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to call an OS API.",
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
                summary="Shell OS API call timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell OS API call failed.",
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
                _call_os_api_with_ctypes,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime called an operating system API with ctypes.",
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
                summary="Python runtime OS API call failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )


class G27_T04:
    id = "T15"
    title = "Spawn PowerShell with constrained-language detection"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_powershell_language_mode_detection,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and "language_mode=" in combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell spawned PowerShell and detected language mode.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not spawn PowerShell and detect language mode.",
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
                summary="PowerShell language mode detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="PowerShell language mode detection failed.",
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
                _detect_powershell_language_mode_with_tool,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime spawned PowerShell and detected language mode.",
                evidence=evidence,
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
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="PowerShell language mode detection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="PowerShell language mode detection failed.",
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
        id="G27",
        title="Code Loading And Execution",
        tests=[],
    )


def _run_shell_native_library_load(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    command = _build_shell_native_library_load_command(operating_system)
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _build_shell_native_library_load_command(
    operating_system: OperatingSystem,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        script = """
$ErrorActionPreference = 'Stop'
$definition = @'
[System.Runtime.InteropServices.DllImport(
    "kernel32.dll",
    CharSet=System.Runtime.InteropServices.CharSet.Unicode,
    SetLastError=true)]
public static extern System.IntPtr LoadLibrary(string lpFileName);
'@
Add-Type -Namespace SandboxTester -Name NativeLoader -MemberDefinition $definition
$handle = [SandboxTester.NativeLoader]::LoadLibrary('kernel32.dll')
if ($handle -eq [System.IntPtr]::Zero) { exit 1 }
Write-Output 'library=kernel32.dll; loaded=true'
"""
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    script = (
        "import ctypes; "
        "ctypes.CDLL('libc.so.6'); "
        "print('library=libc.so.6; loaded=true')"
    )
    return ["python3", "-c", script]


def _load_system_native_library_with_python(
    operating_system: OperatingSystem,
) -> str:
    library_name = _system_library_name(operating_system)
    ctypes.CDLL(library_name)
    return f"library={library_name}; loaded=true"


def _run_shell_create_and_import_python_module(
    operating_system: OperatingSystem,
    module_path: Path,
    module_name: str,
) -> subprocess.CompletedProcess[str]:
    command = _build_shell_create_and_import_python_module_command(
        operating_system,
        module_path,
        module_name,
    )
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _build_shell_create_and_import_python_module_command(
    operating_system: OperatingSystem,
    module_path: Path,
    module_name: str,
) -> list[str]:
    module_content = _runtime_module_content()
    import_script = _runtime_module_import_script(module_path, module_name)

    if operating_system == OperatingSystem.WINDOWS:
        script = (
            "$ErrorActionPreference = 'Stop'; "
            f"$modulePath = {_quote_powershell_string(str(module_path))}; "
            f"$moduleContent = {_quote_powershell_string(module_content)}; "
            "Set-Content -LiteralPath $modulePath -Value $moduleContent "
            "-Encoding UTF8; "
            f"& {_quote_powershell_string(sys.executable)} "
            f"-c {_quote_powershell_string(import_script)}"
        )
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    script = (
        f"printf %s {shlex.quote(module_content)} > "
        f"{shlex.quote(str(module_path))} && "
        f"{shlex.quote(sys.executable)} -c {shlex.quote(import_script)}"
    )
    return ["sh", "-c", script]


def _create_and_import_python_module_with_tool(
    module_path: Path,
    module_name: str,
) -> str:
    module_path.write_text(_runtime_module_content(), encoding="utf-8")
    module = _import_python_module_from_path(module_path, module_name)
    value = module.VALUE

    if value != _RUNTIME_MODULE_SENTINEL:
        raise RuntimeError(f"Unexpected module value: {value!r}")

    return f"module={module_name}; path={module_path}; value={value}"


def _run_shell_os_api_call(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    command = _build_shell_os_api_call_command(operating_system)
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _build_shell_os_api_call_command(
    operating_system: OperatingSystem,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        script = """
$ErrorActionPreference = 'Stop'
$definition = @'
[System.Runtime.InteropServices.DllImport("kernel32.dll")]
public static extern uint GetCurrentProcessId();
'@
Add-Type -Namespace SandboxTester -Name ProcessApi -MemberDefinition $definition
$processId = [SandboxTester.ProcessApi]::GetCurrentProcessId()
Write-Output "api=GetCurrentProcessId; process_id=$processId"
"""
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    script = (
        "import ctypes; "
        "libc = ctypes.CDLL('libc.so.6'); "
        "libc.getpid.restype = ctypes.c_int; "
        "print(f'api=getpid; process_id={libc.getpid()}')"
    )
    return ["python3", "-c", script]


def _call_os_api_with_ctypes(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        process_id = ctypes.windll.kernel32.GetCurrentProcessId()
        return f"api=GetCurrentProcessId; process_id={process_id}"

    libc = ctypes.CDLL("libc.so.6")
    libc.getpid.restype = ctypes.c_int
    process_id = libc.getpid()
    return f"api=getpid; process_id={process_id}"


def _run_shell_powershell_language_mode_detection(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    command = _powershell_language_mode_command(operating_system)
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _detect_powershell_language_mode_with_tool(
    operating_system: OperatingSystem,
) -> str:
    completed = _run_shell_powershell_language_mode_detection(operating_system)
    combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

    if completed.returncode != 0:
        raise OSError(_failure_evidence(completed, combined_output))

    return combined_output


def _powershell_language_mode_command(
    operating_system: OperatingSystem,
) -> list[str]:
    executable = "powershell"
    if operating_system == OperatingSystem.LINUX:
        executable = _available_powershell_executable()

    script = (
        "$mode = $ExecutionContext.SessionState.LanguageMode; "
        'Write-Output "language_mode=$mode"'
    )
    return [executable, "-NoProfile", "-NonInteractive", "-Command", script]


def _available_powershell_executable() -> str:
    for candidate in ["pwsh", "powershell"]:
        if shutil.which(candidate) is not None:
            return candidate

    raise FileNotFoundError("No PowerShell executable was found.")


def _import_python_module_from_path(
    module_path: Path,
    module_name: str,
) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not create import spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_module_name() -> str:
    return f"sandbox_runtime_module_{uuid.uuid4().hex}"


def _runtime_module_content() -> str:
    return f'VALUE = "{_RUNTIME_MODULE_SENTINEL}"\n'


def _runtime_module_import_script(module_path: Path, module_name: str) -> str:
    path_text = str(module_path)
    return (
        "import importlib.util; "
        f"module_name = {module_name!r}; "
        f"path = {path_text!r}; "
        "spec = importlib.util.spec_from_file_location(module_name, path); "
        "module = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(module); "
        "print('module=' + module_name + '; path=' + path + '; value=' + "
        "module.VALUE)"
    )


def _delete_runtime_module_artifacts(module_path: Path) -> None:
    module_path.unlink(missing_ok=True)

    cache_directory = module_path.parent / "__pycache__"
    if cache_directory.exists():
        shutil.rmtree(cache_directory, ignore_errors=True)


def _system_library_name(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "kernel32.dll"

    return "libc.so.6"


def _quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
