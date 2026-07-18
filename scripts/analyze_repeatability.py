from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.repeatability import REQUIRED_FIELDS, analyze_repeatability


def sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def execute(args: argparse.Namespace) -> dict[str, Any]:
    candidate_sha256 = args.candidate_sha256.strip().lower()
    if len(candidate_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in candidate_sha256
    ):
        raise ValueError("candidate_model_sha256 must be a hexadecimal SHA-256")
    if not args.study_id.strip():
        raise ValueError("Study ID must not be blank")
    with args.input.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED_FIELDS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Repeatability input is missing fields: {sorted(missing)}")
        rows = list(reader)
    analysis = analyze_repeatability(rows)
    result = {
        "schema_version": 1,
        "evidence_status": "analysis_output_requires_independent_review",
        "authorized_use": "research_only_unless_separately_approved",
        "study_id": args.study_id,
        "created_at": datetime.now(UTC).isoformat(),
        "candidate_model_sha256": candidate_sha256,
        "input_sha256": sha256(args.input),
        "analysis": analysis,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "summary.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze count and segmentation repeatability/reproducibility"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    args = parser.parse_args()
    if len(args.candidate_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in args.candidate_sha256.lower()
    ):
        parser.error("--candidate-sha256 must be a hexadecimal SHA-256")
    return args


def main() -> None:
    args = parse_args()
    try:
        result = execute(args)
    except (OSError, csv.Error, ValueError) as error:
        raise SystemExit(f"REPEATABILITY ANALYSIS FAILED: {error}") from error
    print(json.dumps(result["analysis"], indent=2))


if __name__ == "__main__":
    main()
