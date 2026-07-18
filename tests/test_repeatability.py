from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pytest

from scripts.analyze_repeatability import execute
from src.repeatability import analyze_repeatability, icc_2_1


def balanced_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item_index, count in enumerate((10, 20, 30), start=1):
        for condition_index, condition in enumerate(("A", "B")):
            for replicate in (1, 2):
                rows.append(
                    {
                        "site_id": "SITE-1",
                        "patient_id": f"PAT-{item_index}",
                        "slide_id": f"SLIDE-{item_index}",
                        "item_id": f"ITEM-{item_index}",
                        "condition_id": condition,
                        "replicate_id": str(replicate),
                        "predicted_count": count + condition_index,
                        "output_sha256": (
                            f"{item_index}{condition_index}".ljust(64, "a")
                        ),
                        "aji_plus": 0.7 + 0.1 * condition_index,
                        "pq": 0.6 + 0.05 * condition_index,
                    }
                )
    return rows


def test_repeatability_analysis_reports_icc_bias_and_paired_metrics() -> None:
    result = analyze_repeatability(balanced_rows())
    assert result["denominators"] == {
        "items": 3,
        "conditions": 2,
        "replicates": 12,
        "item_condition_groups": 6,
    }
    assert result["count_icc_2_1"] == pytest.approx(0.9950248756)
    assert result["mean_within_condition_count_cv"] == 0.0
    assert result["exact_output_agreement_rate"] == 1.0
    paired = result["paired_condition_analysis"]
    assert paired["count_bias_b_minus_a"] == 1.0
    assert paired["count_limits_of_agreement_95"] == [1.0, 1.0]
    assert paired["mean_aji_plus_difference_b_minus_a"] == pytest.approx(0.1)
    assert paired["mean_pq_difference_b_minus_a"] == pytest.approx(0.05)


def test_repeatability_rejects_duplicate_or_invalid_rows() -> None:
    rows = balanced_rows()
    with pytest.raises(ValueError, match="Duplicate"):
        analyze_repeatability([rows[0], dict(rows[0])])
    invalid = [dict(row) for row in rows]
    invalid[0]["output_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="SHA-256"):
        analyze_repeatability(invalid)


def test_icc_requires_balanced_two_factor_matrix() -> None:
    with pytest.raises(ValueError, match="at least two"):
        icc_2_1([[1.0], [2.0]])  # type: ignore[arg-type]


def test_repeatability_script_writes_nonclinical_evidence(tmp_path: Path) -> None:
    input_path = tmp_path / "repeatability.csv"
    rows = balanced_rows()
    with input_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    output = tmp_path / "evidence"
    result = execute(
        argparse.Namespace(
            input=input_path,
            output=output,
            study_id="PV-RR-TEST",
            candidate_sha256="b" * 64,
        )
    )
    assert result["authorized_use"] == "research_only_unless_separately_approved"
    persisted = json.loads((output / "summary.json").read_text())
    assert persisted["analysis"]["denominators"]["items"] == 3
