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
    assert float(augmented["uncertainty"].max()) < 1e-6


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
