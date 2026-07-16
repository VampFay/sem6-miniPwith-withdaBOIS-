from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.validate_medical_evidence import MedicalEvidenceError, validate_document_index

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
