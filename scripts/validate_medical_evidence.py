from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


class MedicalEvidenceError(ValueError):
    """Raised when the controlled medical-device file is inconsistent."""


ALLOWED_DOCUMENT_STATUSES = {"draft", "template", "verified_research_evidence", "approved"}
REQUIRED_GATES = {
    "QMS",
    "INTENDED_USE",
    "REGULATORY",
    "RISK",
    "SOFTWARE",
    "CYBERSECURITY",
    "DATA_LICENSE",
    "CLINICAL",
    "USABILITY",
    "PRIVACY",
    "DEPLOYMENT",
    "LABELING",
    "POSTMARKET",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MedicalEvidenceError(f"Expected an object in {path}.")
    return value


def _inside_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise MedicalEvidenceError(
            f"Indexed evidence is missing or outside the repository: {relative}"
        )
    return path


def validate_document_index(root: Path, index: Path) -> int:
    with index.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {
        "document_id",
        "title",
        "path",
        "revision",
        "status",
        "owner",
        "approver",
        "effective_date",
    }
    if not rows or not required.issubset(rows[0]):
        raise MedicalEvidenceError("Document index is empty or has an invalid schema.")
    identifiers = [row["document_id"].strip() for row in rows]
    paths = [row["path"].strip() for row in rows]
    if any(not value for value in identifiers) or len(identifiers) != len(set(identifiers)):
        raise MedicalEvidenceError("Document identifiers must be populated and unique.")
    if any(not value for value in paths) or len(paths) != len(set(paths)):
        raise MedicalEvidenceError("Document paths must be populated and unique.")
    for row in rows:
        _inside_file(root, row["path"])
        status = row["status"].strip()
        if status not in ALLOWED_DOCUMENT_STATUSES:
            raise MedicalEvidenceError(
                f"Document {row['document_id']} has invalid status {status!r}."
            )
        if not row["revision"].strip() or not row["owner"].strip() or not row["approver"].strip():
            raise MedicalEvidenceError(
                f"Document {row['document_id']} has incomplete control data."
            )
        if status == "approved" and (
            "unassigned" in row["owner"].lower()
            or "unassigned" in row["approver"].lower()
            or not row["effective_date"].strip()
        ):
            raise MedicalEvidenceError(
                f"Approved document {row['document_id']} lacks accountable approval metadata."
            )
    return len(rows)


def validate_release_manifest(root: Path, manifest_path: Path) -> int:
    manifest = _load_json(manifest_path)
    gates = manifest.get("gates")
    if manifest.get("schema_version") != 1 or not isinstance(gates, list):
        raise MedicalEvidenceError("Release readiness manifest has an invalid schema.")
    gate_ids = {str(gate.get("id")) for gate in gates if isinstance(gate, dict)}
    if gate_ids != REQUIRED_GATES:
        raise MedicalEvidenceError(
            f"Release manifest gate set differs from the controlled set: {sorted(gate_ids)}"
        )
    for gate in gates:
        if not isinstance(gate, dict):
            raise MedicalEvidenceError("Release manifest contains a non-object gate.")
        evidence = gate.get("evidence")
        if not isinstance(evidence, list):
            raise MedicalEvidenceError(f"Gate {gate.get('id')} evidence must be a list.")
        for relative in evidence:
            if not isinstance(relative, str):
                raise MedicalEvidenceError(f"Gate {gate.get('id')} has a non-string evidence path.")
            _inside_file(root, relative)
    if manifest.get("disposition") == "release_approved":
        not_approved = [gate["id"] for gate in gates if gate.get("status") != "approved"]
        if not_approved:
            raise MedicalEvidenceError(
                f"Release disposition conflicts with pending gates: {not_approved}"
            )
    return len(gates)


def validate_model_evidence(snapshot_path: Path) -> None:
    snapshot = _load_json(snapshot_path)
    if snapshot.get("schema_version") != 1:
        raise MedicalEvidenceError("Model evidence snapshot has an unsupported schema.")
    dataset = snapshot.get("dataset")
    if not isinstance(dataset, dict) or not isinstance(snapshot.get("release_blockers"), list):
        raise MedicalEvidenceError("Model evidence snapshot is incomplete.")
    if (
        dataset.get("commercially_restricted") is True
        and snapshot.get("release_disposition") != "blocked"
    ):
        raise MedicalEvidenceError("Commercially restricted data must block release.")
    if snapshot.get("artifact_status") == "research_only" and not snapshot.get("release_blockers"):
        raise MedicalEvidenceError("Research-only evidence must state its release blockers.")


def validate(root: Path) -> tuple[int, int]:
    medical_root = root / "docs" / "medical-device"
    documents = validate_document_index(root, medical_root / "DOCUMENT_INDEX.csv")
    gates = validate_release_manifest(root, medical_root / "RELEASE_READINESS.json")
    validate_model_evidence(medical_root / "model-data" / "RESEARCH_EVIDENCE_SNAPSHOT.json")
    return documents, gates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate medical-device document and evidence controls"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        documents, gates = validate(args.root.resolve())
    except (OSError, csv.Error, json.JSONDecodeError, MedicalEvidenceError) as error:
        raise SystemExit(f"MEDICAL EVIDENCE INVALID: {error}") from error
    print(f"MEDICAL EVIDENCE VALID: {documents} documents; {gates} release gates")


if __name__ == "__main__":
    main()
