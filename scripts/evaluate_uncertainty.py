from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.uncertainty import (
    clustered_uncertainty_intervals,
    fit_platt_calibrator,
    risk_coverage_curve,
)

CALIBRATION_FIELDS = {"site_id", "patient_id", "confidence", "correct"}
EVALUATION_FIELDS = {*CALIBRATION_FIELDS, "severe_failure"}


def sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def load_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path.name} is missing fields: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name} is empty")
    for row in rows:
        if not row["site_id"].strip() or not row["patient_id"].strip():
            raise ValueError(f"{path.name} contains a blank site or patient identifier")
    return rows


def binary(value: str, name: str) -> int:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return 1
    if normalized in {"0", "false", "no"}:
        return 0
    raise ValueError(f"{name} must be a binary 0/1 or true/false value")


def validate_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError("candidate_sha256 must be a hexadecimal SHA-256")
    return normalized


def execute(args: argparse.Namespace) -> dict[str, Any]:
    candidate_sha256 = validate_sha256(args.candidate_sha256)
    if not args.study_id.strip() or not args.score_name.strip():
        raise ValueError("Study ID and score name must not be blank")
    calibration_rows = load_rows(args.calibration, CALIBRATION_FIELDS)
    evaluation_rows = load_rows(args.evaluation, EVALUATION_FIELDS)
    calibration_patients = {row["patient_id"].strip() for row in calibration_rows}
    evaluation_patients = {row["patient_id"].strip() for row in evaluation_rows}
    overlap = calibration_patients & evaluation_patients
    if overlap:
        raise ValueError(
            f"Calibration and evaluation patients overlap ({len(overlap)} identifiers)"
        )
    calibration_confidence = [float(row["confidence"]) for row in calibration_rows]
    calibration_correct = [binary(row["correct"], "correct") for row in calibration_rows]
    calibrator = fit_platt_calibrator(calibration_confidence, calibration_correct)

    raw_confidence = [float(row["confidence"]) for row in evaluation_rows]
    calibrated = calibrator.predict(raw_confidence)
    controlled_rows: list[dict[str, Any]] = []
    for source, confidence in zip(evaluation_rows, calibrated, strict=True):
        controlled_rows.append(
            {
                "site_id": source["site_id"].strip(),
                "patient_id": source["patient_id"].strip(),
                "raw_confidence": float(source["confidence"]),
                "calibrated_confidence": float(confidence),
                "correct": binary(source["correct"], "correct"),
                "severe_failure": binary(source["severe_failure"], "severe_failure"),
            }
        )
    intervals = clustered_uncertainty_intervals(
        controlled_rows,
        args.action_threshold,
        bins=args.bins,
        samples=args.bootstrap_samples,
        seed=args.seed,
    )
    curve = risk_coverage_curve(
        [float(row["calibrated_confidence"]) for row in controlled_rows],
        [int(row["correct"]) for row in controlled_rows],
    )
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / "per_case.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(controlled_rows[0]))
        writer.writeheader()
        writer.writerows(controlled_rows)
    calibrator_document = {
        "schema_version": 1,
        "status": "calibrator_requires_independent_review",
        "score_name": args.score_name,
        "candidate_model_sha256": candidate_sha256,
        "calibration_source_sha256": sha256(args.calibration),
        "calibration_rows": len(calibration_rows),
        "calibration_patients": len(calibration_patients),
        "calibrator": calibrator.as_dict(),
    }
    (args.output / "calibrator.json").write_text(
        json.dumps(calibrator_document, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema_version": 1,
        "evidence_status": "analysis_output_requires_independent_review",
        "authorized_use": "research_only_unless_separately_approved",
        "study_id": args.study_id,
        "created_at": datetime.now(UTC).isoformat(),
        "candidate_model_sha256": candidate_sha256,
        "score_name": args.score_name,
        "evaluation_source_sha256": sha256(args.evaluation),
        "evaluation_rows": len(evaluation_rows),
        "evaluation_patients": len(evaluation_patients),
        "action_threshold": args.action_threshold,
        "calibration_bins": args.bins,
        "bootstrap": {
            "method": "site-stratified patient-cluster percentile",
            "samples": args.bootstrap_samples,
            "seed": args.seed,
        },
        "metrics": intervals,
        "risk_coverage_curve": curve,
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fit and evaluate held-out probability-of-correctness calibration"
    )
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--score-name", required=True)
    parser.add_argument("--action-threshold", type=float, required=True)
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if len(args.candidate_sha256) != 64 or any(
        value not in "0123456789abcdef" for value in args.candidate_sha256.lower()
    ):
        parser.error("--candidate-sha256 must be a hexadecimal SHA-256")
    if not 0 < args.action_threshold < 1:
        parser.error("--action-threshold must be in the interval (0, 1)")
    if args.bins < 2 or args.bootstrap_samples < 1:
        parser.error("--bins must be at least two and --bootstrap-samples must be positive")
    return args


def main() -> None:
    args = parse_args()
    try:
        result = execute(args)
    except (OSError, csv.Error, ValueError) as error:
        raise SystemExit(f"UNCERTAINTY EVALUATION FAILED: {error}") from error
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
