from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from src.utils.metrics import (
    ClinicalInstanceMetrics,
    calculate_clinical_instance_metrics,
    calculate_metrics,
)

REQUIRED_HIERARCHY = (
    "site_id",
    "patient_id",
    "specimen_id",
    "slide_id",
    "scan_id",
    "region_id",
)
MACRO_METRICS = (
    "aji",
    "aji_plus",
    "pq",
    "segmentation_quality",
    "recognition_quality",
    "detection_precision",
    "detection_recall",
    "detection_f1",
    "object_false_positive_rate",
    "object_false_negative_rate",
)


@dataclass(frozen=True)
class RegionEvidence:
    hierarchy: dict[str, str]
    subgroups: dict[str, str]
    instance: ClinicalInstanceMetrics | None
    pixel: dict[str, float] | None
    failure_to_return: bool = False
    failure_reason: str | None = None

    def to_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            **self.hierarchy,
            **self.subgroups,
            "failure_to_return": self.failure_to_return,
            "failure_reason": self.failure_reason,
        }
        if self.instance is not None:
            row.update(asdict(self.instance))
        if self.pixel is not None:
            row.update(
                {
                    "pixel_dice": self.pixel["Dice"],
                    "pixel_iou": self.pixel["IoU"],
                    "pixel_precision": self.pixel["Precision"],
                    "pixel_recall": self.pixel["Recall"],
                }
            )
        return row


def _validate_hierarchy(hierarchy: Mapping[str, str]) -> dict[str, str]:
    missing = [field for field in REQUIRED_HIERARCHY if not str(hierarchy.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Evaluation hierarchy is missing required identifiers: {missing}")
    return {field: str(hierarchy[field]).strip() for field in REQUIRED_HIERARCHY}


def evaluate_region(
    truth: np.ndarray,
    prediction: np.ndarray,
    hierarchy: Mapping[str, str],
    subgroups: Mapping[str, str] | None = None,
    match_iou: float = 0.5,
) -> tuple[RegionEvidence, list[dict[str, Any]]]:
    controlled_hierarchy = _validate_hierarchy(hierarchy)
    metrics, matches = calculate_clinical_instance_metrics(truth, prediction, match_iou)
    pixel = calculate_metrics(np.asarray(truth) > 0, np.asarray(prediction) > 0)
    evidence = RegionEvidence(
        hierarchy=controlled_hierarchy,
        subgroups={
            str(key): str(value).strip()
            for key, value in (subgroups or {}).items()
            if str(key).strip()
        },
        instance=metrics,
        pixel=pixel,
    )
    object_rows = [
        {
            **controlled_hierarchy,
            **asdict(match),
            "match_iou_threshold": match_iou,
        }
        for match in matches
    ]
    return evidence, object_rows


def failed_region(
    hierarchy: Mapping[str, str],
    reason: str,
    subgroups: Mapping[str, str] | None = None,
) -> RegionEvidence:
    if not reason.strip():
        raise ValueError("A failed result must have a failure reason")
    return RegionEvidence(
        hierarchy=_validate_hierarchy(hierarchy),
        subgroups={str(key): str(value).strip() for key, value in (subgroups or {}).items()},
        instance=None,
        pixel=None,
        failure_to_return=True,
        failure_reason=reason.strip(),
    )


def validate_evidence_rows(rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError("At least one evaluation row is required")
    region_keys: set[tuple[str, ...]] = set()
    patient_sites: dict[str, str] = {}
    for row in rows:
        hierarchy = _validate_hierarchy(
            {field: str(row.get(field, "")) for field in REQUIRED_HIERARCHY}
        )
        region_key = tuple(hierarchy[field] for field in REQUIRED_HIERARCHY)
        if region_key in region_keys:
            raise ValueError(f"Duplicate evaluation region hierarchy: {region_key}")
        region_keys.add(region_key)
        patient = hierarchy["patient_id"]
        site = hierarchy["site_id"]
        prior_site = patient_sites.setdefault(patient, site)
        if prior_site != site:
            raise ValueError(
                f"patient_id {patient!r} occurs at multiple sites; use globally unique pseudonyms"
            )


def _patient_groups(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["patient_id"])].append(row)
    return groups


def _patient_macro(rows: Sequence[Mapping[str, Any]], metric: str) -> float:
    patient_values: list[float] = []
    for patient_rows in _patient_groups(rows).values():
        values = [
            float(row[metric])
            for row in patient_rows
            if not bool(row.get("failure_to_return")) and row.get(metric) is not None
        ]
        if values:
            patient_values.append(float(np.mean(values)))
    return float(np.mean(patient_values)) if patient_values else float("nan")


def _pooled_detection(rows: Sequence[Mapping[str, Any]], metric: str) -> float:
    valid = [row for row in rows if not bool(row.get("failure_to_return"))]
    true_positive = sum(int(row["true_positive"]) for row in valid)
    false_positive = sum(int(row["false_positive"]) for row in valid)
    false_negative = sum(int(row["false_negative"]) for row in valid)
    both_empty = not (true_positive or false_positive or false_negative)
    if metric == "precision":
        denominator = true_positive + false_positive
        return 1.0 if both_empty else true_positive / denominator if denominator else 0.0
    if metric == "recall":
        denominator = true_positive + false_negative
        return 1.0 if both_empty else true_positive / denominator if denominator else 1.0
    denominator = 2 * true_positive + false_positive + false_negative
    return 1.0 if both_empty else 2 * true_positive / denominator if denominator else 0.0


def _patient_count_error(rows: Sequence[Mapping[str, Any]], kind: str) -> float:
    values: list[float] = []
    for patient_rows in _patient_groups(rows).values():
        valid = [row for row in patient_rows if not bool(row.get("failure_to_return"))]
        if not valid:
            continue
        reference = sum(int(row["reference_count"]) for row in valid)
        predicted = sum(int(row["predicted_count"]) for row in valid)
        error = predicted - reference
        if kind == "signed":
            values.append(float(error))
        elif kind == "absolute":
            values.append(float(abs(error)))
        elif reference:
            values.append(error / reference)
    return float(np.mean(values)) if values else float("nan")


def estimate_statistics(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    validate_evidence_rows(rows)
    statistics = {
        f"patient_macro_{metric}": _patient_macro(rows, metric) for metric in MACRO_METRICS
    }
    statistics.update(
        {
            "pooled_detection_precision": _pooled_detection(rows, "precision"),
            "pooled_detection_recall": _pooled_detection(rows, "recall"),
            "pooled_detection_f1": _pooled_detection(rows, "f1"),
            "patient_mean_signed_count_error": _patient_count_error(rows, "signed"),
            "patient_mean_absolute_count_error": _patient_count_error(rows, "absolute"),
            "patient_mean_relative_count_error": _patient_count_error(rows, "relative"),
            "failure_to_return_rate": sum(
                bool(row.get("failure_to_return")) for row in rows
            )
            / len(rows),
        }
    )
    return statistics


def _clustered_rows(
    rows: Sequence[Mapping[str, Any]], generator: np.random.Generator
) -> list[Mapping[str, Any]]:
    site_patients: dict[str, dict[str, list[Mapping[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        site_patients[str(row["site_id"])][str(row["patient_id"])].append(row)
    sampled: list[Mapping[str, Any]] = []
    for patients in site_patients.values():
        identifiers = sorted(patients)
        chosen = generator.choice(identifiers, size=len(identifiers), replace=True)
        for identifier in chosen:
            sampled.extend(patients[str(identifier)])
    return sampled


def clustered_confidence_intervals(
    rows: Sequence[Mapping[str, Any]],
    samples: int = 10_000,
    seed: int = 42,
    statistic: Callable[[Sequence[Mapping[str, Any]]], dict[str, float]] = estimate_statistics,
) -> dict[str, dict[str, float | list[float]]]:
    if samples < 1:
        raise ValueError("Bootstrap samples must be positive")
    validate_evidence_rows(rows)
    estimates = statistic(rows)
    replicates: dict[str, list[float]] = {name: [] for name in estimates}
    generator = np.random.default_rng(seed)
    for _ in range(samples):
        sampled = statistic(_clustered_rows(rows, generator))
        for name, value in sampled.items():
            if np.isfinite(value):
                replicates[name].append(float(value))
    result: dict[str, dict[str, float | list[float]]] = {}
    for name, estimate in estimates.items():
        values = replicates[name]
        interval = (
            [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]
            if values
            else [float("nan"), float("nan")]
        )
        result[name] = {"estimate": float(estimate), "ci95": interval}
    return result


def summarize_evidence(
    rows: Sequence[Mapping[str, Any]],
    subgroup_fields: Sequence[str] = (),
    bootstrap_samples: int = 10_000,
    seed: int = 42,
) -> dict[str, Any]:
    validate_evidence_rows(rows)
    summary: dict[str, Any] = {
        "denominators": {
            "sites": len({str(row["site_id"]) for row in rows}),
            "patients": len({str(row["patient_id"]) for row in rows}),
            "slides": len({str(row["slide_id"]) for row in rows}),
            "regions": len(rows),
            "evaluable_regions": sum(not bool(row.get("failure_to_return")) for row in rows),
            "reference_objects": sum(
                int(row.get("reference_count", 0))
                for row in rows
                if not bool(row.get("failure_to_return"))
            ),
            "predicted_objects": sum(
                int(row.get("predicted_count", 0))
                for row in rows
                if not bool(row.get("failure_to_return"))
            ),
        },
        "statistics": clustered_confidence_intervals(rows, bootstrap_samples, seed),
        "subgroups": {},
    }
    for field in subgroup_fields:
        groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in rows:
            value = str(row.get(field, "")).strip()
            groups[value or "not_recorded"].append(row)
        summary["subgroups"][field] = {
            value: {
                "denominators": {
                    "patients": len({str(row["patient_id"]) for row in group_rows}),
                    "slides": len({str(row["slide_id"]) for row in group_rows}),
                    "regions": len(group_rows),
                },
                "statistics": clustered_confidence_intervals(
                    group_rows, bootstrap_samples, seed
                ),
            }
            for value, group_rows in sorted(groups.items())
        }
    return summary
