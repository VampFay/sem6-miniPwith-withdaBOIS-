import warnings

import numpy as np
import pytest

from src.inference import AttnDistInference, PostprocessConfig, postprocess_instances


def test_postprocessing_separates_two_distance_peaks() -> None:
    yy, xx = np.mgrid[:64, :64]
    first = np.exp(-((xx - 23) ** 2 + (yy - 32) ** 2) / 80)
    second = np.exp(-((xx - 41) ** 2 + (yy - 32) ** 2) / 80)
    distance = np.maximum(first, second).astype(np.float32)
    foreground = ((xx - 23) ** 2 + (yy - 32) ** 2 < 14**2) | (
        (xx - 41) ** 2 + (yy - 32) ** 2 < 14**2
    )
    instances = postprocess_instances(foreground.astype(np.float32), distance)
    assert set(np.unique(instances)) == {0, 1, 2}


def test_postprocessing_handles_empty_prediction() -> None:
    empty = np.zeros((32, 32), dtype=np.float32)
    assert np.count_nonzero(postprocess_instances(empty, empty)) == 0


def test_tensor_conversion_accepts_read_only_memory_map_views() -> None:
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    image.setflags(write=False)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        tensor = AttnDistInference._to_tensor(image)

    assert tensor.shape == (1, 3, 16, 16)


def test_postprocess_configuration_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="positive odd"):
        PostprocessConfig(peak_window_size=4)
    with pytest.raises(ValueError, match="interval"):
        PostprocessConfig(mask_threshold=1.0)


def test_postprocessing_rejects_invalid_maps() -> None:
    valid = np.zeros((8, 8), dtype=np.float32)
    with pytest.raises(ValueError, match="same-shaped 2D"):
        postprocess_instances(valid, np.zeros((7, 8), dtype=np.float32))
    invalid = valid.copy()
    invalid[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        postprocess_instances(invalid, valid)
