from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
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
REQUIRED_WORKSTREAMS = {f"WS-{number:02d}" for number in range(1, 11)}
ALLOWED_WORKSTREAM_STATUSES = {"execution_pending", "in_progress", "ready", "blocked"}
REQUIRED_VALIDATION_STUDIES = {
    "PV-INT-001",
    "PV-RR-001",
    "PV-EXT-001",
    "PV-PRO-001",
    "PV-RDR-001",
    "PV-TOP-001",
}
ALLOWED_STUDY_STATUSES = {
    "protocol_draft",
    "approved_not_started",
    "in_progress",
    "database_locked",
    "reported",
    "closed",
    "not_required_approved",
    "blocked",
}
RECORD_SCHEMAS = {
    "docs/medical-device/governance/DECISION_REGISTER.csv": {
        "decision_id",
        "decision_type",
        "status",
        "decision",
        "owner",
        "approver",
        "evidence_refs",
    },
    "docs/medical-device/model-data/DATASET_INTAKE_REGISTER.csv": {
        "dataset_id",
        "status",
        "license_or_permission",
        "commercial_derivatives_allowed",
        "privacy_ethics_basis",
        "integrity_manifest_sha256",
        "owner",
    },
    "docs/medical-device/model-data/CLINICAL_STUDY_REGISTER.csv": {
        "study_id",
        "status",
        "stage",
        "candidate_model_sha256",
        "primary_endpoints",
        "acceptance_criteria",
        "result",
    },
    "docs/medical-device/qms/QMS_RECORD_REGISTER.csv": {
        "record_id",
        "record_type",
        "status",
        "owner",
        "approver",
        "evidence_location",
        "evidence_sha256",
    },
    "docs/medical-device/verification/ANOMALY_REGISTER.csv": {
        "anomaly_id",
        "status",
        "description",
        "patient_clinical_impact",
        "severity",
        "disposition_rationale",
        "owner",
    },
    "docs/medical-device/privacy-security/SECURITY_PRIVACY_EVIDENCE_REGISTER.csv": {
        "evidence_id",
        "evidence_type",
        "status",
        "release_site_scope",
        "artifact_sha256",
        "findings_critical",
        "findings_high",
        "owner",
    },
    "docs/medical-device/regulatory/MARKET_AUTHORIZATION_REGISTER.csv": {
        "market_id",
        "jurisdiction",
        "status",
        "final_intended_use_revision",
        "classification_rule_product_code",
        "pathway",
        "authorization_certificate_license_id",
        "regulatory_owner",
    },
    "docs/medical-device/human-factors/USER_COMPETENCY_REGISTER.csv": {
        "competency_record_id",
        "status",
        "site_id",
        "user_pseudonymous_id",
        "role",
        "product_release_model_scope",
        "authorization_scope",
        "authorized_by",
    },
    "docs/medical-device/site/SITE_EXECUTION_REGISTER.csv": {
        "site_execution_id",
        "status",
        "release_id",
        "container_digest",
        "model_sha256",
        "iq_started_completed_result",
        "oq_started_completed_result",
        "pq_started_completed_result",
        "go_live_at",
    },
    "docs/medical-device/postmarket/POSTMARKET_EVENT_REGISTER.csv": {
        "event_id",
        "event_type",
        "status",
        "awareness_at",
        "potential_actual_patient_harm",
        "reportability_markets_deadlines_rationale",
        "owner",
        "evidence_sha256",
    },
    "docs/medical-device/operations/DAILY_SAFETY_CHECKLIST.csv": {
        "control_id",
        "phase",
        "critical",
        "control",
        "acceptance_criteria",
        "action_if_failed",
        "status",
        "performed_at",
        "performed_by",
    },
}
REQUIRED_DAILY_CONTROLS = {
    *(f"DAY-{number:03d}" for number in range(1, 9)),
    *(f"CASE-{number:03d}" for number in range(1, 7)),
}
VALIDATION_TEMPLATE_SCHEMAS = {
    "docs/medical-device/model-data/EVALUATION_MANIFEST.template.csv": {
        "site_id",
        "patient_id",
        "specimen_id",
        "slide_id",
        "scan_id",
        "region_id",
        "result_status",
        "truth_path",
        "prediction_path",
        "failure_reason",
    },
    "docs/medical-device/model-data/UNCERTAINTY_CALIBRATION.template.csv": {
        "site_id",
        "patient_id",
        "confidence",
        "correct",
    },
    "docs/medical-device/model-data/UNCERTAINTY_EVALUATION.template.csv": {
        "site_id",
        "patient_id",
        "confidence",
        "correct",
        "severe_failure",
    },
    "docs/medical-device/model-data/REPEATABILITY_INPUT.template.csv": {
        "site_id",
        "patient_id",
        "slide_id",
        "item_id",
        "condition_id",
        "replicate_id",
        "predicted_count",
        "output_sha256",
        "aji_plus",
        "pq",
    },
    "docs/medical-device/model-data/SUBGROUP_AND_FAILURE_TAXONOMY.csv": {
        "taxonomy_id",
        "kind",
        "name",
        "status",
        "locked_definition",
        "required_metadata",
        "primary_failure_measures",
        "clinical_disposition",
        "owner",
        "approver",
    },
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


def _is_sha256(value: str) -> bool:
    normalized = value.strip().lower()
    return len(normalized) == 64 and all(
        character in "0123456789abcdef" for character in normalized
    )


def validate_model_validation_controls(root: Path) -> int:
    for relative, required_fields in VALIDATION_TEMPLATE_SCHEMAS.items():
        path = _inside_file(root, relative)
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream)
            try:
                fields = {field.strip() for field in next(reader)}
            except StopIteration as error:
                raise MedicalEvidenceError(f"Validation template is empty: {relative}") from error
        missing = required_fields - fields
        if missing:
            raise MedicalEvidenceError(
                f"Validation template {relative} is missing fields: {sorted(missing)}"
            )

    frozen_template = _load_json(
        _inside_file(
            root, "docs/medical-device/model-data/FROZEN_MODEL_CARD.template.json"
        )
    )
    if (
        frozen_template.get("schema_version") != 1
        or frozen_template.get("status") != "template_not_frozen"
        or frozen_template.get("candidate_id") is not None
    ):
        raise MedicalEvidenceError(
            "Frozen-model template could be mistaken for a frozen candidate."
        )
    topology_template = _load_json(
        _inside_file(root, "docs/medical-device/site/TOPOLOGY_MANIFEST.template.json")
    )
    if (
        topology_template.get("schema_version") != 1
        or topology_template.get("status") != "template_not_frozen"
        or topology_template.get("topology_id") is not None
    ):
        raise MedicalEvidenceError("Topology template could be mistaken for a frozen topology.")

    register = _inside_file(
        root, "docs/medical-device/model-data/CLINICAL_STUDY_REGISTER.csv"
    )
    with register.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required_study_fields = {
        "study_id",
        "status",
        "candidate_model_sha256",
        "dataset_manifest_sha256",
        "first_subject_or_analysis_date",
        "database_lock_date",
        "report_id",
        "result",
        "clinical_statistical_approvers",
        "approval_date",
    }
    if not rows or required_study_fields - set(rows[0]):
        raise MedicalEvidenceError(
            "Clinical validation study register is empty or has an invalid schema."
        )
    identifiers = [row["study_id"].strip() for row in rows]
    if set(identifiers) != REQUIRED_VALIDATION_STUDIES or len(identifiers) != len(set(identifiers)):
        raise MedicalEvidenceError(
            f"Clinical validation study set differs from the controlled set: {sorted(identifiers)}"
        )
    for row in rows:
        identifier = row["study_id"].strip()
        status = row["status"].strip()
        if status not in ALLOWED_STUDY_STATUSES:
            raise MedicalEvidenceError(
                f"Clinical study {identifier} has invalid status {status!r}."
            )
        if status == "protocol_draft" and (
            row["result"].strip() != "not_executed"
            or row["first_subject_or_analysis_date"].strip()
            or row["database_lock_date"].strip()
            or row["report_id"].strip()
            or row["approval_date"].strip()
        ):
            raise MedicalEvidenceError(
                f"Draft clinical study {identifier} contains execution or approval claims."
            )
        if status in {"reported", "closed"}:
            if not _is_sha256(row["candidate_model_sha256"]) or not _is_sha256(
                row["dataset_manifest_sha256"]
            ):
                raise MedicalEvidenceError(
                    f"Reported clinical study {identifier} lacks candidate/dataset hashes."
                )
            if (
                not row["report_id"].strip()
                or row["result"].strip() in {"", "not_executed"}
                or not row["first_subject_or_analysis_date"].strip()
                or not row["database_lock_date"].strip()
                or "unassigned" in row["clinical_statistical_approvers"].lower()
            ):
                raise MedicalEvidenceError(
                    f"Reported clinical study {identifier} lacks dates, report, "
                    "result, or approvers."
                )
        if status == "closed" and not row["approval_date"].strip():
            raise MedicalEvidenceError(
                f"Closed clinical study {identifier} has no approval date."
            )
        if status == "not_required_approved" and (
            identifier != "PV-RDR-001"
            or not row["result"].strip()
            or row["result"].strip() == "not_executed"
            or "unassigned" in row["clinical_statistical_approvers"].lower()
            or not row["approval_date"].strip()
        ):
            raise MedicalEvidenceError(
                "Only the reader study may be dispositioned not-required with signed rationale."
            )
    return len(rows)


def verify_clinical_release_evidence(root: Path) -> None:
    """Fail closed if draft/templates are presented as completed clinical evidence."""
    validate_model_validation_controls(root)
    register = root / "docs/medical-device/model-data/CLINICAL_STUDY_REGISTER.csv"
    with register.open(newline="", encoding="utf-8") as stream:
        rows = {row["study_id"]: row for row in csv.DictReader(stream)}
    required_closed = {"PV-INT-001", "PV-RR-001", "PV-EXT-001", "PV-PRO-001"}
    incomplete = [
        identifier
        for identifier in sorted(required_closed)
        if rows[identifier]["status"] != "closed"
    ]
    reader_status = rows["PV-RDR-001"]["status"]
    if reader_status not in {"closed", "not_required_approved"}:
        incomplete.append("PV-RDR-001")
    if incomplete:
        raise MedicalEvidenceError(
            f"Clinical release evidence is not completed and approved: {incomplete}"
        )
    completed_ids = set(required_closed)
    if reader_status == "closed":
        completed_ids.add("PV-RDR-001")
    unsuccessful = [
        identifier
        for identifier in sorted(completed_ids)
        if rows[identifier]["result"].strip().lower()
        not in {"passed", "met_acceptance_criteria"}
    ]
    if unsuccessful:
        raise MedicalEvidenceError(
            f"Clinical studies did not record approved success: {unsuccessful}"
        )
    candidate_hashes = {
        rows[identifier]["candidate_model_sha256"].strip().lower()
        for identifier in completed_ids
    }
    if len(candidate_hashes) != 1:
        raise MedicalEvidenceError(
            "Completed clinical studies do not evaluate one identical frozen candidate."
        )
    candidate_hash = next(iter(candidate_hashes))
    model_card_path = root / "docs/medical-device/model-data/FROZEN_MODEL_CARD.json"
    if not model_card_path.is_file():
        raise MedicalEvidenceError("Clinical release has no completed frozen model card.")
    model_card = _load_json(model_card_path)
    model = model_card.get("model")
    software = model_card.get("software")
    data = model_card.get("data")
    if (
        model_card.get("schema_version") != 1
        or model_card.get("status") != "frozen"
        or not isinstance(model, dict)
        or not _is_sha256(str(model.get("sha256", "")))
        or str(model.get("sha256", "")).strip().lower() != candidate_hash
        or not isinstance(software, dict)
        or not str(software.get("source_commit", "")).strip()
        or not isinstance(data, dict)
        or not _is_sha256(str(data.get("internal_test_manifest_sha256", "")))
        or not model_card.get("quality_approval")
    ):
        raise MedicalEvidenceError("Completed frozen model card is incomplete or invalid.")


def validate_record_templates(root: Path) -> int:
    for relative, required_fields in RECORD_SCHEMAS.items():
        path = _inside_file(root, relative)
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream)
            try:
                header = next(reader)
            except StopIteration as error:
                raise MedicalEvidenceError(
                    f"Operational record template is empty: {relative}"
                ) from error
        normalized = {field.strip() for field in header}
        missing = required_fields - normalized
        if missing:
            raise MedicalEvidenceError(
                f"Operational record template {relative} is missing fields: {sorted(missing)}"
            )

    checklist_path = root / "docs/medical-device/operations/DAILY_SAFETY_CHECKLIST.csv"
    with checklist_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    identifiers = [row["control_id"].strip() for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise MedicalEvidenceError("Daily-safety control identifiers must be unique.")
    if set(identifiers) != REQUIRED_DAILY_CONTROLS:
        raise MedicalEvidenceError(
            "Daily-safety control set differs from the controlled set: "
            f"{sorted(identifiers)}"
        )
    noncritical = [
        row["control_id"] for row in rows if row.get("critical", "").strip().lower() != "yes"
    ]
    if noncritical:
        raise MedicalEvidenceError(
            f"Controlled daily-safety checks must remain critical: {noncritical}"
        )
    return len(RECORD_SCHEMAS)


def validate_execution_workstreams(
    root: Path, manifest_path: Path, release_manifest_path: Path
) -> int:
    manifest = _load_json(manifest_path)
    workstreams = manifest.get("workstreams")
    if manifest.get("schema_version") != 1 or not isinstance(workstreams, list):
        raise MedicalEvidenceError("Execution-workstream manifest has an invalid schema.")
    if manifest.get("authorized_use") not in {"research_only", "clinical_authorized"}:
        raise MedicalEvidenceError("Execution-workstream manifest has an invalid authorized use.")
    identifiers = [
        str(workstream.get("id")) for workstream in workstreams if isinstance(workstream, dict)
    ]
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != REQUIRED_WORKSTREAMS:
        raise MedicalEvidenceError(
            f"Execution workstream set differs from the controlled set: {sorted(identifiers)}"
        )

    dependencies_by_id: dict[str, set[str]] = {}
    status_by_id: dict[str, str] = {}
    referenced_templates: set[str] = set()
    for workstream in workstreams:
        if not isinstance(workstream, dict):
            raise MedicalEvidenceError("Execution manifest contains a non-object workstream.")
        identifier = str(workstream["id"])
        status = str(workstream.get("status", ""))
        if status not in ALLOWED_WORKSTREAM_STATUSES:
            raise MedicalEvidenceError(
                f"Workstream {identifier} has invalid status {status!r}."
            )
        status_by_id[identifier] = status
        owner = str(workstream.get("owner", "")).strip()
        approver = str(workstream.get("approver", "")).strip()
        if not owner or not approver or not str(workstream.get("title", "")).strip():
            raise MedicalEvidenceError(f"Workstream {identifier} has incomplete control data.")
        if status == "ready" and (
            "unassigned" in owner.lower() or "unassigned" in approver.lower()
        ):
            raise MedicalEvidenceError(
                f"Ready workstream {identifier} still has unassigned accountability."
            )
        plan = workstream.get("execution_plan")
        if not isinstance(plan, str):
            raise MedicalEvidenceError(f"Workstream {identifier} has no execution plan.")
        _inside_file(root, plan)
        templates = workstream.get("record_templates")
        if not isinstance(templates, list) or not templates:
            raise MedicalEvidenceError(f"Workstream {identifier} has no record templates.")
        for template in templates:
            if not isinstance(template, str):
                raise MedicalEvidenceError(
                    f"Workstream {identifier} has a non-string record-template path."
                )
            _inside_file(root, template)
            referenced_templates.add(template)
        completed_evidence = workstream.get("completed_evidence")
        if not isinstance(completed_evidence, list) or not all(
            isinstance(evidence, str) for evidence in completed_evidence
        ):
            raise MedicalEvidenceError(
                f"Workstream {identifier} completed evidence is invalid."
            )
        for evidence in completed_evidence:
            _inside_file(root, evidence)
        approved_at = workstream.get("approved_at")
        if status == "ready":
            if not completed_evidence:
                raise MedicalEvidenceError(
                    f"Ready workstream {identifier} has no completed evidence."
                )
            if set(completed_evidence) & set(templates):
                raise MedicalEvidenceError(
                    f"Ready workstream {identifier} uses a blank template as completed evidence."
                )
            if not isinstance(approved_at, str):
                raise MedicalEvidenceError(
                    f"Ready workstream {identifier} has no approval timestamp."
                )
            try:
                approved_datetime = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
            except ValueError as error:
                raise MedicalEvidenceError(
                    f"Ready workstream {identifier} has an invalid approval timestamp."
                ) from error
            if approved_datetime.tzinfo is None:
                raise MedicalEvidenceError(
                    f"Ready workstream {identifier} approval timestamp has no timezone."
                )
        elif approved_at is not None:
            raise MedicalEvidenceError(
                f"Non-ready workstream {identifier} must not carry an approval timestamp."
            )
        dependencies = workstream.get("dependencies")
        if not isinstance(dependencies, list) or not all(
            isinstance(dependency, str) for dependency in dependencies
        ):
            raise MedicalEvidenceError(f"Workstream {identifier} dependencies are invalid.")
        dependency_set = set(dependencies)
        if identifier in dependency_set or not dependency_set.issubset(REQUIRED_WORKSTREAMS):
            raise MedicalEvidenceError(f"Workstream {identifier} has invalid dependencies.")
        dependencies_by_id[identifier] = dependency_set
        exit_criteria = workstream.get("exit_criteria")
        if not isinstance(exit_criteria, list) or not exit_criteria or not all(
            isinstance(criterion, str) and criterion.strip() for criterion in exit_criteria
        ):
            raise MedicalEvidenceError(f"Workstream {identifier} has invalid exit criteria.")

    if referenced_templates != set(RECORD_SCHEMAS):
        raise MedicalEvidenceError(
            "Execution manifest record-template set differs from the controlled schema set."
        )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str) -> None:
        if identifier in visiting:
            raise MedicalEvidenceError("Execution-workstream dependencies contain a cycle.")
        if identifier in visited:
            return
        visiting.add(identifier)
        for dependency in dependencies_by_id[identifier]:
            visit(dependency)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in REQUIRED_WORKSTREAMS:
        visit(identifier)

    prematurely_ready = [
        identifier
        for identifier, dependencies in dependencies_by_id.items()
        if status_by_id[identifier] == "ready"
        and any(status_by_id[dependency] != "ready" for dependency in dependencies)
    ]
    if prematurely_ready:
        raise MedicalEvidenceError(
            "Ready workstreams have incomplete dependencies: "
            f"{sorted(prematurely_ready)}"
        )

    release_manifest = _load_json(release_manifest_path)
    ready = all(workstream.get("status") == "ready" for workstream in workstreams)
    clinically_authorized = manifest.get("authorized_use") == "clinical_authorized"
    release_approved = release_manifest.get("disposition") == "release_approved"
    if clinically_authorized and (not ready or not release_approved):
        raise MedicalEvidenceError(
            "Clinical authorization conflicts with pending workstreams or blocked release."
        )
    if release_approved and not clinically_authorized:
        raise MedicalEvidenceError(
            "Approved release conflicts with research-only execution authorization."
        )
    return len(workstreams)


def validate(root: Path) -> tuple[int, int, int]:
    medical_root = root / "docs" / "medical-device"
    documents = validate_document_index(root, medical_root / "DOCUMENT_INDEX.csv")
    gates = validate_release_manifest(root, medical_root / "RELEASE_READINESS.json")
    validate_model_evidence(medical_root / "model-data" / "RESEARCH_EVIDENCE_SNAPSHOT.json")
    validate_model_validation_controls(root)
    workstreams = validate_execution_workstreams(
        root,
        medical_root / "EXECUTION_WORKSTREAMS.json",
        medical_root / "RELEASE_READINESS.json",
    )
    validate_record_templates(root)
    return documents, gates, workstreams


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate medical-device document and evidence controls"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        documents, gates, workstreams = validate(args.root.resolve())
    except (OSError, csv.Error, json.JSONDecodeError, MedicalEvidenceError) as error:
        raise SystemExit(f"MEDICAL EVIDENCE INVALID: {error}") from error
    print(
        f"MEDICAL EVIDENCE VALID: {documents} documents; {gates} release gates; "
        f"{workstreams} execution workstreams"
    )


if __name__ == "__main__":
    main()
