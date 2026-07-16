import json
import subprocess
from pathlib import Path

import pytest

from scripts import generate_sbom as sbom_module
from scripts.generate_sbom import SbomGenerationError, generate_sbom


def write_lock(path: Path) -> None:
    path.write_text("example==1.0 --hash=sha256:" + "0" * 64 + "\n", encoding="utf-8")


def fake_audit(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int = 0,
    vulnerabilities: list[dict[str, object]] | None = None,
) -> None:
    def run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        assert not check
        assert command[command.index("--extra-index-url") + 1] == sbom_module.PYTORCH_CPU_INDEX
        output = Path(command[command.index("--output") + 1])
        output.write_text(
            json.dumps(
                {
                    "bomFormat": "CycloneDX",
                    "specVersion": "1.6",
                    "components": [{"name": "example", "version": "1.0"}],
                    "vulnerabilities": vulnerabilities or [],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, returncode)

    monkeypatch.setattr(sbom_module.subprocess, "run", run)


def test_sbom_generation_binds_evidence_to_requirements_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.lock"
    output = tmp_path / "sbom.cdx.json"
    write_lock(requirements)
    fake_audit(monkeypatch)

    receipt = generate_sbom(requirements, output, tmp_path / "cache")

    assert receipt.release_acceptable
    assert receipt.component_count == 1
    assert receipt.vulnerability_count == 0
    assert receipt.requirements_sha256 == sbom_module.sha256_file(requirements)
    assert receipt.sbom_sha256 == sbom_module.sha256_file(output)
    stored = json.loads(output.with_suffix(".json.receipt.json").read_text())
    assert stored["sbom_sha256"] == receipt.sbom_sha256


def test_sbom_generation_preserves_failed_audit_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.lock"
    output = tmp_path / "sbom.cdx.json"
    write_lock(requirements)
    fake_audit(monkeypatch, returncode=1, vulnerabilities=[{"id": "CVE-test"}])

    with pytest.raises(SbomGenerationError, match="release is blocked"):
        generate_sbom(requirements, output, tmp_path / "cache")

    assert output.is_file()
    stored = json.loads(output.with_suffix(".json.receipt.json").read_text())
    assert stored["release_acceptable"] is False
    assert stored["vulnerability_count"] == 1


def test_sbom_generation_refuses_implicit_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.lock"
    output = tmp_path / "sbom.cdx.json"
    write_lock(requirements)
    output.write_text("existing evidence", encoding="utf-8")
    fake_audit(monkeypatch)

    with pytest.raises(SbomGenerationError, match="already exists"):
        generate_sbom(requirements, output, tmp_path / "cache")
