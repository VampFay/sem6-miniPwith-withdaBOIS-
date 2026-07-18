from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.benchmark_topology import Timing, load_topology, summarize_timings
from scripts.evaluate_uncertainty import execute
from src.uncertainty import (
    clustered_uncertainty_intervals,
    fit_platt_calibrator,
    risk_coverage_curve,
    uncertainty_metrics,
)


def test_platt_calibration_produces_bounded_probabilities() -> None:
    confidence = [0.05, 0.20, 0.35, 0.55, 0.70, 0.90]
    correct = [0, 0, 1, 0, 1, 1]
    calibrator = fit_platt_calibrator(confidence, correct)
    calibrated = calibrator.predict(confidence)
    assert np.isfinite(calibrated).all()
    assert np.all((calibrated > 0) & (calibrated < 1))


def test_uncertainty_metrics_measure_failure_detection_and_false_reassurance() -> None:
    confidence = [0.9, 0.8, 0.2, 0.1]
    correct = [1, 1, 0, 0]
    severe = [0, 0, 0, 1]
    metrics = uncertainty_metrics(confidence, correct, severe, action_threshold=0.5, bins=5)
    assert metrics["failure_detection_auroc"] == 1.0
    assert metrics["failure_detection_auprc"] == 1.0
    assert metrics["severe_failure_sensitivity"] == 1.0
    assert metrics["false_reassurance_rate"] == 0.0
    curve = risk_coverage_curve(confidence, correct, points=4)
    assert curve[-1]["coverage"] == 1.0
    assert curve[-1]["risk"] == 0.5


def test_uncertainty_intervals_resample_patients_within_site() -> None:
    rows = [
        {
            "site_id": f"SITE-{index % 2}",
            "patient_id": f"PAT-{index}",
            "calibrated_confidence": confidence,
            "correct": correct,
            "severe_failure": severe,
        }
        for index, (confidence, correct, severe) in enumerate(
            [(0.9, 1, 0), (0.7, 1, 0), (0.3, 0, 0), (0.1, 0, 1)]
        )
    ]
    result = clustered_uncertainty_intervals(
        rows, action_threshold=0.5, bins=5, samples=50, seed=9
    )
    assert result["failure_detection_auroc"]["estimate"] == 1.0
    assert result["false_reassurance_rate"]["estimate"] == 0.0
    assert len(result["brier_score"]["ci95"]) == 2


def write_uncertainty_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_uncertainty_execution_keeps_calibration_and_evaluation_disjoint(
    tmp_path: Path,
) -> None:
    calibration = tmp_path / "calibration.csv"
    evaluation = tmp_path / "evaluation.csv"
    write_uncertainty_csv(
        calibration,
        [
            {
                "site_id": "A",
                "patient_id": f"C-{index}",
                "confidence": confidence,
                "correct": correct,
            }
            for index, (confidence, correct) in enumerate(
                [(0.1, 0), (0.3, 1), (0.6, 0), (0.9, 1)]
            )
        ],
    )
    write_uncertainty_csv(
        evaluation,
        [
            {
                "site_id": "B",
                "patient_id": f"E-{index}",
                "confidence": confidence,
                "correct": correct,
                "severe_failure": severe,
            }
            for index, (confidence, correct, severe) in enumerate(
                [(0.1, 0, 1), (0.4, 0, 0), (0.6, 1, 0), (0.9, 1, 0)]
            )
        ],
    )
    output = tmp_path / "uncertainty"
    result = execute(
        argparse.Namespace(
            calibration=calibration,
            evaluation=evaluation,
            output=output,
            study_id="PV-UNC-TEST",
            candidate_sha256="a" * 64,
            score_name="object_correctness",
            action_threshold=0.5,
            bins=5,
            bootstrap_samples=20,
            seed=42,
        )
    )
    assert result["authorized_use"] == "research_only_unless_separately_approved"
    assert json.loads((output / "calibrator.json").read_text())["calibrator"]
    assert (output / "per_case.csv").is_file()


def test_topology_timing_summary_reports_tail_and_determinism() -> None:
    timings = [
        Timing(0, 0.08, 0.02, 0.10, "same"),
        Timing(1, 0.16, 0.04, 0.20, "same"),
        Timing(2, 0.24, 0.06, 0.30, "same"),
        Timing(3, 0.32, 0.08, 0.40, "same"),
    ]
    summary = summarize_timings(timings)
    assert summary["throughput_regions_per_second"] == pytest.approx(4.0)
    assert summary["end_to_end_seconds"]["p50"] == pytest.approx(0.25)
    assert summary["end_to_end_seconds"]["p99"] == pytest.approx(0.397)
    assert summary["deterministic_output"] is True


def test_topology_manifest_must_be_frozen(tmp_path: Path) -> None:
    path = tmp_path / "topology.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "template_not_frozen",
                "topology_id": None,
                "device_type": None,
                "model_sha256": None,
                "source_commit": None,
                "configuration_sha256": None,
                "hardware": {},
                "software": {},
            }
        )
    )
    with pytest.raises(ValueError, match="frozen"):
        load_topology(path)
