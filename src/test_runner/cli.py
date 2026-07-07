"""Command-line interface for the application."""

from __future__ import annotations

import asyncio
import dataclasses
import datetime as dt
import json
import os
from pathlib import Path

from sandbox_tester.manager import run_all_groups
from sandbox_tester.models import CapabilityGroupResult
from sandbox_tester.reporter import ConsoleReporter, QuietReporter
from sandbox_tester.testing import (
    CapabilityContext,
    create_allowed_directory,
    create_disallowed_directory,
    delete_allowed_directory,
    delete_denied_directory,
)
from sandbox_tester.utilities import render_markdown_report

VERBOSE_LOGGING = False
DELETE_SCRATCH_DIRECTORIES = True
SAVE_REPORT_TO_JSON = True
PRINT_MARKDOWN_REPORT = True
MOUNTED_SHARED_DIRECTORY = Path("S:/")
ALLOWED_DOMAIN = "example.com"
DENIED_DOMAIN = "example.net"
ALLOWED_LOCAL_ADDRESS = None
DENIED_LOCAL_ADDRESS = None
ALLOWED_LOCALNET_ADDRESS = None
DENIED_LOCALNET_ADDRESS = None
ALLOWED_INTRANET_TARGET = None
DENIED_INTRANET_TARGET = "192.168.86.28"
ALLOWED_DATABASE_ADDRESS = None
DENIED_DATABASE_ADDRESS = None
CONTAINER_RUNTIME_SOCKET = None
LOCAL_DEV_SERVER_URL = None
LOCAL_MODEL_SERVER_URL = None
METADATA_ENDPOINT_URL = None
DNS_EXFILTRATION_DOMAIN = "c2FuZGJveC10ZXN0ZXI.example.com"
HTTP_EXFILTRATION_DOMAIN = "example.com"
HTTP_EXFILTRATION_HEADER = "exfiltration=example"
WEBSOCKET_EXFILTRATION_URL = "wss://echo.websocket.org"
SMTP_EXFILTRATION_URL = None
SSH_AGENT_SOCKET = os.environ.get("SSH_AUTH_SOCK")
BROWSER_DEBUGGING_URL = None
BROWSER_EXECUTABLE = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
EXISTING_BROWSER_PROFILE = Path(
    r"C:\Users\somen\AppData\Local\Google\Chrome\User Data\Default"
)
ALLOWED_GIT_REPOSITORY = Path(r"C:\Git\ScratchpadOne")
DENIED_GIT_REPOSITORY = Path(r"C:\Git\ScratchpadTwo")
GIT_REMOTE_URL = "https://github.com/SomeNewKid/ScratchpadOne.git"
ALLOW_CAMERA_CAPTURE = True
ALLOW_MICROPHONE_CAPTURE = True


def main() -> int:
    """Run the command-line interface."""
    allowed_directory = create_allowed_directory()
    denied_directory = create_disallowed_directory()
    capability_context = CapabilityContext.from_current_environment(
        working_directory=Path.cwd(),
        allowed_directory=allowed_directory,
        denied_directory=denied_directory,
        mounted_shared_directory=MOUNTED_SHARED_DIRECTORY,
        allowed_domain=ALLOWED_DOMAIN,
        denied_domain=DENIED_DOMAIN,
        allowed_local_address=ALLOWED_LOCAL_ADDRESS,
        denied_local_address=DENIED_LOCAL_ADDRESS,
        allowed_localnet_address=ALLOWED_LOCALNET_ADDRESS,
        denied_localnet_address=DENIED_LOCALNET_ADDRESS,
        allowed_intranet_target=ALLOWED_INTRANET_TARGET,
        denied_intranet_target=DENIED_INTRANET_TARGET,
        allowed_database_address=ALLOWED_DATABASE_ADDRESS,
        denied_database_address=DENIED_DATABASE_ADDRESS,
        container_runtime_socket=CONTAINER_RUNTIME_SOCKET,
        local_dev_server_url=LOCAL_DEV_SERVER_URL,
        local_model_server_url=LOCAL_MODEL_SERVER_URL,
        metadata_endpoint_url=METADATA_ENDPOINT_URL,
        dns_exfiltration_domain=DNS_EXFILTRATION_DOMAIN,
        http_exfiltration_domain=HTTP_EXFILTRATION_DOMAIN,
        http_exfiltration_header=HTTP_EXFILTRATION_HEADER,
        websocket_exfiltration_url=WEBSOCKET_EXFILTRATION_URL,
        smtp_exfiltration_url=SMTP_EXFILTRATION_URL,
        ssh_agent_socket=SSH_AGENT_SOCKET,
        browser_debugging_url=BROWSER_DEBUGGING_URL,
        browser_executable=BROWSER_EXECUTABLE,
        existing_browser_profile=EXISTING_BROWSER_PROFILE,
        allowed_git_repository=ALLOWED_GIT_REPOSITORY,
        denied_git_repository=DENIED_GIT_REPOSITORY,
        git_remote_url=GIT_REMOTE_URL,
        allow_camera_capture=ALLOW_CAMERA_CAPTURE,
        allow_microphone_capture=ALLOW_MICROPHONE_CAPTURE,
    )

    reporter = ConsoleReporter() if VERBOSE_LOGGING else QuietReporter()
    results = asyncio.run(run_all_groups(capability_context, reporter))
    if SAVE_REPORT_TO_JSON:
        report_path = _save_report_to_json(Path.cwd(), results)
        print(f"JSON report saved to: {report_path}")

    if results:
        if PRINT_MARKDOWN_REPORT:
            markdown = render_markdown_report(results)
            print()
            print("-" * 40)
            print()
            print(markdown)
        else:
            print("Markdown report not printed.")
    else:
        print("No results.")

    if DELETE_SCRATCH_DIRECTORIES:
        delete_allowed_directory(allowed_directory)
        delete_denied_directory(denied_directory)
    else:
        print(f"Allowed directory retained at: {allowed_directory}")
        print(f"Denied directory retained at: {denied_directory}")
    return 0


def _save_report_to_json(
    working_directory: Path,
    results: list[CapabilityGroupResult],
) -> Path:
    reports_directory = working_directory / ".reports"
    reports_directory.mkdir(parents=True, exist_ok=True)

    timestamp = dt.datetime.now().strftime("%Y-%m-%d-%H-%M")
    report_path = reports_directory / f"report-{timestamp}.json"
    report_data = [dataclasses.asdict(result) for result in results]
    report_json = json.dumps(report_data, indent=2)
    report_path.write_text(f"{report_json}\n", encoding="utf-8")

    return report_path
