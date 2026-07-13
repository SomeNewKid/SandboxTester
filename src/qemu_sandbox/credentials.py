"""Manage local guest credentials for QEMU sandbox VMs."""

from __future__ import annotations

import json
import secrets
import string
from pathlib import Path

from .models import GuestCredentials

_CREDENTIALS_FILE_NAME = "credentials.json"
_PASSWORD_LENGTH = 32
_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def load_or_create_guest_credentials(
    base_directory: Path,
    guest_user: str,
) -> GuestCredentials:
    """Load persisted guest credentials or create new local credentials."""
    credentials_path = base_directory / _CREDENTIALS_FILE_NAME

    if credentials_path.exists():
        return _read_guest_credentials(credentials_path)

    credentials = GuestCredentials(
        user=guest_user,
        password=_generate_password(),
    )
    _write_guest_credentials(credentials_path, credentials)
    return credentials


def _read_guest_credentials(path: Path) -> GuestCredentials:
    data = json.loads(path.read_text(encoding="utf-8"))
    return GuestCredentials(
        user=str(data["guest_user"]),
        password=str(data["guest_password"]),
    )


def _write_guest_credentials(path: Path, credentials: GuestCredentials) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "guest_user": credentials.user,
        "guest_password": credentials.password,
    }
    text = json.dumps(data, indent=2)
    path.write_text(f"{text}\n", encoding="utf-8")


def _generate_password() -> str:
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(_PASSWORD_LENGTH))
