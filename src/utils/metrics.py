from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass(frozen=True)
class BinaryMetrics:
    dice: float
    iou: float
    precision: float
    recall: float


@dataclass(frozen=True)
class InstanceMetrics:
    aji: float
    aji_plus: float
    pq: float
    detection_f1: float
    segmentation_quality: float
    recognition_quality: float


@dataclass(frozen=True)
class ClinicalInstanceMetrics:
    aji: float
    aji_plus: float
    pq: float
    segmentation_quality: float
    recognition_quality: float
    true_positive: int
    false_positive: int
    false_negative: int
    detection_precision: float
    detection_recall: float
    detection_f1: float
    reference_count: int
    predicted_count: int
    signed_count_error: int
    absolute_count_error: int
    relative_count_error: float | None
    object_false_positive_rate: float
    object_false_negative_rate: float


@dataclass(frozen=True)
class ObjectMatch:
    truth_id: int | None
    prediction_id: int | None
    intersection: int
    union: int
    iou: float
    status: str


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    true = np.asarray(y_true, dtype=bool)
    pred = np.asarray(y_pred, dtype=bool)
    intersection = np.logical_and(true, pred).sum()
    true_count, pred_count = true.sum(), pred.sum()
    union = np.logical_or(true, pred).sum()
    both_empty = true_count == 0 and pred_count == 0
    metrics = BinaryMetrics(
        dice=1.0 if both_empty else float(2 * intersection / max(true_count + pred_count, 1)),
        iou=1.0 if both_empty else float(intersection / max(union, 1)),
        precision=1.0
        if pred_count == 0 and true_count == 0
        else float(intersection / max(pred_count, 1)),
        recall=1.0
        if true_count == 0 and pred_count == 0
        else float(intersection / max(true_count, 1)),
    )
    return {
        "Dice": metrics.dice,
        "IoU": metrics.iou,
        "Precision": metrics.precision,
        "Recall": metrics.recall,
    }


def _overlap_table(
    gt_instances: np.ndarray, pred_instances: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    truth = np.asarray(gt_instances)
    prediction = np.asarray(pred_instances)
    if truth.ndim != 2 or prediction.ndim != 2 or truth.shape != prediction.shape:
        raise ValueError("Instance maps must be two-dimensional arrays with identical shapes")
    if np.any(truth < 0) or np.any(prediction < 0):
        raise ValueError("Instance labels must be non-negative")

    true_ids, true_inverse = np.unique(truth, return_inverse=True)
    pred_ids, pred_inverse = np.unique(prediction, return_inverse=True)
    pair_indices = (true_inverse * len(pred_ids) + pred_inverse).ravel()
    intersections = np.bincount(
        pair_indices, minlength=len(true_ids) * len(pred_ids)
    ).reshape(len(true_ids), len(pred_ids))
    true_areas = intersections.sum(axis=1)
    pred_areas = intersections.sum(axis=0)
    true_foreground = true_ids > 0
    pred_foreground = pred_ids > 0
    foreground_intersections = intersections[np.ix_(true_foreground, pred_foreground)].astype(
        np.float64
    )
    foreground_true_areas = true_areas[true_foreground].astype(np.float64)
    foreground_pred_areas = pred_areas[pred_foreground].astype(np.float64)
    unions = (
        foreground_true_areas[:, None]
        + foreground_pred_areas[None, :]
        - foreground_intersections
    )
    iou = np.divide(
        foreground_intersections,
        unions,
        out=np.zeros_like(foreground_intersections),
        where=unions > 0,
    )
    return foreground_intersections, unions, foreground_true_areas, foreground_pred_areas, iou


def _aji_from_overlaps(
    intersections: np.ndarray,
    unions: np.ndarray,
    true_areas: np.ndarray,
    pred_areas: np.ndarray,
    iou: np.ndarray,
) -> float:
    if not len(true_areas) and not len(pred_areas):
        return 1.0
    if not len(true_areas) or not len(pred_areas):
        return 0.0

    intersection_sum = 0.0
    union_sum = 0.0
    matched_columns: set[int] = set()
    for row in range(len(true_areas)):
        column = int(np.argmax(iou[row]))
        if intersections[row, column] == 0:
            union_sum += true_areas[row]
            continue
        intersection_sum += intersections[row, column]
        union_sum += unions[row, column]
        matched_columns.add(column)
    union_sum += sum(area for index, area in enumerate(pred_areas) if index not in matched_columns)
    return float(intersection_sum / union_sum) if union_sum else 1.0


def _aji_plus_from_overlaps(
    intersections: np.ndarray,
    unions: np.ndarray,
    true_areas: np.ndarray,
    pred_areas: np.ndarray,
    iou: np.ndarray,
) -> float:
    if not len(true_areas) and not len(pred_areas):
        return 1.0
    if not len(true_areas) or not len(pred_areas):
        return 0.0
    rows, columns = linear_sum_assignment(-iou)
    matched = [
        (row, column) for row, column in zip(rows, columns, strict=True) if iou[row, column]
    ]
    matched_rows = {row for row, _ in matched}
    matched_columns = {column for _, column in matched}
    intersection_sum = sum(intersections[row, column] for row, column in matched)
    union_sum = sum(unions[row, column] for row, column in matched)
    union_sum += sum(area for index, area in enumerate(true_areas) if index not in matched_rows)
    union_sum += sum(area for index, area in enumerate(pred_areas) if index not in matched_columns)
    return float(intersection_sum / union_sum) if union_sum else 1.0


def calculate_aji(gt_instances: np.ndarray, pred_instances: np.ndarray) -> float:
    overlaps = _overlap_table(gt_instances, pred_instances)
    return _aji_from_overlaps(*overlaps)


def calculate_aji_plus(gt_instances: np.ndarray, pred_instances: np.ndarray) -> float:
    overlaps = _overlap_table(gt_instances, pred_instances)
    return _aji_plus_from_overlaps(*overlaps)


def calculate_instance_metrics(
    gt_instances: np.ndarray, pred_instances: np.ndarray, match_iou: float = 0.5
) -> InstanceMetrics:
    if not 0 < match_iou <= 1:
        raise ValueError("match_iou must be in the interval (0, 1]")
    intersections, unions, true_areas, pred_areas, iou = _overlap_table(
        gt_instances, pred_instances
    )
    if not len(true_areas) and not len(pred_areas):
        return InstanceMetrics(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
    rows, columns = linear_sum_assignment(-iou) if iou.size else (np.array([]), np.array([]))
    matched_ious = [
        iou[row, column]
        for row, column in zip(rows, columns, strict=True)
        if iou[row, column] > match_iou
    ]
    true_positive = len(matched_ious)
    false_positive = len(pred_areas) - true_positive
    false_negative = len(true_areas) - true_positive
    denominator = true_positive + 0.5 * false_positive + 0.5 * false_negative
    recognition_quality = true_positive / denominator if denominator else 1.0
    segmentation_quality = float(np.mean(matched_ious)) if matched_ious else 0.0
    detection_denominator = 2 * true_positive + false_positive + false_negative
    detection_f1 = 2 * true_positive / detection_denominator if detection_denominator else 1.0
    return InstanceMetrics(
        aji=_aji_from_overlaps(intersections, unions, true_areas, pred_areas, iou),
        aji_plus=_aji_plus_from_overlaps(intersections, unions, true_areas, pred_areas, iou),
        pq=segmentation_quality * recognition_quality,
        detection_f1=detection_f1,
        segmentation_quality=segmentation_quality,
        recognition_quality=recognition_quality,
    )


def calculate_clinical_instance_metrics(
    gt_instances: np.ndarray,
    pred_instances: np.ndarray,
    match_iou: float = 0.5,
) -> tuple[ClinicalInstanceMetrics, list[ObjectMatch]]:
    """Return auditable object-level metrics and one row for every TP, FP, and FN.

    Matching follows the controlled strict ``IoU > match_iou`` rule. Assignments that do not
    exceed the threshold produce one false-negative and one false-positive rather than a match.
    """
    if not 0 < match_iou <= 1:
        raise ValueError("match_iou must be in the interval (0, 1]")
    truth = np.asarray(gt_instances)
    prediction = np.asarray(pred_instances)
    intersections, unions, true_areas, pred_areas, iou = _overlap_table(truth, prediction)
    true_ids = [int(value) for value in np.unique(truth) if value > 0]
    pred_ids = [int(value) for value in np.unique(prediction) if value > 0]
    rows, columns = linear_sum_assignment(-iou) if iou.size else (np.array([]), np.array([]))
    accepted = [
        (int(row), int(column))
        for row, column in zip(rows, columns, strict=True)
        if iou[row, column] > match_iou
    ]
    accepted_rows = {row for row, _ in accepted}
    accepted_columns = {column for _, column in accepted}
    matches = [
        ObjectMatch(
            truth_id=true_ids[row],
            prediction_id=pred_ids[column],
            intersection=int(intersections[row, column]),
            union=int(unions[row, column]),
            iou=float(iou[row, column]),
            status="true_positive",
        )
        for row, column in accepted
    ]
    matches.extend(
        ObjectMatch(
            truth_id=true_ids[row],
            prediction_id=None,
            intersection=0,
            union=int(true_areas[row]),
            iou=0.0,
            status="false_negative",
        )
        for row in range(len(true_ids))
        if row not in accepted_rows
    )
    matches.extend(
        ObjectMatch(
            truth_id=None,
            prediction_id=pred_ids[column],
            intersection=0,
            union=int(pred_areas[column]),
            iou=0.0,
            status="false_positive",
        )
        for column in range(len(pred_ids))
        if column not in accepted_columns
    )

    true_positive = len(accepted)
    false_positive = len(pred_ids) - true_positive
    false_negative = len(true_ids) - true_positive
    both_empty = not true_ids and not pred_ids
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    f1_denominator = 2 * true_positive + false_positive + false_negative
    recognition_denominator = true_positive + 0.5 * (false_positive + false_negative)
    matched_ious = [float(iou[row, column]) for row, column in accepted]
    segmentation_quality = (
        1.0 if both_empty else float(np.mean(matched_ious)) if matched_ious else 0.0
    )
    recognition_quality = (
        1.0 if both_empty else true_positive / recognition_denominator
        if recognition_denominator
        else 0.0
    )
    reference_count = len(true_ids)
    predicted_count = len(pred_ids)
    signed_count_error = predicted_count - reference_count
    metrics = ClinicalInstanceMetrics(
        aji=_aji_from_overlaps(intersections, unions, true_areas, pred_areas, iou),
        aji_plus=_aji_plus_from_overlaps(intersections, unions, true_areas, pred_areas, iou),
        pq=segmentation_quality * recognition_quality,
        segmentation_quality=segmentation_quality,
        recognition_quality=recognition_quality,
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        detection_precision=(
            1.0 if both_empty else true_positive / precision_denominator
            if precision_denominator
            else 0.0
        ),
        detection_recall=(
            1.0 if not true_ids else true_positive / recall_denominator
        ),
        detection_f1=1.0 if both_empty else 2 * true_positive / f1_denominator
        if f1_denominator
        else 0.0,
        reference_count=reference_count,
        predicted_count=predicted_count,
        signed_count_error=signed_count_error,
        absolute_count_error=abs(signed_count_error),
        relative_count_error=(
            signed_count_error / reference_count if reference_count else None
        ),
        object_false_positive_rate=(
            false_positive / precision_denominator if precision_denominator else 0.0
        ),
        object_false_negative_rate=(
            false_negative / recall_denominator if recall_denominator else 0.0
        ),
    )
    return metrics, matches
