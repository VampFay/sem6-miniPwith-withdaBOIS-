import numpy as np
import torch

from scripts.tune_postprocessing import (
    score_settings,
    selected_positions,
    write_calibrated_checkpoint,
)
from src.inference import PostprocessConfig
from src.preprocessing.instances import instance_distance_map


def test_search_subset_is_deterministic_and_unique() -> None:
    first = selected_positions(100, 20, seed=42)
    second = selected_positions(100, 20, seed=42)

    np.testing.assert_array_equal(first, second)
    assert len(np.unique(first)) == 20


def test_tuning_score_is_exact_for_one_clean_instance() -> None:
    truth = np.zeros((1, 32, 32), dtype=np.uint16)
    truth[0, 8:24, 8:24] = 1
    masks = (truth > 0).astype(np.float32)
    distances = instance_distance_map(truth[0])[None]

    result = score_settings(
        PostprocessConfig(),
        np.array([0]),
        masks,
        distances,
        truth,
        np.array([0]),
    )

    assert result["dice"] == 1.0
    assert result["aji"] == 1.0
    assert result["pq"] == 1.0


def test_calibrated_checkpoint_records_selected_parameters(tmp_path) -> None:
    source = tmp_path / "source.pt"
    destination = tmp_path / "calibrated.pt"
    torch.save(
        {
            "format_version": 2,
            "artifact_type": "attn-dist-inference",
            "config": {},
            "model_state_dict": {},
        },
        source,
    )
    settings = PostprocessConfig(0.45, 0.3, 20, 0.5, 5)
    validation = {
        "samples": 10.0,
        "dice": 0.8,
        "aji": 0.5,
        "pq": 0.4,
        "detection_f1": 0.6,
        "sq": 0.7,
    }

    digest = write_calibrated_checkpoint(source, destination, settings, validation)
    checkpoint = torch.load(destination, map_location="cpu", weights_only=True)

    assert len(digest) == 64
    assert checkpoint["postprocessing"] == settings.as_dict()
    assert checkpoint["calibration"]["scope"] == "validation_fold_2_only"
    assert checkpoint["calibration"]["validation_metrics"]["pq"] == 0.4
