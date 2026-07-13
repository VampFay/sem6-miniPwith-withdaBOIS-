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


def _instances(instance_map: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    ids = np.unique(instance_map)
    ids = ids[ids > 0]
    return ids, [instance_map == instance_id for instance_id in ids]


def _pairwise_iou(true_masks: list[np.ndarray], pred_masks: list[np.ndarray]) -> np.ndarray:
    matrix = np.zeros((len(true_masks), len(pred_masks)), dtype=np.float64)
    for row, true_mask in enumerate(true_masks):
        for column, pred_mask in enumerate(pred_masks):
            intersection = np.logical_and(true_mask, pred_mask).sum()
            if intersection:
                matrix[row, column] = intersection / np.logical_or(true_mask, pred_mask).sum()
    return matrix


def calculate_aji(gt_instances: np.ndarray, pred_instances: np.ndarray) -> float:
    _, true_masks = _instances(gt_instances)
    _, pred_masks = _instances(pred_instances)
    if not true_masks and not pred_masks:
        return 1.0
    if not true_masks or not pred_masks:
        return 0.0
    iou = _pairwise_iou(true_masks, pred_masks)
    rows, columns = linear_sum_assignment(-iou)
    matched = [
        (row, column) for row, column in zip(rows, columns, strict=True) if iou[row, column] > 0
    ]
    intersection = sum(np.logical_and(true_masks[r], pred_masks[c]).sum() for r, c in matched)
    union = sum(np.logical_or(true_masks[r], pred_masks[c]).sum() for r, c in matched)
    matched_rows = {row for row, _ in matched}
    matched_columns = {column for _, column in matched}
    union += sum(mask.sum() for index, mask in enumerate(true_masks) if index not in matched_rows)
    union += sum(
        mask.sum() for index, mask in enumerate(pred_masks) if index not in matched_columns
    )
    return float(intersection / union) if union else 1.0


def calculate_instance_metrics(
    gt_instances: np.ndarray, pred_instances: np.ndarray, match_iou: float = 0.5
) -> InstanceMetrics:
    _, true_masks = _instances(gt_instances)
    _, pred_masks = _instances(pred_instances)
    if not true_masks and not pred_masks:
        return InstanceMetrics(1.0, 1.0, 1.0, 1.0, 1.0)
    iou = _pairwise_iou(true_masks, pred_masks)
    rows, columns = linear_sum_assignment(-iou) if iou.size else (np.array([]), np.array([]))
    matched_ious = [
        iou[row, column]
        for row, column in zip(rows, columns, strict=True)
        if iou[row, column] >= match_iou
    ]
    true_positive = len(matched_ious)
    false_positive = len(pred_masks) - true_positive
    false_negative = len(true_masks) - true_positive
    denominator = true_positive + 0.5 * false_positive + 0.5 * false_negative
    recognition_quality = true_positive / denominator if denominator else 1.0
    segmentation_quality = float(np.mean(matched_ious)) if matched_ious else 0.0
    detection_denominator = 2 * true_positive + false_positive + false_negative
    detection_f1 = 2 * true_positive / detection_denominator if detection_denominator else 1.0
    return InstanceMetrics(
        aji=calculate_aji(gt_instances, pred_instances),
        pq=segmentation_quality * recognition_quality,
        detection_f1=detection_f1,
        segmentation_quality=segmentation_quality,
        recognition_quality=recognition_quality,
    )
