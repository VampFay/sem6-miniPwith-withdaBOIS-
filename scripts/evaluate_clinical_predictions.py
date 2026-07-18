from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from src.clinical_evaluation import (
    REQUIRED_HIERARCHY,
    evaluate_region,
    failed_region,
    summarize_evidence,
)

SUBGROUP_FIELDS = (
    "tissue_type",
    "tumor_type",
    "scanner_model",
    "stain_protocol",
    "stain_batch",
    "density_group",
    "edge_condition",
    "artifact_condition",
)
REQUIRED_MANIFEST_FIELDS = {
    *REQUIRED_HIERARCHY,
    *SUBGROUP_FIELDS,
    "result_status",
    "truth_path",
    "prediction_path",
    "failure_reason",
}


def sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def validate_sha256(value: str, name: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{name} must be a 64-character hexadecimal SHA-256")
    return normalized


def controlled_path(root: Path, relative: str) -> Path:
    if not relative.strip():
        raise ValueError("A successful manifest row must provide truth and prediction paths")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Evaluation data path escapes the controlled data root: {relative}")
    if not path.is_file():
        raise ValueError(f"Evaluation data file is missing: {relative}")
    return path


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or ())
        missing = REQUIRED_MANIFEST_FIELDS - fields
        if missing:
            raise ValueError(f"Evaluation manifest is missing fields: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError("Evaluation manifest is empty")
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]], leading: tuple[str, ...]) -> None:
    discovered = {key for row in rows for key in row}
    fields = [field for field in leading if field in discovered or not discovered]
    fields.extend(sorted(discovered - set(fields)))
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def execute(args: argparse.Namespace) -> dict[str, Any]:
    candidate_sha256 = validate_sha256(args.candidate_sha256, "candidate_sha256")
    dataset_sha256 = validate_sha256(args.dataset_manifest_sha256, "dataset_manifest_sha256")
    manifest_rows = load_manifest(args.manifest)
    data_root = args.data_root.resolve()
    region_rows: list[dict[str, Any]] = []
    object_rows: list[dict[str, Any]] = []
    input_hashes: list[dict[str, str]] = []
    for source in manifest_rows:
        hierarchy = {field: source[field] for field in REQUIRED_HIERARCHY}
        subgroups = {field: source[field] for field in SUBGROUP_FIELDS}
        status = source["result_status"].strip().lower()
        if status == "failed":
            region_evidence = failed_region(hierarchy, source["failure_reason"], subgroups)
        elif status == "success":
            truth_path = controlled_path(data_root, source["truth_path"])
            prediction_path = controlled_path(data_root, source["prediction_path"])
            truth = np.load(truth_path, allow_pickle=False)
            prediction = np.load(prediction_path, allow_pickle=False)
            region_evidence, matches = evaluate_region(
                truth,
                prediction,
                hierarchy,
                subgroups,
                match_iou=args.match_iou,
            )
            object_rows.extend(matches)
            input_hashes.append(
                {
                    "region_id": hierarchy["region_id"],
                    "truth_sha256": sha256(truth_path),
                    "prediction_sha256": sha256(prediction_path),
                }
            )
        else:
            raise ValueError(
                f"result_status for region {hierarchy['region_id']!r} must be success or failed"
            )
        region_rows.append(region_evidence.to_row())

    summary = summarize_evidence(
        region_rows,
        subgroup_fields=SUBGROUP_FIELDS,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    args.output.mkdir(parents=True, exist_ok=False)
    write_rows(args.output / "per_region.csv", region_rows, REQUIRED_HIERARCHY)
    write_rows(
        args.output / "per_object.csv",
        object_rows,
        (*REQUIRED_HIERARCHY, "truth_id", "prediction_id", "status"),
    )
    evidence_document = {
        "schema_version": 1,
        "evidence_status": "analysis_output_requires_independent_review",
        "authorized_use": "research_only_unless_separately_approved",
        "study_id": args.study_id,
        "created_at": datetime.now(UTC).isoformat(),
        "candidate_model_sha256": candidate_sha256,
        "dataset_manifest_sha256": dataset_sha256,
        "analysis": {
            "source": "scripts.evaluate_clinical_predictions",
            "metric_dictionary": "MD-MDE-006@0.1",
            "strict_match_iou_greater_than": args.match_iou,
            "bootstrap": {
                "method": "site-stratified patient-cluster percentile",
                "samples": args.bootstrap_samples,
                "seed": args.seed,
            },
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "manifest": {
            "file": args.manifest.name,
            "sha256": sha256(args.manifest),
            "rows": len(manifest_rows),
        },
        "controlled_input_hashes": input_hashes,
        "summary": summary,
    }
    safe_evidence = cast(dict[str, Any], json_safe(evidence_document))
    (args.output / "summary.json").write_text(
        json.dumps(safe_evidence, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return safe_evidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score locked instance predictions with patient/slide-aware evidence"
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--dataset-manifest-sha256", required=True)
    parser.add_argument("--match-iou", type=float, default=0.5)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.study_id.strip():
        parser.error("--study-id must not be blank")
    if not 0 < args.match_iou <= 1:
        parser.error("--match-iou must be in the interval (0, 1]")
    if args.bootstrap_samples < 1:
        parser.error("--bootstrap-samples must be positive")
    return args


def main() -> None:
    args = parse_args()
    try:
        result = execute(args)
    except (OSError, csv.Error, json.JSONDecodeError, ValueError) as error:
        raise SystemExit(f"CLINICAL EVALUATION FAILED: {error}") from error
    print(json.dumps(result["summary"]["denominators"], indent=2))


if __name__ == "__main__":
    main()
