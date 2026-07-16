import warnings
from pathlib import Path
from typing import Literal

import numpy as np
import pytest
import torch
from torch import nn

from src.inference import AttnDistInference, PostprocessConfig, postprocess_instances
from src.inference import predictor as predictor_module
from src.models.attn_dist_unet import ModelOutput


class EquivariantTestModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def forward(self, image: torch.Tensor) -> ModelOutput:
        self.calls += 1
        return ModelOutput(mask_logits=image[:, :1], distance=image[:, 1:2])


class ZeroDistanceModel(nn.Module):
    def forward(self, image: torch.Tensor) -> ModelOutput:
        zeros = image[:, :1] * 0
        return ModelOutput(mask_logits=zeros, distance=zeros)


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


def test_postprocessing_retains_every_disconnected_foreground_component() -> None:
    foreground = np.zeros((16, 32), dtype=np.float32)
    distance = np.zeros_like(foreground)
    foreground[2:8, 2:8] = 1
    foreground[2:8, 22:28] = 1
    distance[3:7, 3:7] = 0.8
    distance[3:7, 23:27] = 0.2

    instances = postprocess_instances(
        foreground,
        distance,
        peak_threshold=0.35,
        min_size=1,
        gaussian_sigma=0,
        peak_window_size=3,
    )

    assert np.all(instances[foreground > 0] > 0)
    assert set(np.unique(instances)) == {0, 1, 2}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_size": 0},
        {"gaussian_sigma": -0.1},
        {"peak_window_size": 2},
    ],
)
def test_postprocessing_rejects_invalid_geometry(kwargs: dict[str, float | int]) -> None:
    with pytest.raises(ValueError):
        PostprocessConfig(**kwargs)


def test_tensor_conversion_accepts_read_only_memory_map_views() -> None:
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    image.setflags(write=False)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        tensor = AttnDistInference._to_tensor(image)

    assert tensor.shape == (1, 3, 16, 16)


def test_tta_batches_all_views_in_one_equivariant_model_call() -> None:
    generator = np.random.default_rng(42)
    image = generator.integers(0, 256, size=(32, 32, 3), dtype=np.uint8)
    model = EquivariantTestModel()
    engine = AttnDistInference(model, "cpu")

    reference = engine.predict_maps(image, use_tta=False)
    model.calls = 0
    augmented = engine.predict_maps(image, use_tta=True)

    assert model.calls == 1
    np.testing.assert_allclose(augmented["mask"], reference["mask"], atol=1e-6)
    np.testing.assert_allclose(augmented["dist_map"], reference["dist_map"], atol=1e-6)
    assert float(augmented["tta_disagreement"].max()) < 1e-6


@pytest.mark.parametrize(
    ("activation", "expected"), [("identity", 0.0), ("sigmoid", 0.5)]
)
def test_inference_applies_declared_distance_activation(
    activation: Literal["identity", "sigmoid"], expected: float
) -> None:
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    engine = AttnDistInference(
        ZeroDistanceModel(),
        "cpu",
        distance_activation=activation,
    )

    result = engine.predict_maps(image)

    assert float(result["dist_map"].mean()) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("length", "tile_size", "step", "expected"),
    [
        (16, 32, 24, [0]),
        (32, 32, 24, [0]),
        (64, 32, 24, [0, 24, 32]),
        (83, 32, 24, [0, 24, 48, 51]),
    ],
)
def test_tile_starts_cover_borders_without_duplicate_terminal_tile(
    length: int, tile_size: int, step: int, expected: list[int]
) -> None:
    assert AttnDistInference._starts(length, tile_size, step) == expected


def test_tiled_blending_preserves_constant_maps_across_seams(monkeypatch) -> None:
    engine = AttnDistInference(ZeroDistanceModel(), "cpu", tile_size=32, overlap=8)
    calls: list[tuple[int, int]] = []

    def constant_patch(image: np.ndarray, use_tta: bool) -> tuple[np.ndarray, ...]:
        assert use_tta
        calls.append(image.shape[:2])
        shape = image.shape[:2]
        return (
            np.full(shape, 0.25, dtype=np.float32),
            np.full(shape, 0.75, dtype=np.float32),
            np.full(shape, 0.10, dtype=np.float32),
        )

    monkeypatch.setattr(engine, "_predict_patch", constant_patch)
    result = engine.predict_maps(np.zeros((70, 83, 3), dtype=np.uint8), use_tta=True)

    assert len(calls) == 12
    assert set(calls) == {(32, 32)}
    assert all(value.shape == (70, 83) for value in result.values())
    np.testing.assert_allclose(result["mask"], 0.25, atol=1e-6)
    np.testing.assert_allclose(result["dist_map"], 0.75, atol=1e-6)
    np.testing.assert_allclose(result["tta_disagreement"], 0.10, atol=1e-6)


def test_predict_full_applies_explicit_postprocessing_overrides(monkeypatch) -> None:
    engine = AttnDistInference(
        ZeroDistanceModel(),
        "cpu",
        postprocess=PostprocessConfig(
            mask_threshold=0.5,
            peak_threshold=0.35,
            min_size=10,
            gaussian_sigma=1.0,
            peak_window_size=7,
        ),
    )
    maps = {
        "mask": np.full((8, 8), 0.8, dtype=np.float32),
        "dist_map": np.full((8, 8), 0.6, dtype=np.float32),
        "tta_disagreement": np.full((8, 8), 0.1, dtype=np.float32),
    }
    captured: tuple[object, ...] | None = None

    def capture(*args):
        nonlocal captured
        captured = args
        return np.ones((8, 8), dtype=np.int32)

    monkeypatch.setattr(engine, "predict_maps", lambda image, use_tta: maps)
    monkeypatch.setattr(predictor_module, "postprocess_instances", capture)
    result = engine.predict_full(
        np.zeros((8, 8, 3), dtype=np.uint8),
        mask_threshold=0.6,
        peak_threshold=0.4,
        min_size=4,
        gaussian_sigma=0.5,
        peak_window_size=5,
    )

    assert captured is not None
    assert captured[0] is maps["mask"]
    assert captured[1] is maps["dist_map"]
    assert captured[2:] == (0.6, 0.4, 4, 0.5, 5)
    assert np.all(result["instances"] == 1)


@pytest.mark.parametrize(
    "payload",
    [
        {"format_version": 1, "artifact_type": "attn-dist-inference"},
        {"format_version": 2, "artifact_type": "attn-dist-training"},
    ],
)
def test_inference_rejects_wrong_artifact_contract(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        AttnDistInference._from_checkpoint_payload(payload, "cpu", "test")


@pytest.mark.parametrize(
    ("model_contract", "expected"),
    [({}, "identity"), ({"distance_activation": "sigmoid"}, "sigmoid")],
)
def test_checkpoint_distance_activation_is_explicit_and_legacy_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model_contract: dict[str, str],
    expected: str,
) -> None:
    checkpoint = tmp_path / "model.pt"
    torch.save(
        {
            "format_version": 2,
            "artifact_type": "attn-dist-inference",
            "config": {"model_name": "attn-dist", "encoder": "test"},
            "model_contract": model_contract,
            "model_state_dict": {},
        },
        checkpoint,
    )
    monkeypatch.setattr(
        predictor_module,
        "build_model",
        lambda model_name, encoder_name, encoder_weights: ZeroDistanceModel(),
    )

    engine = AttnDistInference.from_checkpoint(checkpoint)

    assert engine.distance_activation == expected


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
