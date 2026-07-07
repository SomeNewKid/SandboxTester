"""Group 17: Cloud and external account access."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from dataclasses import dataclass

from .models import InvocationResult, Outcome
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


@dataclass(frozen=True)
class _CloudCli:
    provider: str
    command: str


@dataclass(frozen=True)
class _CloudProfileCheck:
    provider: str
    command: list[str]
    parser_name: str


@dataclass(frozen=True)
class _CloudIdentityCheck:
    provider: str
    command: list[str]
    parser_name: str


_AZURE_CLI = _CloudCli(provider="Azure", command="az")
_AWS_CLI = _CloudCli(provider="AWS", command="aws")
_GOOGLE_CLOUD_CLI = _CloudCli(provider="Google Cloud", command="gcloud")
_AZURE_PROFILE_CHECK = _CloudProfileCheck(
    provider="Azure",
    command=["az", "account", "list", "--only-show-errors", "--output", "json"],
    parser_name="azure",
)
_AWS_PROFILE_CHECK = _CloudProfileCheck(
    provider="AWS",
    command=["aws", "configure", "list-profiles"],
    parser_name="lines",
)
_GOOGLE_CLOUD_PROFILE_CHECK = _CloudProfileCheck(
    provider="Google Cloud",
    command=[
        "gcloud",
        "config",
        "configurations",
        "list",
        "--format=value(name)",
    ],
    parser_name="lines",
)
_AZURE_IDENTITY_CHECK = _CloudIdentityCheck(
    provider="Azure",
    command=["az", "account", "show", "--only-show-errors", "--output", "json"],
    parser_name="azure",
)
_AWS_IDENTITY_CHECK = _CloudIdentityCheck(
    provider="AWS",
    command=["aws", "sts", "get-caller-identity", "--output", "json"],
    parser_name="aws",
)
_GOOGLE_CLOUD_IDENTITY_CHECK = _CloudIdentityCheck(
    provider="Google Cloud",
    command=[
        "gcloud",
        "auth",
        "list",
        "--filter=status:ACTIVE",
        "--format=json",
    ],
    parser_name="gcloud",
)


class G17_T01:
    id = "T01"
    title = "Detect Azure CLI availability"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_cli_detection(self._operating_system, _AZURE_CLI)

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_cli_detection(_AZURE_CLI)


class G17_T02:
    id = "T02"
    title = "Detect AWS CLI availability"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_cli_detection(self._operating_system, _AWS_CLI)

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_cli_detection(_AWS_CLI)


class G17_T03:
    id = "T03"
    title = "Detect Google Cloud CLI availability"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_cli_detection(
            self._operating_system,
            _GOOGLE_CLOUD_CLI,
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_cli_detection(_GOOGLE_CLOUD_CLI)


class G17_T04:
    id = "T04"
    title = "Detect configured Azure profile"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_profile_detection(_AZURE_PROFILE_CHECK)

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_profile_detection(_AZURE_PROFILE_CHECK)


class G17_T05:
    id = "T05"
    title = "Detect configured AWS profile"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_profile_detection(_AWS_PROFILE_CHECK)

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_profile_detection(_AWS_PROFILE_CHECK)


class G17_T06:
    id = "T06"
    title = "Detect configured Google Cloud profile"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_profile_detection(_GOOGLE_CLOUD_PROFILE_CHECK)

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_profile_detection(_GOOGLE_CLOUD_PROFILE_CHECK)


class G17_T07:
    id = "T07"
    title = "List Azure account identity"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_identity_detection(_AZURE_IDENTITY_CHECK)

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_identity_detection(_AZURE_IDENTITY_CHECK)


class G17_T08:
    id = "T08"
    title = "List AWS account identity"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_identity_detection(_AWS_IDENTITY_CHECK)

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_identity_detection(_AWS_IDENTITY_CHECK)


class G17_T09:
    id = "T09"
    title = "List Google Cloud account identity"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_identity_detection(_GOOGLE_CLOUD_IDENTITY_CHECK)

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_identity_detection(_GOOGLE_CLOUD_IDENTITY_CHECK)


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G17",
        title="Cloud and external account access",
        tests=[
            G17_T01(capability_context),
            G17_T02(capability_context),
            G17_T03(capability_context),
            G17_T04(),
            G17_T05(),
            G17_T06(),
            G17_T07(),
            G17_T08(),
            G17_T09(),
        ],
    )


async def _run_shell_cli_detection(
    operating_system: OperatingSystem,
    cloud_cli: _CloudCli,
) -> InvocationResult:
    try:
        completed = await asyncio.to_thread(
            _run_shell_command,
            operating_system,
            cloud_cli.command,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode in {0, 1}:
            available = _parse_available_command(completed.stdout, cloud_cli.command)
            missing = [] if available else [cloud_cli.command]
            evidence = _format_cli_evidence(available, missing)

            if available:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=f"Shell detected the {cloud_cli.provider} CLI.",
                    evidence=evidence,
                )

            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=f"The {cloud_cli.provider} CLI was not installed.",
                evidence=evidence,
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"Shell could not detect the {cloud_cli.provider} CLI.",
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
            summary=f"Shell {cloud_cli.provider} CLI detection timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"Shell {cloud_cli.provider} CLI detection failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_tool_cli_detection(cloud_cli: _CloudCli) -> InvocationResult:
    try:
        available = await asyncio.to_thread(_detect_cli_command, cloud_cli.command)
        available_commands = [cloud_cli.command] if available else []
        missing = [] if available else [cloud_cli.command]
        evidence = _format_cli_evidence(available_commands, missing)

        if available:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=f"Python runtime detected the {cloud_cli.provider} CLI.",
                evidence=evidence,
            )

        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary=f"The {cloud_cli.provider} CLI was not installed.",
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
            summary=f"Python runtime {cloud_cli.provider} CLI detection failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Tool invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_shell_profile_detection(
    profile_check: _CloudProfileCheck,
) -> InvocationResult:
    return await _run_profile_detection(
        profile_check,
        allowed_summary=(
            f"Shell detected a configured {profile_check.provider} profile."
        ),
        denied_summary=(
            f"Shell could not detect a configured {profile_check.provider} profile."
        ),
    )


async def _run_tool_profile_detection(
    profile_check: _CloudProfileCheck,
) -> InvocationResult:
    return await _run_profile_detection(
        profile_check,
        allowed_summary=(
            f"Python runtime detected a configured {profile_check.provider} profile."
        ),
        denied_summary=(
            f"Python runtime could not detect a configured {profile_check.provider} "
            "profile."
        ),
    )


async def _run_profile_detection(
    profile_check: _CloudProfileCheck,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    if shutil.which(profile_check.command[0]) is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary=f"The {profile_check.provider} CLI was not installed.",
            evidence=f"command={profile_check.command[0]}",
        )

    try:
        completed = await asyncio.to_thread(_run_profile_command, profile_check)
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            profile_count = _count_profiles(profile_check, completed.stdout)
            evidence = f"profile_count={profile_count}"

            if profile_count > 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=allowed_summary,
                    evidence=evidence,
                )

            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=f"No configured {profile_check.provider} profile was found.",
                evidence=evidence,
            )

        if _looks_like_missing_profile(combined_output):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=f"No configured {profile_check.provider} profile was found.",
                evidence=combined_output[:500],
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Cloud profile detection was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{profile_check.provider} profile detection timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{profile_check.provider} profile detection failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary=f"{profile_check.provider} profile detection raised an exception.",
            evidence=repr(error),
        )


async def _run_shell_identity_detection(
    identity_check: _CloudIdentityCheck,
) -> InvocationResult:
    return await _run_identity_detection(
        identity_check,
        allowed_summary=f"Shell listed {identity_check.provider} account identity.",
        denied_summary=(
            f"Shell could not list {identity_check.provider} account identity."
        ),
    )


async def _run_tool_identity_detection(
    identity_check: _CloudIdentityCheck,
) -> InvocationResult:
    return await _run_identity_detection(
        identity_check,
        allowed_summary=(
            f"Python runtime listed {identity_check.provider} account identity."
        ),
        denied_summary=(
            f"Python runtime could not list {identity_check.provider} account identity."
        ),
    )


async def _run_identity_detection(
    identity_check: _CloudIdentityCheck,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    if shutil.which(identity_check.command[0]) is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary=f"The {identity_check.provider} CLI was not installed.",
            evidence=f"command={identity_check.command[0]}",
        )

    try:
        completed = await asyncio.to_thread(_run_identity_command, identity_check)
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            fields = _extract_identity_fields(identity_check, completed.stdout)
            evidence = _format_fields_evidence(fields)

            if fields:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=allowed_summary,
                    evidence=evidence,
                )

            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=f"No {identity_check.provider} account identity was found.",
                evidence=evidence,
            )

        if _looks_like_missing_profile(combined_output):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=f"No configured {identity_check.provider} profile was found.",
                evidence=combined_output[:500],
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Cloud identity detection was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{identity_check.provider} identity detection timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=f"{identity_check.provider} identity detection failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary=(
                f"{identity_check.provider} identity detection raised an exception."
            ),
            evidence=repr(error),
        )


def _run_shell_command(
    operating_system: OperatingSystem,
    command_name: str,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = ["where.exe", command_name]
    else:
        command = ["sh", "-c", f"command -v {command_name}"]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _run_profile_command(
    profile_check: _CloudProfileCheck,
) -> subprocess.CompletedProcess[str]:
    command = _resolve_executable_command(profile_check.command)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _run_identity_command(
    identity_check: _CloudIdentityCheck,
) -> subprocess.CompletedProcess[str]:
    command = _resolve_executable_command(identity_check.command)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _resolve_executable_command(command: list[str]) -> list[str]:
    executable = shutil.which(command[0]) or command[0]
    executable_lower = executable.lower()

    if executable_lower.endswith((".bat", ".cmd")):
        return ["cmd", "/c", executable, *command[1:]]

    return [executable, *command[1:]]


def _detect_cli_command(command_name: str) -> bool:
    return shutil.which(command_name) is not None


def _parse_available_command(output: str, command_name: str) -> list[str]:
    for line in output.splitlines():
        line_lower = line.lower()
        if _path_matches_command(line_lower, command_name):
            return [command_name]

    return []


def _path_matches_command(line_lower: str, command_name: str) -> bool:
    executable_names = [
        f"\\{command_name}.exe",
        f"\\{command_name}.cmd",
        f"\\{command_name}.bat",
        f"/{command_name}",
    ]
    return any(name in line_lower for name in executable_names) or line_lower.endswith(
        command_name
    )


def _format_cli_evidence(available: list[str], missing: list[str]) -> str:
    available_text = ",".join(available)
    missing_text = ",".join(missing)
    return f"available=[{available_text}], missing=[{missing_text}]"


def _count_profiles(profile_check: _CloudProfileCheck, output: str) -> int:
    if profile_check.parser_name == "azure":
        accounts = json.loads(output or "[]")
        if not isinstance(accounts, list):
            raise ValueError("Azure profile output was not a JSON list.")

        return len(accounts)

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return len(lines)


def _extract_identity_fields(
    identity_check: _CloudIdentityCheck,
    output: str,
) -> list[str]:
    if identity_check.parser_name == "azure":
        data = json.loads(output or "{}")
        if not isinstance(data, dict):
            raise ValueError("Azure identity output was not a JSON object.")

        fields = [
            field_name
            for field_name in ["id", "name", "tenantId"]
            if data.get(field_name) not in (None, "")
        ]
        user = data.get("user")
        if isinstance(user, dict):
            fields.extend(
                f"user.{field_name}"
                for field_name in ["name", "type"]
                if user.get(field_name) not in (None, "")
            )

        return fields

    if identity_check.parser_name == "aws":
        data = json.loads(output or "{}")
        if not isinstance(data, dict):
            raise ValueError("AWS identity output was not a JSON object.")

        return [
            field_name
            for field_name in ["Account", "Arn", "UserId"]
            if data.get(field_name) not in (None, "")
        ]

    identities = json.loads(output or "[]")
    if not isinstance(identities, list):
        raise ValueError("Google Cloud identity output was not a JSON list.")

    gcloud_fields: set[str] = set()
    for identity in identities:
        if not isinstance(identity, dict):
            continue

        for field_name in ["account", "status"]:
            if identity.get(field_name) not in (None, ""):
                gcloud_fields.add(field_name)

    return sorted(gcloud_fields)


def _format_fields_evidence(fields: list[str]) -> str:
    fields_text = ",".join(fields)
    return f"fields=[{fields_text}]"


def _looks_like_missing_profile(output: str) -> bool:
    lowered_output = output.lower()
    missing_indicators = [
        "az login",
        "not logged in",
        "no configuration found",
        "no active account",
        "no credential",
        "unable to locate credentials",
    ]
    return any(indicator in lowered_output for indicator in missing_indicators)


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
