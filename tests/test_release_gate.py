import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts.generate_sbom import sha256_file
from scripts.release_gate import (
    ReleaseGateError,
    load_release_gates,
    verify_controlled_runtime,
    verify_release_disposition,
    verify_sbom_receipt,
)

ROOT = Path(__file__).resolve().parents[1]


def write_manifest(
    path: Path, gate: dict[str, object], disposition: str = "release_blocked"
) -> None:
    path.write_text(
        json.dumps(
            {"schema_version": 1, "disposition": disposition, "gates": [gate]}
        ),
        encoding="utf-8",
    )


def test_pending_gate_is_valid_but_not_release_approved(tmp_path: Path) -> None:
    manifest = tmp_path / "readiness.json"
    write_manifest(
        manifest,
        {
            "id": "CLINICAL",
            "title": "Clinical validation",
            "required": True,
            "status": "pending",
            "owner": "clinical-lead",
            "evidence": [],
        },
    )
    gates = load_release_gates(manifest, tmp_path)
    assert gates[0].status == "pending"
    assert gates[0].required


def test_approved_gate_requires_existing_evidence(tmp_path: Path) -> None:
    manifest = tmp_path / "readiness.json"
    write_manifest(
        manifest,
        {
            "id": "SOFTWARE",
            "title": "Software verification",
            "required": True,
            "status": "approved",
            "owner": "verification-lead",
            "evidence": ["missing-report.pdf"],
            "approver": "independent-reviewer",
            "approved_at": "2026-07-16T10:00:00Z",
        },
    )
    with pytest.raises(ReleaseGateError, match="missing evidence"):
        load_release_gates(manifest, tmp_path)


def test_approved_gate_accepts_dated_review_and_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "verification.txt"
    evidence.write_text("signed verification evidence", encoding="utf-8")
    manifest = tmp_path / "readiness.json"
    write_manifest(
        manifest,
        {
            "id": "SOFTWARE",
            "title": "Software verification",
            "required": True,
            "status": "approved",
            "owner": "verification-lead",
            "evidence": [evidence.name],
            "approver": "independent-reviewer",
            "approved_at": "2026-07-16T10:00:00Z",
        },
    )
    assert load_release_gates(manifest, tmp_path)[0].status == "approved"


def test_clinical_gate_rejects_draft_studies_and_templates(tmp_path: Path) -> None:
    shutil.copytree(
        ROOT / "docs/medical-device",
        tmp_path / "docs/medical-device",
    )
    manifest = tmp_path / "readiness.json"
    write_manifest(
        manifest,
        {
            "id": "CLINICAL",
            "title": "Clinical validation",
            "required": True,
            "status": "approved",
            "owner": "clinical-lead",
            "evidence": ["docs/medical-device/CLINICAL_EVALUATION.md"],
            "approver": "independent-clinical-reviewer",
            "approved_at": "2026-07-18T10:00:00Z",
        },
    )
    with pytest.raises(ReleaseGateError, match="lacks completed controlled evidence"):
        load_release_gates(manifest, tmp_path)


def test_approved_gate_rejects_evidence_outside_repository(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-evidence.txt"
    outside.write_text("not controlled by this repository", encoding="utf-8")
    manifest = tmp_path / "readiness.json"
    write_manifest(
        manifest,
        {
            "id": "SOFTWARE",
            "title": "Software verification",
            "required": True,
            "status": "approved",
            "owner": "verification-lead",
            "evidence": [f"../{outside.name}"],
            "approver": "independent-reviewer",
            "approved_at": "2026-07-16T10:00:00Z",
        },
    )
    with pytest.raises(ReleaseGateError, match="outside the repository"):
        load_release_gates(manifest, tmp_path)


def test_release_disposition_must_be_explicitly_approved(tmp_path: Path) -> None:
    manifest = tmp_path / "readiness.json"
    write_manifest(manifest, {}, disposition="release_blocked")
    with pytest.raises(ReleaseGateError, match="release_approved"):
        verify_release_disposition(manifest)

    write_manifest(manifest, {}, disposition="release_approved")
    verify_release_disposition(manifest)


def write_sbom_evidence(root: Path) -> tuple[Path, Path]:
    requirements = root / "requirements.lock"
    requirements.write_text("example==1.0\n", encoding="utf-8")
    sbom = root / "sbom.cdx.json"
    sbom.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "components": [{"name": "example", "version": "1.0"}],
            }
        ),
        encoding="utf-8",
    )
    receipt = root / "sbom.cdx.json.receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "audit_exit_code": 0,
                "release_acceptable": True,
                "generated_at_utc": "2026-07-16T10:00:00Z",
                "generator": "pip-audit test",
                "component_count": 1,
                "vulnerability_count": 0,
                "requirements_sha256": sha256_file(requirements),
                "sbom_sha256": sha256_file(sbom),
            }
        ),
        encoding="utf-8",
    )
    return sbom, receipt


def test_release_gate_revalidates_sbom_and_lock_hashes(tmp_path: Path) -> None:
    _, receipt = write_sbom_evidence(tmp_path)
    verify_sbom_receipt(receipt, tmp_path)

    (tmp_path / "requirements.lock").write_text("changed==2.0\n", encoding="utf-8")
    with pytest.raises(ReleaseGateError, match="requirements.lock"):
        verify_sbom_receipt(receipt, tmp_path)


def test_release_gate_rejects_tampered_sbom(tmp_path: Path) -> None:
    sbom, receipt = write_sbom_evidence(tmp_path)
    payload = json.loads(sbom.read_text())
    payload["components"].append({"name": "injected", "version": "9.9"})
    sbom.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ReleaseGateError, match="counts|CycloneDX document"):
        verify_sbom_receipt(receipt, tmp_path)


def test_controlled_runtime_requires_and_revalidates_sbom_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, receipt = write_sbom_evidence(tmp_path)
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"approved model")
    monkeypatch.setenv("ATTNDIST_OPERATING_MODE", "controlled")
    monkeypatch.setenv("ATTNDIST_RELEASE_ID", "release-1")
    monkeypatch.setenv(
        "ATTNDIST_APPROVED_CHECKPOINT_SHA256",
        hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("ATTNDIST_CHECKPOINT", str(checkpoint))
    monkeypatch.setenv("ATTNDIST_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("ATTNDIST_API_TOKEN", "s" * 32)
    monkeypatch.setenv("ATTNDIST_ALLOWED_ORIGINS", "https://lab.example")

    with pytest.raises(ReleaseGateError, match="ATTNDIST_SBOM_RECEIPT"):
        verify_controlled_runtime(tmp_path)

    monkeypatch.setenv("ATTNDIST_SBOM_RECEIPT", str(receipt))
    verify_controlled_runtime(tmp_path)
