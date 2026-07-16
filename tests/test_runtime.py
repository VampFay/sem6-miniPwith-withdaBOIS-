from pathlib import Path

import pytest

from src.runtime import RuntimeConfig, RuntimeConfigurationError, read_verified_checkpoint


def clear_runtime_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ATTNDIST_OPERATING_MODE",
        "ATTNDIST_RELEASE_ID",
        "ATTNDIST_APPROVED_CHECKPOINT_SHA256",
        "ATTNDIST_AUDIT_DIR",
        "ATTNDIST_API_TOKEN",
        "ATTNDIST_ALLOWED_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_research_mode_is_safe_default(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_runtime_environment(monkeypatch)
    config = RuntimeConfig.from_environment()
    assert config.operating_mode == "research"
    assert config.release_id == "development"
    assert not config.is_controlled


def test_controlled_mode_requires_all_safeguards(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_runtime_environment(monkeypatch)
    monkeypatch.setenv("ATTNDIST_OPERATING_MODE", "controlled")
    with pytest.raises(RuntimeConfigurationError, match="Controlled mode requires"):
        RuntimeConfig.from_environment()


def test_runtime_rejects_unknown_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_runtime_environment(monkeypatch)
    monkeypatch.setenv("ATTNDIST_OPERATING_MODE", "clinical")
    with pytest.raises(RuntimeConfigurationError, match="must be"):
        RuntimeConfig.from_environment()


def test_runtime_rejects_invalid_release_and_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_runtime_environment(monkeypatch)
    monkeypatch.setenv("ATTNDIST_RELEASE_ID", "invalid release")
    with pytest.raises(RuntimeConfigurationError, match="RELEASE_ID"):
        RuntimeConfig.from_environment()
    monkeypatch.setenv("ATTNDIST_RELEASE_ID", "release-1")
    monkeypatch.setenv("ATTNDIST_APPROVED_CHECKPOINT_SHA256", "not-a-digest")
    with pytest.raises(RuntimeConfigurationError, match="SHA-256"):
        RuntimeConfig.from_environment()


def test_controlled_mode_requires_exact_https_origins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clear_runtime_environment(monkeypatch)
    monkeypatch.setenv("ATTNDIST_OPERATING_MODE", "controlled")
    monkeypatch.setenv("ATTNDIST_RELEASE_ID", "release-1")
    monkeypatch.setenv("ATTNDIST_APPROVED_CHECKPOINT_SHA256", "a" * 64)
    monkeypatch.setenv("ATTNDIST_AUDIT_DIR", str(tmp_path))
    monkeypatch.setenv("ATTNDIST_API_TOKEN", "s" * 32)
    monkeypatch.setenv("ATTNDIST_ALLOWED_ORIGINS", "http://lab.example")
    with pytest.raises(RuntimeConfigurationError, match="exact HTTPS origins"):
        RuntimeConfig.from_environment()

    monkeypatch.setenv("ATTNDIST_ALLOWED_ORIGINS", "https://lab.example")
    assert RuntimeConfig.from_environment().allowed_origins == ("https://lab.example",)


def test_checkpoint_digest_is_enforced(tmp_path: Path) -> None:
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"trusted model")
    with pytest.raises(RuntimeConfigurationError, match="approved digest"):
        read_verified_checkpoint(checkpoint, "0" * 64)


def test_checkpoint_digest_is_returned_for_matching_content(tmp_path: Path) -> None:
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"trusted model")
    content, digest = read_verified_checkpoint(checkpoint, None)
    assert content == b"trusted model"
    assert len(digest) == 64
