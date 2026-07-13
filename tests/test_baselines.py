import pytest
import torch

from src.models.factory import build_model


@pytest.mark.parametrize("model_name", ["unet", "unetplusplus"])
def test_baseline_output_contract(model_name: str) -> None:
    model = build_model(model_name, "resnet18", encoder_weights=None)
    with torch.inference_mode():
        output = model(torch.randn(1, 3, 64, 64))
    assert output.mask_logits.shape == (1, 1, 64, 64)
    assert output.distance.shape == (1, 1, 64, 64)
