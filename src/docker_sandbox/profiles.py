"""Docker sandbox hardening profiles."""

from __future__ import annotations

from .models import DockerProfile

BASELINE_PROFILE_NAME = "baseline"
BASELINE_IMAGE_NAME = "sandbox-tester/docker-sandbox:baseline"
READONLY_FS_PROFILE_NAME = "readonly-fs"
READONLY_FS_IMAGE_NAME = "sandbox-tester/docker-sandbox:readonly-fs"

_PROFILES: dict[str, DockerProfile] = {
    BASELINE_PROFILE_NAME: DockerProfile(
        name=BASELINE_PROFILE_NAME,
        description=(
            "Current Docker sandbox behavior with no additional image or "
            "container hardening."
        ),
        image_name=BASELINE_IMAGE_NAME,
    ),
    READONLY_FS_PROFILE_NAME: DockerProfile(
        name=READONLY_FS_PROFILE_NAME,
        description=(
            "Run Sandbox Tester with a read-only root filesystem, writable "
            "output mount, and tmpfs-backed runtime directories."
        ),
        image_name=READONLY_FS_IMAGE_NAME,
        container_run_options=(
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,size=2g",
            "--tmpfs",
            "/sandbox-work:rw,nosuid,nodev,noexec,size=256m",
            "--env",
            "HOME=/tmp/sandbox-home",
            "--env",
            "XDG_CACHE_HOME=/tmp/sandbox-cache",
            "--env",
            "XDG_CONFIG_HOME=/tmp/sandbox-config",
            "--env",
            "XDG_RUNTIME_DIR=/tmp/sandbox-runtime",
        ),
        remote_run_root="/sandbox-work",
        allowed_directory_template="{remote_run_directory}/allowed",
        denied_directory_template="/sandbox-denied",
        readonly_denied_mount_target="/sandbox-denied",
    ),
}

SUPPORTED_PROFILE_NAMES = tuple(sorted(_PROFILES))


def get_docker_profile(name: str) -> DockerProfile:
    """Return the Docker hardening profile with the given name."""
    try:
        return _PROFILES[name]
    except KeyError as error:
        raise ValueError(f"Unsupported Docker sandbox profile: {name}") from error
