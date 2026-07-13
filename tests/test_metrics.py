import numpy as np

from src.utils.metrics import calculate_aji, calculate_instance_metrics, calculate_metrics


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
    assert result.pq == 1.0
    assert result.detection_f1 == 1.0


def test_aji_penalizes_an_unmatched_prediction() -> None:
    truth = np.zeros((10, 10), dtype=np.int32)
    prediction = np.zeros_like(truth)
    truth[1:4, 1:4] = 1
    prediction[1:4, 1:4] = 1
    prediction[6:9, 6:9] = 2
    assert calculate_aji(truth, prediction) == 0.5
