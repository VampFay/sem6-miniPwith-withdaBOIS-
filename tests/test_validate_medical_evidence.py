from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from scripts.validate_medical_evidence import (
    RECORD_SCHEMAS,
    MedicalEvidenceError,
    validate,
    validate_document_index,
    validate_execution_workstreams,
    validate_model_validation_controls,
    validate_record_templates,
    verify_clinical_release_evidence,
)

FIELDS = [
    "document_id",
    "title",
    "path",
    "revision",
    "status",
    "owner",
    "approver",
    "effective_date",
]
ROOT = Path(__file__).resolve().parents[1]


def _write_index(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_document_index_rejects_false_approval(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"value": 1}), encoding="utf-8")
    index = tmp_path / "index.csv"
    _write_index(
        index,
        [
            {
                "document_id": "DOC-1",
                "title": "Fixture",
                "path": "evidence.json",
                "revision": "1",
                "status": "approved",
                "owner": "owner-unassigned",
                "approver": "approver-unassigned",
                "effective_date": "",
            }
        ],
    )
    with pytest.raises(MedicalEvidenceError, match="lacks accountable"):
        validate_document_index(tmp_path, index)


def test_document_index_accepts_controlled_draft(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"value": 1}), encoding="utf-8")
    index = tmp_path / "index.csv"
    _write_index(
        index,
        [
            {
                "document_id": "DOC-1",
                "title": "Fixture",
                "path": "evidence.json",
                "revision": "0.1",
                "status": "draft",
                "owner": "owner-unassigned",
                "approver": "approver-unassigned",
                "effective_date": "",
            }
        ],
    )
    assert validate_document_index(tmp_path, index) == 1


def test_repository_has_all_controlled_execution_workstreams() -> None:
    assert validate(ROOT) == (68, 13, 10)
    assert validate_model_validation_controls(ROOT) == 6


def _copy_medical_controls(tmp_path: Path) -> Path:
    shutil.copytree(
        ROOT / "docs/medical-device",
        tmp_path / "docs/medical-device",
    )
    return tmp_path


def test_draft_study_cannot_claim_execution_or_results(tmp_path: Path) -> None:
    root = _copy_medical_controls(tmp_path)
    register = root / "docs/medical-device/model-data/CLINICAL_STUDY_REGISTER.csv"
    with register.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0]["result"] = "passed"
    with register.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(MedicalEvidenceError, match="execution or approval claims"):
        validate_model_validation_controls(root)


def test_reported_study_requires_frozen_hashes_and_approvers(tmp_path: Path) -> None:
    root = _copy_medical_controls(tmp_path)
    register = root / "docs/medical-device/model-data/CLINICAL_STUDY_REGISTER.csv"
    with register.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0]["status"] = "reported"
    rows[0]["result"] = "passed"
    rows[0]["report_id"] = "REPORT-1"
    with register.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(MedicalEvidenceError, match="candidate/dataset hashes"):
        validate_model_validation_controls(root)


def test_current_draft_studies_cannot_satisfy_clinical_release_gate() -> None:
    with pytest.raises(MedicalEvidenceError, match="not completed and approved"):
        verify_clinical_release_evidence(ROOT)


def _write_completed_clinical_evidence(root: Path) -> Path:
    register = root / "docs/medical-device/model-data/CLINICAL_STUDY_REGISTER.csv"
    with register.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {"PV-INT-001", "PV-RR-001", "PV-EXT-001", "PV-PRO-001"}
    for row in rows:
        if row["study_id"] in required:
            row.update(
                {
                    "status": "closed",
                    "candidate_model_sha256": "a" * 64,
                    "dataset_manifest_sha256": "b" * 64,
                    "first_subject_or_analysis_date": "2026-01-01",
                    "database_lock_date": "2026-02-01",
                    "report_id": f"REPORT-{row['study_id']}",
                    "result": "met_acceptance_criteria",
                    "clinical_statistical_approvers": "clinical-lead;biostatistician",
                    "approval_date": "2026-03-01",
                }
            )
        elif row["study_id"] == "PV-RDR-001":
            row.update(
                {
                    "status": "not_required_approved",
                    "result": "approved claim-based not-required rationale",
                    "clinical_statistical_approvers": "clinical-lead;biostatistician",
                    "approval_date": "2026-03-01",
                }
            )
    with register.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    template = root / "docs/medical-device/model-data/FROZEN_MODEL_CARD.template.json"
    model_card = json.loads(template.read_text(encoding="utf-8"))
    model_card["status"] = "frozen"
    model_card["candidate_id"] = "CANDIDATE-1"
    model_card["model"]["sha256"] = "a" * 64
    model_card["software"]["source_commit"] = "f" * 40
    model_card["data"]["internal_test_manifest_sha256"] = "b" * 64
    model_card["quality_approval"] = "quality-manager@2026-03-01"
    path = root / "docs/medical-device/model-data/FROZEN_MODEL_CARD.json"
    path.write_text(json.dumps(model_card), encoding="utf-8")
    return register


def test_completed_clinical_evidence_must_bind_one_frozen_candidate(
    tmp_path: Path,
) -> None:
    root = _copy_medical_controls(tmp_path)
    register = _write_completed_clinical_evidence(root)
    verify_clinical_release_evidence(root)

    with register.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[1]["candidate_model_sha256"] = "c" * 64
    with register.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(MedicalEvidenceError, match="one identical frozen candidate"):
        verify_clinical_release_evidence(root)


def _write_execution_manifest(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "execution-workstreams.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_execution_workstream_rejects_false_readiness(tmp_path: Path) -> None:
    root = ROOT
    source = root / "docs/medical-device/EXECUTION_WORKSTREAMS.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["workstreams"][0]["status"] = "ready"
    manifest = _write_execution_manifest(tmp_path, payload)
    with pytest.raises(MedicalEvidenceError, match="unassigned accountability"):
        validate_execution_workstreams(
            root,
            manifest,
            root / "docs/medical-device/RELEASE_READINESS.json",
        )


def test_ready_workstream_requires_completed_evidence(tmp_path: Path) -> None:
    root = ROOT
    source = root / "docs/medical-device/EXECUTION_WORKSTREAMS.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    workstream = payload["workstreams"][0]
    workstream["status"] = "ready"
    workstream["owner"] = "executive-sponsor"
    workstream["approver"] = "legal-manufacturer"
    workstream["approved_at"] = "2026-07-17T12:00:00Z"
    manifest = _write_execution_manifest(tmp_path, payload)
    with pytest.raises(MedicalEvidenceError, match="no completed evidence"):
        validate_execution_workstreams(
            root,
            manifest,
            root / "docs/medical-device/RELEASE_READINESS.json",
        )


def test_execution_workstream_rejects_dependency_cycle(tmp_path: Path) -> None:
    root = ROOT
    source = root / "docs/medical-device/EXECUTION_WORKSTREAMS.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["workstreams"][0]["dependencies"] = ["WS-10"]
    manifest = _write_execution_manifest(tmp_path, payload)
    with pytest.raises(MedicalEvidenceError, match="dependencies contain a cycle"):
        validate_execution_workstreams(
            root,
            manifest,
            root / "docs/medical-device/RELEASE_READINESS.json",
        )


def test_execution_workstream_rejects_false_clinical_authorization(tmp_path: Path) -> None:
    root = ROOT
    source = root / "docs/medical-device/EXECUTION_WORKSTREAMS.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["authorized_use"] = "clinical_authorized"
    manifest = _write_execution_manifest(tmp_path, payload)
    with pytest.raises(MedicalEvidenceError, match="Clinical authorization conflicts"):
        validate_execution_workstreams(
            root,
            manifest,
            root / "docs/medical-device/RELEASE_READINESS.json",
        )


def test_daily_safety_template_rejects_missing_control(tmp_path: Path) -> None:
    root = ROOT
    for relative in RECORD_SCHEMAS:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, destination)
    checklist = tmp_path / "docs/medical-device/operations/DAILY_SAFETY_CHECKLIST.csv"
    rows = checklist.read_text(encoding="utf-8").splitlines()
    checklist.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(MedicalEvidenceError, match="Daily-safety control set"):
        validate_record_templates(tmp_path)
