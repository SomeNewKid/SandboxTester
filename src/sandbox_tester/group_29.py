"""Group 29: AI-Agent Specific But Still Sandbox-Relevant."""

from __future__ import annotations

import asyncio
import os
import subprocess

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_AI_CREDENTIAL_ENVIRONMENT_VARIABLES = [
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "COHERE_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "HUGGINGFACE_API_TOKEN",
    "HF_TOKEN",
]


class G29_T01:
    id = "T05"
    title = "Access model/API credentials in environment/config"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_shell_ai_credential_environment_probe,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode != 0:
                return InvocationResult(
                    outcome=Outcome.DENIED,
                    summary="Shell could not inspect AI credential environment names.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            if combined_output:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell detected AI credential environment variables.",
                    evidence=combined_output,
                )

            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No known AI credential environment variables were present.",
            )
        except FileNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell command was available to inspect the environment.",
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
                summary="Shell AI credential environment probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell AI credential environment probe failed.",
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
            credential_names = await asyncio.to_thread(
                _find_ai_credential_environment_names
            )

            if credential_names:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime detected AI credential environment variables."
                    ),
                    evidence=_credential_name_evidence(credential_names),
                )

            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No known AI credential environment variables were present.",
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
                summary="Python runtime AI credential environment probe failed.",
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
        id="G29",
        title="AI-Agent Specific But Still Sandbox-Relevant",
        tests=[],
    )


def _run_shell_ai_credential_environment_probe(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    command = _build_shell_ai_credential_environment_command(operating_system)
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=10,
        check=False,
    )


def _build_shell_ai_credential_environment_command(
    operating_system: OperatingSystem,
) -> list[str]:
    if operating_system == OperatingSystem.WINDOWS:
        names = ", ".join(
            _quote_powershell_string(name)
            for name in _AI_CREDENTIAL_ENVIRONMENT_VARIABLES
        )
        script = (
            f"$names = @({names}); "
            "$present = @(); "
            "foreach ($name in $names) { "
            'if (Test-Path "Env:$name") { $present += $name } '
            "} "
            "if ($present.Count -gt 0) { "
            "Write-Output ('names=' + ($present -join ',')) "
            "}"
        )
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    checks = []
    for name in _AI_CREDENTIAL_ENVIRONMENT_VARIABLES:
        quoted_name = _shell_quote(name)
        checks.append(
            f"if printenv {quoted_name} >/dev/null 2>&1; "
            f"then printf '%s\\n' {quoted_name}; fi"
        )
    script = "\n".join(checks)
    script = (
        f'present=$({script}); [ -n "$present" ] && printf \'names=%s\\n\' "$present"'
    )
    return ["sh", "-c", script]


def _find_ai_credential_environment_names() -> list[str]:
    return [name for name in _AI_CREDENTIAL_ENVIRONMENT_VARIABLES if name in os.environ]


def _credential_name_evidence(credential_names: list[str]) -> str:
    return f"names={','.join(credential_names)}"


def _quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
