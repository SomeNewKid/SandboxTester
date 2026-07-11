"""Tests for evidence redaction."""

import pytest

from sandbox_tester.redaction import redact_evidence

_REDACTED = "[REDACTED]"


def test_redacts_sensitive_environment_assignment_values() -> None:
    """Sensitive environment variable values should not remain in evidence."""
    evidence = "\n".join(
        [
            "ANTHROPIC_API_KEY=sk-ant-test-secret",
            "GOOGLE_API_KEY=AIzaSyTestSecret",
            "HF_TOKEN=hf_test_secret",
            r"APPDATA=C:\Users\somen\AppData\Roaming",
        ]
    )

    redacted = redact_evidence(evidence)

    assert "ANTHROPIC_API_KEY=[REDACTED]" in redacted
    assert "GOOGLE_API_KEY=[REDACTED]" in redacted
    assert "HF_TOKEN=[REDACTED]" in redacted
    assert r"APPDATA=C:\Users\somen\AppData\Roaming" in redacted
    assert "sk-ant-test-secret" not in redacted
    assert "AIzaSyTestSecret" not in redacted
    assert "hf_test_secret" not in redacted


@pytest.mark.parametrize(
    ("secret", "evidence"),
    [
        ("sk-ant-test-secret", "token sk-ant-test-secret was visible"),
        ("sk-test-secret", "OPENAI_API_KEY=sk-test-secret"),
        ("ghp_testsecret", "GitHub token ghp_testsecret was visible"),
        ("github_pat_testsecret", "token=github_pat_testsecret"),
        ("AKIATESTSECRET", "AWS_ACCESS_KEY_ID=AKIATESTSECRET"),
    ],
)
def test_redacts_common_token_patterns(secret: str, evidence: str) -> None:
    """Common token formats should be redacted even outside env output."""
    redacted = redact_evidence(evidence)

    assert secret not in redacted
    assert _REDACTED in redacted


@pytest.mark.parametrize(
    "evidence",
    [
        "Authorization: Bearer bearer-token-secret",
        "password: correct-horse-battery-staple",
        "client_secret=client-secret-value",
        "SESSION_COOKIE=session-cookie-value",
    ],
)
def test_redacts_sensitive_key_value_fields(evidence: str) -> None:
    """Sensitive key names should have their associated values redacted."""
    redacted = redact_evidence(evidence)

    assert evidence not in redacted
    assert _REDACTED in redacted


def test_redacts_private_key_blocks() -> None:
    """Private key material should be removed from evidence."""
    evidence = "\n".join(
        [
            "before",
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "private-key-material",
            "-----END OPENSSH PRIVATE KEY-----",
            "after",
        ]
    )

    redacted = redact_evidence(evidence)

    assert "private-key-material" not in redacted
    assert "-----BEGIN OPENSSH PRIVATE KEY-----" not in redacted
    assert "before" in redacted
    assert "after" in redacted
    assert _REDACTED in redacted


def test_preserves_non_sensitive_evidence() -> None:
    """Ordinary diagnostic evidence should be left unchanged."""
    evidence = "count=3; names=PATH, APPDATA, COMPUTERNAME"

    redacted = redact_evidence(evidence)

    assert redacted == evidence
