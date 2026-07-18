from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

REQUIRED_FIELDS = {
    "site_id",
    "patient_id",
    "slide_id",
    "item_id",
    "condition_id",
    "replicate_id",
    "predicted_count",
    "output_sha256",
    "aji_plus",
    "pq",
}


def _mean_by_item_condition(
    rows: Sequence[Mapping[str, Any]], field: str
) -> dict[tuple[str, str], float]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["item_id"]), str(row["condition_id"]))].append(float(row[field]))
    return {key: float(np.mean(values)) for key, values in grouped.items()}


def _balanced_matrix(
    rows: Sequence[Mapping[str, Any]], field: str
) -> tuple[list[str], list[str], np.ndarray]:
    means = _mean_by_item_condition(rows, field)
    conditions = sorted({condition for _, condition in means})
    candidate_items = sorted({item for item, _ in means})
    items = [
        item
        for item in candidate_items
        if all((item, condition) in means for condition in conditions)
    ]
    if len(items) < 2 or len(conditions) < 2:
        raise ValueError("ICC requires at least two complete items and two conditions")
    matrix = np.asarray(
        [[means[(item, condition)] for condition in conditions] for item in items],
        dtype=np.float64,
    )
    return items, conditions, matrix


def icc_2_1(matrix: np.ndarray) -> float | None:
    values = np.asarray(matrix, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] < 2 or values.shape[1] < 2:
        raise ValueError("ICC(2,1) requires a matrix with at least two items and conditions")
    item_count, condition_count = values.shape
    grand_mean = float(values.mean())
    item_means = values.mean(axis=1)
    condition_means = values.mean(axis=0)
    ms_item = condition_count * float(np.sum((item_means - grand_mean) ** 2)) / (
        item_count - 1
    )
    ms_condition = item_count * float(
        np.sum((condition_means - grand_mean) ** 2)
    ) / (condition_count - 1)
    residual = (
        values
        - item_means[:, None]
        - condition_means[None, :]
        + grand_mean
    )
    ms_error = float(np.sum(residual**2)) / (
        (item_count - 1) * (condition_count - 1)
    )
    denominator = (
        ms_item
        + (condition_count - 1) * ms_error
        + condition_count * (ms_condition - ms_error) / item_count
    )
    return (ms_item - ms_error) / denominator if denominator else None


def analyze_repeatability(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Repeatability analysis requires at least one row")
    seen: set[tuple[str, str, str]] = set()
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        missing = REQUIRED_FIELDS - set(row)
        if missing:
            raise ValueError(f"Repeatability row is missing fields: {sorted(missing)}")
        key = (
            str(row["item_id"]).strip(),
            str(row["condition_id"]).strip(),
            str(row["replicate_id"]).strip(),
        )
        if not all(key):
            raise ValueError("Item, condition, and replicate identifiers must not be blank")
        if key in seen:
            raise ValueError(f"Duplicate item/condition/replicate row: {key}")
        if float(row["predicted_count"]) < 0:
            raise ValueError("Predicted counts must be non-negative")
        if any(not 0 <= float(row[field]) <= 1 for field in ("aji_plus", "pq")):
            raise ValueError("AJI+ and PQ must be in [0, 1]")
        output_hash = str(row["output_sha256"]).strip().lower()
        if len(output_hash) != 64 or any(
            character not in "0123456789abcdef" for character in output_hash
        ):
            raise ValueError("Output hashes must be hexadecimal SHA-256 values")
        seen.add(key)
        grouped[(key[0], key[1])].append(row)

    repeatability_cvs: list[float] = []
    deterministic_groups = 0
    for group_rows in grouped.values():
        counts = np.asarray([float(row["predicted_count"]) for row in group_rows])
        if len(counts) > 1 and counts.mean() != 0:
            repeatability_cvs.append(float(counts.std(ddof=1) / abs(counts.mean())))
        if len({str(row["output_sha256"]) for row in group_rows}) == 1:
            deterministic_groups += 1

    items, conditions, count_matrix = _balanced_matrix(rows, "predicted_count")
    result: dict[str, Any] = {
        "denominators": {
            "items": len(items),
            "conditions": len(conditions),
            "replicates": len(rows),
            "item_condition_groups": len(grouped),
        },
        "conditions": conditions,
        "count_icc_2_1": icc_2_1(count_matrix),
        "mean_within_condition_count_cv": (
            float(np.mean(repeatability_cvs)) if repeatability_cvs else None
        ),
        "exact_output_agreement_rate": deterministic_groups / len(grouped),
        "paired_condition_analysis": None,
    }
    if len(conditions) == 2:
        count_difference = count_matrix[:, 1] - count_matrix[:, 0]
        difference_sd = (
            float(count_difference.std(ddof=1)) if len(count_difference) > 1 else 0.0
        )
        paired: dict[str, Any] = {
            "condition_a": conditions[0],
            "condition_b": conditions[1],
            "count_bias_b_minus_a": float(count_difference.mean()),
            "count_limits_of_agreement_95": [
                float(count_difference.mean() - 1.96 * difference_sd),
                float(count_difference.mean() + 1.96 * difference_sd),
            ],
        }
        for metric in ("aji_plus", "pq"):
            _, _, matrix = _balanced_matrix(rows, metric)
            difference = matrix[:, 1] - matrix[:, 0]
            paired[f"mean_{metric}_difference_b_minus_a"] = float(difference.mean())
        result["paired_condition_analysis"] = paired
    return result
