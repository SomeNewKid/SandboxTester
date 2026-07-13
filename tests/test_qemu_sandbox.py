"""Tests for the QEMU sandbox harness."""

from __future__ import annotations

from pathlib import Path

from qemu_sandbox.credentials import load_or_create_guest_credentials
from qemu_sandbox.models import (
    GuestCredentials,
    QemuConfiguration,
    QemuRunResult,
    QemuRunStatus,
)
from qemu_sandbox.qemu_machine_factory import (
    _build_qemu_command,
    stop_and_remove_qemu_run,
)
from qemu_sandbox.run_results import save_run_results
from virtualbox_sandbox.models import GuestScriptResult


def test_qemu_credentials_round_trip(tmp_path: Path) -> None:
    """Verify QEMU guest credentials use the expected JSON file shape."""
    credentials = load_or_create_guest_credentials(tmp_path, "sandbox")
    loaded_credentials = load_or_create_guest_credentials(tmp_path, "ignored")

    assert loaded_credentials == credentials
    assert (tmp_path / "credentials.json").exists()


def test_qemu_command_uses_requested_ssh_forward(tmp_path: Path) -> None:
    """Verify the QEMU command includes the run disk and SSH forward."""
    configuration = _create_test_configuration(tmp_path)
    run_disk_path = tmp_path / "run.qcow2"
    command = _build_qemu_command(
        configuration,
        Path("qemu-system-x86_64"),
        run_disk_path,
        2222,
    )

    assert "-machine" in command
    assert "q35,accel=whpx" in command
    assert f"file={run_disk_path},format=qcow2,if=virtio" in command
    assert "user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22" in command
    assert "virtio-net-pci,netdev=net0" in command


def test_qemu_run_results_do_not_write_result_json(tmp_path: Path) -> None:
    """Verify QEMU run persistence omits the old result.json wrapper file."""
    run_result = QemuRunResult(
        status=QemuRunStatus.STARTED,
        base_image_path=tmp_path / "base.qcow2",
        qemu_path=Path("qemu-system-x86_64"),
        run_directory=tmp_path,
        run_disk_path=tmp_path / "run.qcow2",
        ssh_host="127.0.0.1",
        ssh_port=2222,
        process=None,
        command=["qemu-system-x86_64"],
    )
    script_result = GuestScriptResult(
        script_path="/tmp/script.py",
        source_path="/tmp/source",
        command="python /tmp/script.py",
        exit_code=0,
        stdout="hello",
        stderr="",
        artifacts={
            "report.json": "[]",
            "playwright_tool_screenshot.png": b"png",
        },
    )

    save_run_results(tmp_path, run_result, script_result)

    assert (tmp_path / "stdout.txt").read_text(encoding="utf-8") == "hello\n"
    assert (tmp_path / "stderr.txt").read_text(encoding="utf-8") == "\n"
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "playwright_tool_screenshot.png").exists()
    assert (tmp_path / "run-metadata.json").exists()
    assert not (tmp_path / "result.json").exists()


def test_stop_and_remove_qemu_run_deletes_run_disk(tmp_path: Path) -> None:
    """Verify default QEMU teardown removes the disposable disk clone."""
    run_disk_path = tmp_path / "run.qcow2"
    run_disk_path.write_text("disk", encoding="utf-8")
    run_result = QemuRunResult(
        status=QemuRunStatus.STARTED,
        base_image_path=tmp_path / "base.qcow2",
        run_directory=tmp_path,
        run_disk_path=run_disk_path,
    )

    stop_and_remove_qemu_run(run_result)

    assert not run_disk_path.exists()


def _create_test_configuration(tmp_path: Path) -> QemuConfiguration:
    return QemuConfiguration(
        base_directory=tmp_path,
        base_image_path=tmp_path / "base.qcow2",
        qemu_path=Path("qemu-system-x86_64"),
        guest_credentials=GuestCredentials(
            user="sandbox",
            password="password",
        ),
        machine="q35",
        accelerator="whpx",
        cpu="qemu64",
        memory_megabytes=4096,
        cpu_count=2,
    )
