from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from scripts.generate_sbom import SbomGenerationError, sha256_file, validate_sbom
from src.provenance import AuditStore
from src.runtime import RuntimeConfig, RuntimeConfigurationError, read_verified_checkpoint

GateStatus = Literal["pending", "approved", "rejected"]


class ReleaseGateError(ValueError):
    """Raised when release evidence is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class ReleaseGate:
    gate_id: str
    title: str
    required: bool
    status: GateStatus
    owner: str
    evidence: tuple[str, ...]
    approver: str | None
    approved_at: str | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ReleaseGate:
        required_fields = {"id", "title", "required", "status", "owner", "evidence"}
        missing = required_fields - value.keys()
        if missing:
            raise ReleaseGateError(f"Release gate is missing fields: {sorted(missing)}")
        status = value["status"]
        if status not in {"pending", "approved", "rejected"}:
            raise ReleaseGateError(f"Gate {value['id']} has an invalid status: {status}")
        return cls(
            gate_id=str(value["id"]),
            title=str(value["title"]),
            required=bool(value["required"]),
            status=status,
            owner=str(value["owner"]),
            evidence=tuple(str(path) for path in value["evidence"]),
            approver=str(value["approver"]) if value.get("approver") else None,
            approved_at=str(value["approved_at"]) if value.get("approved_at") else None,
        )


def load_release_gates(manifest: Path, root: Path) -> list[ReleaseGate]:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ReleaseGateError("Unsupported release-readiness schema version.")
    gates = [ReleaseGate.from_dict(value) for value in payload.get("gates", [])]
    if not gates:
        raise ReleaseGateError("Release-readiness manifest contains no gates.")
    identifiers = [gate.gate_id for gate in gates]
    if len(identifiers) != len(set(identifiers)):
        raise ReleaseGateError("Release gate identifiers must be unique.")
    for gate in gates:
        if not gate.owner:
            raise ReleaseGateError(f"Gate {gate.gate_id} has no accountable owner.")
        if gate.status != "approved":
            continue
        if "unassigned" in gate.owner.lower():
            raise ReleaseGateError(
                f"Approved gate {gate.gate_id} still has an unassigned owner."
            )
        if not gate.approver or not gate.approved_at:
            raise ReleaseGateError(
                f"Approved gate {gate.gate_id} requires approver and approved_at."
            )
        try:
            datetime.fromisoformat(gate.approved_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ReleaseGateError(
                f"Approved gate {gate.gate_id} has an invalid approval timestamp."
            ) from error
        if not gate.evidence:
            raise ReleaseGateError(f"Approved gate {gate.gate_id} has no evidence.")
        root_resolved = root.resolve()
        outside = [
            path
            for path in gate.evidence
            if not (root / path).resolve().is_relative_to(root_resolved)
        ]
        if outside:
            raise ReleaseGateError(
                f"Approved gate {gate.gate_id} references evidence outside "
                f"the repository: {outside}"
            )
        missing = [path for path in gate.evidence if not (root / path).resolve().is_file()]
        if missing:
            raise ReleaseGateError(
                f"Approved gate {gate.gate_id} references missing evidence: {missing}"
            )
    return gates


def verify_release_disposition(manifest: Path) -> None:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("disposition") != "release_approved":
        raise ReleaseGateError(
            "Release-readiness disposition must be 'release_approved'."
        )


def verify_sbom_receipt(receipt_path: Path, root: Path) -> None:
    root_resolved = root.resolve()
    receipt_path = receipt_path.resolve()
    if not receipt_path.is_relative_to(root_resolved):
        raise ReleaseGateError("SBOM receipt must be contained within the release repository.")
    suffix = ".receipt.json"
    if not receipt_path.name.endswith(suffix):
        raise ReleaseGateError("SBOM receipt filename must end with '.receipt.json'.")
    sbom_path = Path(str(receipt_path).removesuffix(suffix))
    requirements_path = root_resolved / "requirements.lock"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseGateError("SBOM receipt is missing or invalid.") from error
    required = {
        "schema_version": 1,
        "audit_exit_code": 0,
        "release_acceptable": True,
        "vulnerability_count": 0,
    }
    if any(receipt.get(key) != value for key, value in required.items()):
        raise ReleaseGateError("SBOM receipt does not record an acceptable vulnerability audit.")
    if not isinstance(receipt.get("generator"), str) or not receipt["generator"].strip():
        raise ReleaseGateError("SBOM receipt has no generator identity.")
    try:
        generated_at = datetime.fromisoformat(
            str(receipt["generated_at_utc"]).replace("Z", "+00:00")
        )
    except (KeyError, ValueError) as error:
        raise ReleaseGateError("SBOM receipt has an invalid generation timestamp.") from error
    if generated_at.tzinfo is None:
        raise ReleaseGateError("SBOM receipt generation timestamp must include a timezone.")
    try:
        component_count, vulnerability_count = validate_sbom(sbom_path)
    except SbomGenerationError as error:
        raise ReleaseGateError("Approved CycloneDX SBOM is missing or invalid.") from error
    if vulnerability_count != 0 or receipt.get("component_count") != component_count:
        raise ReleaseGateError("SBOM receipt counts do not match the CycloneDX document.")
    if not requirements_path.is_file():
        raise ReleaseGateError("Release repository has no requirements.lock.")
    if receipt.get("requirements_sha256") != sha256_file(requirements_path):
        raise ReleaseGateError("SBOM receipt does not match requirements.lock.")
    if receipt.get("sbom_sha256") != sha256_file(sbom_path):
        raise ReleaseGateError("SBOM receipt does not match the CycloneDX document.")


def verify_controlled_runtime(root: Path) -> None:
    config = RuntimeConfig.from_environment()
    if not config.is_controlled:
        raise ReleaseGateError("Release verification requires controlled operating mode.")
    checkpoint_value = os.getenv("ATTNDIST_CHECKPOINT", "").strip()
    if not checkpoint_value:
        raise ReleaseGateError("ATTNDIST_CHECKPOINT must identify the release artifact.")
    read_verified_checkpoint(Path(checkpoint_value), config.approved_checkpoint_sha256)
    if config.audit_dir is None:
        raise ReleaseGateError("Controlled runtime has no audit directory.")
    AuditStore(config.audit_dir).ensure_ready()
    sbom_receipt = os.getenv("ATTNDIST_SBOM_RECEIPT", "").strip()
    if not sbom_receipt:
        raise ReleaseGateError("ATTNDIST_SBOM_RECEIPT must identify approved SBOM evidence.")
    receipt_path = Path(sbom_receipt)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    verify_sbom_receipt(receipt_path, root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail closed unless every release gate is approved"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/medical-device/RELEASE_READINESS.json"),
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--runtime", action="store_true", help="also verify controlled runtime")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        gates = load_release_gates(args.manifest, args.root)
        blockers = [gate for gate in gates if gate.required and gate.status != "approved"]
        if blockers:
            detail = ", ".join(f"{gate.gate_id}={gate.status}" for gate in blockers)
            raise ReleaseGateError(f"Required release gates are not approved: {detail}")
        verify_release_disposition(args.manifest)
        if args.runtime:
            verify_controlled_runtime(args.root)
    except (OSError, json.JSONDecodeError, RuntimeConfigurationError, ReleaseGateError) as error:
        raise SystemExit(f"RELEASE BLOCKED: {error}") from error
    print(f"RELEASE GATES PASSED: {len(gates)} controlled requirements approved")


if __name__ == "__main__":
    main()
