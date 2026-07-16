from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import torch


class ModelEvidenceError(ValueError):
    """Raised when model or dataset evidence is missing or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ModelEvidenceError(f"Expected an object in {path}.")
    return value


def verify_dataset(data_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = data_dir / "manifest.json"
    provenance_path = data_dir / "provenance.json"
    manifest = load_object(manifest_path)
    provenance = load_object(provenance_path)
    arrays = manifest.get("arrays")
    if manifest.get("format") != "prepared-pannuke-v2" or not isinstance(arrays, list):
        raise ModelEvidenceError("Unsupported or incomplete prepared-dataset manifest.")
    for entry in arrays:
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            raise ModelEvidenceError("Dataset manifest contains an invalid array entry.")
        path = (data_dir / entry["file"]).resolve()
        if not path.is_relative_to(data_dir.resolve()) or not path.is_file():
            raise ModelEvidenceError(f"Dataset array is missing or outside its root: {path}")
        if sha256_file(path) != entry.get("sha256"):
            raise ModelEvidenceError(f"Dataset array digest mismatch: {path.name}")
    return manifest, provenance


def summarize_metrics(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {"epoch", "validation_loss", "validation_dice", "validation_iou"}
    if not rows or not required.issubset(rows[0]):
        raise ModelEvidenceError("Training metrics are empty or missing required columns.")
    try:
        parsed = [
            {
                "epoch": int(row["epoch"]),
                "validation_loss": float(row["validation_loss"]),
                "validation_dice": float(row["validation_dice"]),
                "validation_iou": float(row["validation_iou"]),
            }
            for row in rows
        ]
    except (TypeError, ValueError) as error:
        raise ModelEvidenceError("Training metrics contain an invalid numeric value.") from error
    return {
        "sha256": sha256_file(path),
        "epochs_recorded": len(parsed),
        "last_epoch": parsed[-1]["epoch"],
        "best_validation_iou": max(parsed, key=lambda row: row["validation_iou"]),
        "best_validation_dice": max(parsed, key=lambda row: row["validation_dice"]),
        "best_validation_loss": min(parsed, key=lambda row: row["validation_loss"]),
    }


def is_commercially_restricted(license_name: str) -> bool:
    normalized = license_name.upper().replace("_", "-")
    return "NONCOMMERCIAL" in normalized or "NON-COMMERCIAL" in normalized or "-NC" in normalized


def load_checkpoint_metadata(path: Path) -> dict[str, Any]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or checkpoint.get("artifact_type") != "attn-dist-inference":
        raise ModelEvidenceError("Checkpoint does not satisfy the inference artifact contract.")
    required = {"format_version", "epoch", "config", "validation", "dataset", "model_state_dict"}
    missing = required - checkpoint.keys()
    if missing:
        raise ModelEvidenceError(f"Checkpoint is missing fields: {sorted(missing)}")
    config = checkpoint["config"]
    if not isinstance(config, dict):
        raise ModelEvidenceError("Checkpoint config must be an object.")
    return {
        "sha256": sha256_file(path),
        "artifact_type": checkpoint["artifact_type"],
        "format_version": checkpoint["format_version"],
        "checkpoint_epoch_zero_based": checkpoint["epoch"],
        "planned_epochs": config.get("epochs"),
        "configuration": {
            key: config.get(key)
            for key in (
                "encoder",
                "model_name",
                "encoder_weights",
                "seed",
                "train_fold",
                "validation_fold",
                "test_fold",
            )
        },
        "validation": checkpoint["validation"],
        "dataset": checkpoint["dataset"],
    }


def build_evidence(data_dir: Path, checkpoint_path: Path, metrics_path: Path) -> dict[str, Any]:
    manifest, provenance = verify_dataset(data_dir)
    checkpoint = load_checkpoint_metadata(checkpoint_path)
    metrics = summarize_metrics(metrics_path)
    manifest_sha256 = sha256_file(data_dir / "manifest.json")
    checkpoint_manifest_sha256 = checkpoint["dataset"].get("manifest_sha256")
    if checkpoint_manifest_sha256 != manifest_sha256:
        raise ModelEvidenceError("Checkpoint does not reference the supplied dataset manifest.")
    planned_epochs = checkpoint.get("planned_epochs")
    training_complete = isinstance(planned_epochs, int) and metrics["last_epoch"] >= planned_epochs
    license_name = str(provenance.get("license", "unknown"))
    blockers = [
        "No locked held-out test-fold evaluation is present.",
        "No independent external multi-site validation is present.",
        "No prospective workflow validation is present.",
        "No clinical residual-risk acceptance is present.",
    ]
    if not training_complete:
        blockers.insert(0, "The recorded training run did not reach its configured epoch count.")
    if is_commercially_restricted(license_name):
        blockers.insert(0, "The source dataset license restricts commercial use.")
    return {
        "schema_version": 1,
        "artifact_status": "research_only",
        "release_disposition": "blocked",
        "dataset": {
            "source": provenance.get("source"),
            "revision": provenance.get("revision"),
            "license": license_name,
            "commercially_restricted": is_commercially_restricted(license_name),
            "sample_count": manifest.get("sample_count"),
            "fold_counts": manifest.get("fold_counts"),
            "manifest_sha256": manifest_sha256,
            "provenance_sha256": sha256_file(data_dir / "provenance.json"),
            "arrays": manifest.get("arrays"),
        },
        "model": checkpoint,
        "training_metrics": metrics,
        "training_complete": training_complete,
        "clinical_evidence": {
            "held_out_test_fold": "not_performed",
            "external_validation": "not_performed",
            "prospective_validation": "not_performed",
        },
        "release_blockers": blockers,
    }


def write_atomic(path: Path, evidence: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(evidence, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build verified model/data evidence")
    parser.add_argument("--data-dir", type=Path, default=Path("data/pannuke"))
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("outputs_v2/e03_bounded_distance/checkpoints/best_iou.pt"),
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=Path("outputs_v2/e03_bounded_distance/logs/metrics.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/medical-device/model-data/RESEARCH_EVIDENCE_SNAPSHOT.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evidence = build_evidence(args.data_dir, args.checkpoint, args.metrics)
    write_atomic(args.output, evidence)
    print(f"Wrote verified research evidence to {args.output}")


if __name__ == "__main__":
    main()
