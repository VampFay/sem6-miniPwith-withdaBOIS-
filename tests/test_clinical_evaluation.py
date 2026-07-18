from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.evaluate_clinical_predictions import REQUIRED_MANIFEST_FIELDS, execute
from src.clinical_evaluation import (
    evaluate_region,
    failed_region,
    summarize_evidence,
    validate_evidence_rows,
)
from src.utils.metrics import calculate_clinical_instance_metrics


def hierarchy(region: str, patient: str = "PAT-1", site: str = "SITE-1") -> dict[str, str]:
    return {
        "site_id": site,
        "patient_id": patient,
        "specimen_id": f"SPEC-{patient}",
        "slide_id": f"SLIDE-{patient}",
        "scan_id": f"SCAN-{patient}",
        "region_id": region,
    }


def test_clinical_metrics_record_object_detection_and_count_errors() -> None:
    truth = np.zeros((5, 5), dtype=np.int32)
    prediction = np.zeros_like(truth)
    truth[0:2, 0:2] = 11
    truth[3:5, 3:5] = 22
    prediction[0:2, 0:2] = 101
    prediction[0:2, 3:5] = 202

    metrics, matches = calculate_clinical_instance_metrics(truth, prediction)

    assert metrics.true_positive == 1
    assert metrics.false_positive == 1
    assert metrics.false_negative == 1
    assert metrics.detection_precision == 0.5
    assert metrics.detection_recall == 0.5
    assert metrics.detection_f1 == 0.5
    assert metrics.reference_count == metrics.predicted_count == 2
    assert metrics.signed_count_error == metrics.absolute_count_error == 0
    assert {match.status for match in matches} == {
        "true_positive",
        "false_positive",
        "false_negative",
    }


def test_clinical_matching_is_strictly_greater_than_threshold() -> None:
    truth = np.zeros((2, 2), dtype=np.int32)
    prediction = np.zeros_like(truth)
    truth[0, :2] = 1
    prediction[0, 0] = 2

    metrics, matches = calculate_clinical_instance_metrics(truth, prediction, match_iou=0.5)

    assert metrics.true_positive == 0
    assert metrics.false_positive == metrics.false_negative == 1
    assert {match.status for match in matches} == {"false_positive", "false_negative"}


def test_empty_clinical_maps_have_explicit_neutral_rates() -> None:
    empty = np.zeros((4, 4), dtype=np.int32)
    metrics, matches = calculate_clinical_instance_metrics(empty, empty)
    assert not matches
    assert metrics.pq == metrics.detection_precision == metrics.detection_recall == 1.0
    assert metrics.object_false_positive_rate == metrics.object_false_negative_rate == 0.0
    assert metrics.relative_count_error is None


def test_summary_clusters_by_patient_and_reports_subgroups() -> None:
    truth = np.zeros((4, 4), dtype=np.int32)
    truth[1:3, 1:3] = 1
    perfect, _ = evaluate_region(
        truth,
        truth,
        hierarchy("REG-1", "PAT-1", "SITE-1"),
        {"tissue_type": "lung"},
    )
    missed, _ = evaluate_region(
        truth,
        np.zeros_like(truth),
        hierarchy("REG-2", "PAT-2", "SITE-2"),
        {"tissue_type": "breast"},
    )
    failed = failed_region(
        hierarchy("REG-3", "PAT-2", "SITE-2"),
        "controlled timeout",
        {"tissue_type": "breast"},
    )
    rows = [perfect.to_row(), missed.to_row(), failed.to_row()]

    summary = summarize_evidence(
        rows, subgroup_fields=("tissue_type",), bootstrap_samples=100, seed=7
    )

    assert summary["denominators"] == {
        "sites": 2,
        "patients": 2,
        "slides": 2,
        "regions": 3,
        "evaluable_regions": 2,
        "reference_objects": 2,
        "predicted_objects": 1,
    }
    assert summary["statistics"]["failure_to_return_rate"]["estimate"] == pytest.approx(1 / 3)
    assert set(summary["subgroups"]["tissue_type"]) == {"breast", "lung"}


def test_duplicate_region_and_cross_site_patient_are_rejected() -> None:
    base = {**hierarchy("REG-1"), "failure_to_return": True}
    with pytest.raises(ValueError, match="Duplicate"):
        validate_evidence_rows([base, dict(base)])
    other_site = {**base, "region_id": "REG-2", "site_id": "SITE-2"}
    with pytest.raises(ValueError, match="multiple sites"):
        validate_evidence_rows([base, other_site])


def test_controlled_prediction_evaluator_writes_auditable_outputs(tmp_path: Path) -> None:
    data_root = tmp_path / "controlled"
    data_root.mkdir()
    truth = np.zeros((4, 4), dtype=np.int32)
    truth[1:3, 1:3] = 1
    np.save(data_root / "truth.npy", truth, allow_pickle=False)
    np.save(data_root / "prediction.npy", truth, allow_pickle=False)
    manifest = tmp_path / "manifest.csv"
    row = {field: "" for field in REQUIRED_MANIFEST_FIELDS}
    row.update(
        {
            **hierarchy("REG-1"),
            "tissue_type": "lung",
            "scanner_model": "SCANNER-A",
            "stain_protocol": "H&E-A",
            "result_status": "success",
            "truth_path": "truth.npy",
            "prediction_path": "prediction.npy",
        }
    )
    with manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(REQUIRED_MANIFEST_FIELDS))
        writer.writeheader()
        writer.writerow(row)
    output = tmp_path / "evidence"
    args = argparse.Namespace(
        manifest=manifest,
        data_root=data_root,
        output=output,
        study_id="PV-TEST-001",
        candidate_sha256="a" * 64,
        dataset_manifest_sha256="b" * 64,
        match_iou=0.5,
        bootstrap_samples=20,
        seed=42,
    )

    result = execute(args)

    assert result["authorized_use"] == "research_only_unless_separately_approved"
    assert (output / "per_region.csv").is_file()
    assert (output / "per_object.csv").is_file()
    persisted = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert persisted["summary"]["denominators"]["patients"] == 1
    assert persisted["controlled_input_hashes"][0]["truth_sha256"]
