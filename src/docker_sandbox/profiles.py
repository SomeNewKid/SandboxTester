"""Docker sandbox hardening profiles."""

from __future__ import annotations

from .models import (
    DockerProfile,
    EnvironmentVariablePolicy,
    LandlockPathRule,
    NetworkGatewayProfile,
)

BASELINE_PROFILE_NAME = "baseline"
BASELINE_IMAGE_NAME = "sandbox-tester/docker-sandbox:baseline"
READONLY_FS_PROFILE_NAME = "readonly-fs"
READONLY_FS_IMAGE_NAME = "sandbox-tester/docker-sandbox:readonly-fs"
NETWORK_EGRESS_PROFILE_NAME = "network-egress"
NETWORK_EGRESS_IMAGE_NAME = "sandbox-tester/docker-sandbox:network-egress"
AMBIENT_SERVICES_PROFILE_NAME = "ambient-services"
AMBIENT_SERVICES_IMAGE_NAME = "sandbox-tester/docker-sandbox:ambient-services"
EXECUTION_CONTROL_PROFILE_NAME = "execution-control"
EXECUTION_CONTROL_IMAGE_NAME = "sandbox-tester/docker-sandbox:execution-control"

_PROFILES: dict[str, DockerProfile] = {
    BASELINE_PROFILE_NAME: DockerProfile(
        name=BASELINE_PROFILE_NAME,
        description=(
            "Current Docker sandbox behavior with no additional image or "
            "container hardening."
        ),
        image_name=BASELINE_IMAGE_NAME,
        cgroupns_mode=None,
        pids_limit=None,
        cap_drop=(),
        security_options=(),
        denied_executable_paths=(),
    ),
    READONLY_FS_PROFILE_NAME: DockerProfile(
        name=READONLY_FS_PROFILE_NAME,
        description=(
            "Run Sandbox Tester with a read-only root filesystem, writable "
            "output mount, and tmpfs-backed runtime directories."
        ),
        image_name=READONLY_FS_IMAGE_NAME,
        cgroupns_mode=None,
        pids_limit=None,
        cap_drop=(),
        security_options=(),
        denied_executable_paths=(),
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
        landlock_rules=(
            LandlockPathRule("/bin", "rx"),
            LandlockPathRule("/etc", "r"),
            LandlockPathRule("/lib", "rx"),
            LandlockPathRule("/lib64", "rx"),
            LandlockPathRule("/ms-playwright", "rx"),
            LandlockPathRule("/opt/sandbox-tester", "rx"),
            LandlockPathRule("/sbin", "rx"),
            LandlockPathRule("/usr", "rx"),
            LandlockPathRule("/var", "r"),
            LandlockPathRule("/dev", "rw"),
            LandlockPathRule("/proc", "r"),
            LandlockPathRule("/sys", "r"),
            LandlockPathRule("/sandbox-source", "r"),
            LandlockPathRule("/sandbox-output", "rw"),
            LandlockPathRule("/sandbox-work", "rw"),
            LandlockPathRule("/tmp", "rw"),
        ),
    ),
    NETWORK_EGRESS_PROFILE_NAME: DockerProfile(
        name=NETWORK_EGRESS_PROFILE_NAME,
        description=(
            "Start from the readonly-fs hardening profile so network egress "
            "controls can be added and measured independently."
        ),
        image_name=NETWORK_EGRESS_IMAGE_NAME,
        cgroupns_mode=None,
        pids_limit=None,
        cap_drop=(),
        security_options=(),
        denied_executable_paths=(),
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
        landlock_rules=(
            LandlockPathRule("/bin", "rx"),
            LandlockPathRule("/etc", "r"),
            LandlockPathRule("/lib", "rx"),
            LandlockPathRule("/lib64", "rx"),
            LandlockPathRule("/ms-playwright", "rx"),
            LandlockPathRule("/opt/sandbox-tester", "rx"),
            LandlockPathRule("/sbin", "rx"),
            LandlockPathRule("/usr", "rx"),
            LandlockPathRule("/var", "r"),
            LandlockPathRule("/dev", "rw"),
            LandlockPathRule("/proc", "r"),
            LandlockPathRule("/sys", "r"),
            LandlockPathRule("/sandbox-source", "r"),
            LandlockPathRule("/sandbox-output", "rw"),
            LandlockPathRule("/sandbox-work", "rw"),
            LandlockPathRule("/tmp", "rw"),
        ),
        network_gateway=NetworkGatewayProfile(
            image_name="ubuntu/squid:latest",
            proxy_host="egress-gateway",
            proxy_port=3128,
            allowed_domains=(
                ".openai.com",
                ".example.com",
                ".github.com",
                ".gov.uk",
            ),
            allowed_ip_addresses=(
                # "1.1.1.1",
            ),
        ),
    ),
    AMBIENT_SERVICES_PROFILE_NAME: DockerProfile(
        name=AMBIENT_SERVICES_PROFILE_NAME,
        description=(
            "Start from the network-egress hardening profile so ambient "
            "service and IPC controls can be added and measured independently."
        ),
        image_name=AMBIENT_SERVICES_IMAGE_NAME,
        ipc_mode="private",
        shm_size="1g",
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
        landlock_rules=(
            LandlockPathRule("/bin", "rx"),
            LandlockPathRule("/etc", "r"),
            LandlockPathRule("/lib", "rx"),
            LandlockPathRule("/lib64", "rx"),
            LandlockPathRule("/ms-playwright", "rx"),
            LandlockPathRule("/opt/sandbox-tester", "rx"),
            LandlockPathRule("/sbin", "rx"),
            LandlockPathRule("/usr", "rx"),
            LandlockPathRule("/var", "r"),
            LandlockPathRule("/dev", "rw"),
            LandlockPathRule("/proc", "r"),
            LandlockPathRule("/sys", "r"),
            LandlockPathRule("/sandbox-source", "r"),
            LandlockPathRule("/sandbox-output", "rw"),
            LandlockPathRule("/sandbox-work", "rw"),
            LandlockPathRule("/tmp", "rw"),
        ),
        network_gateway=NetworkGatewayProfile(
            image_name="ubuntu/squid:latest",
            proxy_host="egress-gateway",
            proxy_port=3128,
            allowed_domains=(
                ".openai.com",
                ".example.com",
                ".github.com",
                ".gov.uk",
            ),
            allowed_ip_addresses=(
                # "1.1.1.1",
            ),
        ),
        environment=(
            EnvironmentVariablePolicy("SSH_AUTH_SOCK", None),
            EnvironmentVariablePolicy("GPG_AGENT_INFO", None),
            EnvironmentVariablePolicy("DBUS_SESSION_BUS_ADDRESS", None),
            EnvironmentVariablePolicy("DISPLAY", None),
            EnvironmentVariablePolicy("WAYLAND_DISPLAY", None),
            EnvironmentVariablePolicy("GNUPGHOME", "/tmp/sandbox-gnupg-empty"),
        ),
        denied_executable_paths=(
            "/usr/bin/busctl",
            "/usr/bin/dbus-send",
            "/usr/bin/gpg",
            "/usr/bin/gpg-connect-agent",
            "/usr/bin/gpgconf",
            "/usr/bin/journalctl",
            "/usr/bin/loginctl",
            "/usr/bin/scp",
            "/usr/bin/sftp",
            "/usr/bin/ssh",
            "/usr/bin/ssh-add",
            "/usr/bin/systemctl",
            "/usr/sbin/service",
        ),
    ),
    EXECUTION_CONTROL_PROFILE_NAME: DockerProfile(
        name=EXECUTION_CONTROL_PROFILE_NAME,
        description=(
            "Start from the ambient-services hardening profile so process "
            "and executable controls can be added and measured independently."
        ),
        image_name=EXECUTION_CONTROL_IMAGE_NAME,
        ipc_mode="private",
        shm_size="1g",
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
        landlock_rules=(
            LandlockPathRule("/bin", "rx"),
            LandlockPathRule("/etc", "r"),
            LandlockPathRule("/lib", "rx"),
            LandlockPathRule("/lib64", "rx"),
            LandlockPathRule("/ms-playwright", "rx"),
            LandlockPathRule("/opt/sandbox-tester", "rx"),
            LandlockPathRule("/sbin", "rx"),
            LandlockPathRule("/usr", "rx"),
            LandlockPathRule("/var", "r"),
            LandlockPathRule("/dev", "rw"),
            LandlockPathRule("/proc", "r"),
            LandlockPathRule("/sys", "r"),
            LandlockPathRule("/sandbox-source", "r"),
            LandlockPathRule("/sandbox-output", "rw"),
            LandlockPathRule("/sandbox-work", "rw"),
            LandlockPathRule("/tmp", "rw"),
        ),
        network_gateway=NetworkGatewayProfile(
            image_name="ubuntu/squid:latest",
            proxy_host="egress-gateway",
            proxy_port=3128,
            allowed_domains=(
                ".openai.com",
                ".example.com",
                ".github.com",
                ".gov.uk",
            ),
            allowed_ip_addresses=(
                # "1.1.1.1",
            ),
        ),
        environment=(
            EnvironmentVariablePolicy("SSH_AUTH_SOCK", None),
            EnvironmentVariablePolicy("GPG_AGENT_INFO", None),
            EnvironmentVariablePolicy("DBUS_SESSION_BUS_ADDRESS", None),
            EnvironmentVariablePolicy("DISPLAY", None),
            EnvironmentVariablePolicy("WAYLAND_DISPLAY", None),
            EnvironmentVariablePolicy("GNUPGHOME", "/tmp/sandbox-gnupg-empty"),
        ),
    ),
}

SUPPORTED_PROFILE_NAMES = tuple(sorted(_PROFILES))


def get_docker_profile(name: str) -> DockerProfile:
    """Return the Docker hardening profile with the given name."""
    try:
        return _PROFILES[name]
    except KeyError as error:
        raise ValueError(f"Unsupported Docker sandbox profile: {name}") from error
