from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit
from scipy.stats import rankdata


@dataclass(frozen=True)
class PlattCalibrator:
    slope: float
    intercept: float
    input_semantics: str = "probability_of_correctness"

    def predict(self, confidence: Sequence[float] | np.ndarray) -> np.ndarray:
        probabilities = _probabilities(confidence)
        logits = logit(np.clip(probabilities, 1e-7, 1 - 1e-7))
        return np.asarray(expit(self.slope * logits + self.intercept), dtype=np.float64)

    def as_dict(self) -> dict[str, float | str]:
        return asdict(self)


def _probabilities(values: Sequence[float] | np.ndarray) -> np.ndarray:
    probabilities = np.asarray(values, dtype=np.float64)
    if probabilities.ndim != 1 or not len(probabilities):
        raise ValueError("Confidence values must be a non-empty one-dimensional array")
    if not np.isfinite(probabilities).all() or np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Confidence values must be finite probabilities in [0, 1]")
    return probabilities


def _binary(values: Sequence[int] | np.ndarray, name: str, length: int) -> np.ndarray:
    labels = np.asarray(values, dtype=np.int8)
    if labels.ndim != 1 or len(labels) != length or np.any((labels != 0) & (labels != 1)):
        raise ValueError(f"{name} must be a same-length one-dimensional binary array")
    return labels


def fit_platt_calibrator(
    confidence: Sequence[float] | np.ndarray,
    correct: Sequence[int] | np.ndarray,
) -> PlattCalibrator:
    probabilities = _probabilities(confidence)
    labels = _binary(correct, "correct", len(probabilities))
    if len(np.unique(labels)) != 2:
        raise ValueError("Calibration requires both correct and incorrect examples")
    logits = logit(np.clip(probabilities, 1e-7, 1 - 1e-7))

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        slope, intercept = parameters
        calibrated = expit(slope * logits + intercept)
        clipped = np.clip(calibrated, 1e-12, 1 - 1e-12)
        loss = -float(np.sum(labels * np.log(clipped) + (1 - labels) * np.log(1 - clipped)))
        residual = calibrated - labels
        gradient = np.array([np.sum(residual * logits), np.sum(residual)], dtype=np.float64)
        return loss, gradient

    fitted = minimize(
        objective,
        np.array([1.0, 0.0]),
        method="L-BFGS-B",
        jac=True,
    )
    if not fitted.success or not np.isfinite(fitted.x).all():
        raise ValueError(f"Calibration optimization failed: {fitted.message}")
    return PlattCalibrator(float(fitted.x[0]), float(fitted.x[1]))


def _roc_auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    positives = int(labels.sum())
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    ranks = rankdata(scores, method="average")
    positive_rank_sum = float(ranks[labels == 1].sum())
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _average_precision(labels: np.ndarray, scores: np.ndarray) -> float | None:
    positives = int(labels.sum())
    if not positives:
        return None
    order = np.argsort(-scores, kind="stable")
    ordered = labels[order]
    precision = np.cumsum(ordered) / np.arange(1, len(ordered) + 1)
    return float(np.sum(precision * ordered) / positives)


def uncertainty_metrics(
    calibrated_confidence: Sequence[float] | np.ndarray,
    correct: Sequence[int] | np.ndarray,
    severe_failure: Sequence[int] | np.ndarray,
    action_threshold: float,
    bins: int = 10,
) -> dict[str, float | None]:
    confidence = _probabilities(calibrated_confidence)
    labels = _binary(correct, "correct", len(confidence))
    severe = _binary(severe_failure, "severe_failure", len(confidence))
    if not 0 < action_threshold < 1:
        raise ValueError("Action threshold must be in the interval (0, 1)")
    if bins < 2:
        raise ValueError("Calibration bins must be at least two")
    edges = np.linspace(0.0, 1.0, bins + 1)
    bin_ids = np.minimum(np.digitize(confidence, edges[1:-1]), bins - 1)
    expected_calibration_error = 0.0
    maximum_calibration_error = 0.0
    for bin_id in range(bins):
        selected = bin_ids == bin_id
        if not selected.any():
            continue
        gap = abs(float(confidence[selected].mean() - labels[selected].mean()))
        expected_calibration_error += float(selected.mean()) * gap
        maximum_calibration_error = max(maximum_calibration_error, gap)
    failure = 1 - labels
    failure_score = 1 - confidence
    severe_count = int(severe.sum())
    severe_flagged = int(np.sum((confidence < action_threshold) & (severe == 1)))
    severe_reassured = int(np.sum((confidence >= action_threshold) & (severe == 1)))
    return {
        "brier_score": float(np.mean((confidence - labels) ** 2)),
        "expected_calibration_error": expected_calibration_error,
        "maximum_calibration_error": maximum_calibration_error,
        "failure_detection_auroc": _roc_auc(failure, failure_score),
        "failure_detection_auprc": _average_precision(failure, failure_score),
        "coverage_at_action_threshold": float(np.mean(confidence >= action_threshold)),
        "risk_at_action_threshold": (
            float(np.mean(failure[confidence >= action_threshold]))
            if np.any(confidence >= action_threshold)
            else None
        ),
        "severe_failure_sensitivity": severe_flagged / severe_count if severe_count else None,
        "false_reassurance_rate": severe_reassured / severe_count if severe_count else None,
    }


def risk_coverage_curve(
    calibrated_confidence: Sequence[float] | np.ndarray,
    correct: Sequence[int] | np.ndarray,
    points: int = 101,
) -> list[dict[str, float]]:
    confidence = _probabilities(calibrated_confidence)
    labels = _binary(correct, "correct", len(confidence))
    if points < 2:
        raise ValueError("Risk-coverage curve requires at least two points")
    order = np.argsort(-confidence, kind="stable")
    ordered_correct = labels[order]
    requested = np.unique(np.linspace(1, len(order), min(points, len(order)), dtype=int))
    return [
        {
            "coverage": int(count) / len(order),
            "risk": float(1 - ordered_correct[: int(count)].mean()),
            "minimum_confidence": float(confidence[order[int(count) - 1]]),
        }
        for count in requested
    ]


def clustered_uncertainty_intervals(
    rows: Sequence[Mapping[str, Any]],
    action_threshold: float,
    bins: int = 10,
    samples: int = 10_000,
    seed: int = 42,
) -> dict[str, dict[str, float | list[float | None] | None]]:
    if not rows or samples < 1:
        raise ValueError("Uncertainty bootstrap requires rows and positive samples")

    def calculate(selected: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
        return uncertainty_metrics(
            [float(row["calibrated_confidence"]) for row in selected],
            [int(row["correct"]) for row in selected],
            [int(row["severe_failure"]) for row in selected],
            action_threshold,
            bins,
        )

    estimates = calculate(rows)
    site_patients: dict[str, dict[str, list[Mapping[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        site = str(row.get("site_id", "")).strip()
        patient = str(row.get("patient_id", "")).strip()
        if not site or not patient:
            raise ValueError("Uncertainty rows require site_id and patient_id")
        site_patients[site][patient].append(row)
    replicates: dict[str, list[float]] = {name: [] for name in estimates}
    generator = np.random.default_rng(seed)
    for _ in range(samples):
        sampled: list[Mapping[str, Any]] = []
        for patients in site_patients.values():
            identifiers = sorted(patients)
            for identifier in generator.choice(
                identifiers, size=len(identifiers), replace=True
            ):
                sampled.extend(patients[str(identifier)])
        for name, value in calculate(sampled).items():
            if value is not None and np.isfinite(value):
                replicates[name].append(float(value))
    return {
        name: {
            "estimate": estimate,
            "ci95": (
                [
                    float(np.percentile(replicates[name], 2.5)),
                    float(np.percentile(replicates[name], 97.5)),
                ]
                if replicates[name]
                else [None, None]
            ),
        }
        for name, estimate in estimates.items()
    }
