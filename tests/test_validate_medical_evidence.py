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
    validate_record_templates,
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
    assert validate(ROOT) == (63, 13, 10)


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
