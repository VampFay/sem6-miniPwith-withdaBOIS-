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
    pq: float
    detection_f1: float
    segmentation_quality: float
    recognition_quality: float


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


def calculate_instance_metrics(
    gt_instances: np.ndarray, pred_instances: np.ndarray, match_iou: float = 0.5
) -> InstanceMetrics:
    if not 0 < match_iou <= 1:
        raise ValueError("match_iou must be in the interval (0, 1]")
    intersections, unions, true_areas, pred_areas, iou = _overlap_table(
        gt_instances, pred_instances
    )
    if not len(true_areas) and not len(pred_areas):
        return InstanceMetrics(1.0, 1.0, 1.0, 1.0, 1.0)
    rows, columns = linear_sum_assignment(-iou) if iou.size else (np.array([]), np.array([]))
    matched_ious = [
        iou[row, column]
        for row, column in zip(rows, columns, strict=True)
        if iou[row, column] >= match_iou
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
        pq=segmentation_quality * recognition_quality,
        detection_f1=detection_f1,
        segmentation_quality=segmentation_quality,
        recognition_quality=recognition_quality,
    )
