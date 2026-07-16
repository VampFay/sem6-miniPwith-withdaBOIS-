import numpy as np
import pytest
from scipy.optimize import linear_sum_assignment

from src.utils.metrics import (
    calculate_aji,
    calculate_aji_plus,
    calculate_instance_metrics,
    calculate_metrics,
)


def brute_force_instance_scores(
    truth: np.ndarray, prediction: np.ndarray, match_iou: float = 0.5
) -> tuple[float, float, float, float, float, float]:
    true_masks = [truth == value for value in np.unique(truth) if value > 0]
    pred_masks = [prediction == value for value in np.unique(prediction) if value > 0]
    if not true_masks and not pred_masks:
        return 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
    iou = np.zeros((len(true_masks), len(pred_masks)), dtype=np.float64)
    intersections = np.zeros_like(iou)
    unions = np.zeros_like(iou)
    for row, true_mask in enumerate(true_masks):
        for column, pred_mask in enumerate(pred_masks):
            intersections[row, column] = np.logical_and(true_mask, pred_mask).sum()
            unions[row, column] = np.logical_or(true_mask, pred_mask).sum()
            if intersections[row, column]:
                iou[row, column] = intersections[row, column] / unions[row, column]
    rows, columns = linear_sum_assignment(-iou) if iou.size else ([], [])
    aji_plus_pairs = [
        (row, column)
        for row, column in zip(rows, columns, strict=True)
        if iou[row, column] > 0
    ]
    matched_rows = {row for row, _ in aji_plus_pairs}
    matched_columns = {column for _, column in aji_plus_pairs}
    aji_plus_intersection = sum(intersections[row, column] for row, column in aji_plus_pairs)
    aji_plus_union = sum(unions[row, column] for row, column in aji_plus_pairs)
    aji_plus_union += sum(
        mask.sum() for row, mask in enumerate(true_masks) if row not in matched_rows
    )
    aji_plus_union += sum(
        mask.sum() for column, mask in enumerate(pred_masks) if column not in matched_columns
    )
    aji_plus = float(aji_plus_intersection / aji_plus_union) if aji_plus_union else 1.0

    aji_intersection = 0.0
    aji_union = 0.0
    aji_columns: set[int] = set()
    for row, true_mask in enumerate(true_masks):
        if not pred_masks:
            aji_union += true_mask.sum()
            continue
        column = int(np.argmax(iou[row]))
        if intersections[row, column] == 0:
            aji_union += true_mask.sum()
            continue
        aji_intersection += intersections[row, column]
        aji_union += unions[row, column]
        aji_columns.add(column)
    aji_union += sum(
        mask.sum() for column, mask in enumerate(pred_masks) if column not in aji_columns
    )
    aji = float(aji_intersection / aji_union) if aji_union else 1.0

    matches = [
        iou[row, column]
        for row, column in zip(rows, columns, strict=True)
        if iou[row, column] > match_iou
    ]
    true_positive = len(matches)
    false_positive = len(pred_masks) - true_positive
    false_negative = len(true_masks) - true_positive
    denominator = true_positive + 0.5 * false_positive + 0.5 * false_negative
    recognition_quality = true_positive / denominator if denominator else 1.0
    segmentation_quality = float(np.mean(matches)) if matches else 0.0
    detection_f1 = (
        2 * true_positive / (2 * true_positive + false_positive + false_negative)
        if 2 * true_positive + false_positive + false_negative
        else 1.0
    )
    return (
        aji,
        aji_plus,
        segmentation_quality * recognition_quality,
        detection_f1,
        segmentation_quality,
        recognition_quality,
    )


def test_empty_binary_masks_are_a_perfect_match() -> None:
    empty = np.zeros((8, 8), dtype=np.uint8)
    assert calculate_metrics(empty, empty) == {
        "Dice": 1.0,
        "IoU": 1.0,
        "Precision": 1.0,
        "Recall": 1.0,
    }


def test_instance_metrics_are_exact_for_identical_instances() -> None:
    instances = np.zeros((12, 12), dtype=np.int32)
    instances[1:4, 1:4] = 1
    instances[7:10, 7:10] = 2
    result = calculate_instance_metrics(instances, instances)
    assert calculate_aji(instances, instances) == 1.0
    assert result.aji == 1.0
    assert result.aji_plus == 1.0
    assert result.pq == 1.0
    assert result.detection_f1 == 1.0


def test_aji_penalizes_an_unmatched_prediction() -> None:
    truth = np.zeros((10, 10), dtype=np.int32)
    prediction = np.zeros_like(truth)
    truth[1:4, 1:4] = 1
    prediction[1:4, 1:4] = 1
    prediction[6:9, 6:9] = 2
    assert calculate_aji(truth, prediction) == 0.5


def test_instance_metrics_score_a_merged_pair() -> None:
    truth = np.zeros((6, 8), dtype=np.int32)
    prediction = np.zeros_like(truth)
    truth[1:3, 1:3] = 7
    truth[1:3, 3:5] = 42
    prediction[1:3, 1:5] = 9000

    result = calculate_instance_metrics(truth, prediction)

    assert result.aji == pytest.approx(0.5)
    assert result.aji_plus == pytest.approx(1 / 3)
    assert calculate_aji_plus(truth, prediction) == pytest.approx(1 / 3)
    assert result.detection_f1 == 0.0
    assert result.segmentation_quality == 0.0
    assert result.pq == 0.0


def test_instance_metrics_support_sparse_noncontiguous_ids() -> None:
    truth = np.zeros((8, 8), dtype=np.int64)
    prediction = np.zeros_like(truth)
    truth[1:4, 1:4] = 1_000_000
    prediction[1:4, 1:4] = 9_000_000

    assert calculate_instance_metrics(truth, prediction).pq == 1.0


def test_vectorized_instance_metrics_match_brute_force_reference() -> None:
    generator = np.random.default_rng(42)
    for _ in range(12):
        truth = generator.integers(0, 5, size=(16, 18), dtype=np.int32) * 11
        prediction = generator.integers(0, 6, size=(16, 18), dtype=np.int32) * 101
        expected = brute_force_instance_scores(truth, prediction)
        actual = calculate_instance_metrics(truth, prediction)
        assert (
            actual.aji,
            actual.aji_plus,
            actual.pq,
            actual.detection_f1,
            actual.segmentation_quality,
            actual.recognition_quality,
        ) == pytest.approx(expected)


def test_instance_metrics_reject_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="identical shapes"):
        calculate_instance_metrics(np.zeros((2, 2)), np.zeros((3, 3)))
    with pytest.raises(ValueError, match="match_iou"):
        calculate_instance_metrics(np.zeros((2, 2)), np.zeros((2, 2)), match_iou=0)
