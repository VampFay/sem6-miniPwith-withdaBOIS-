import torch

from src.models.attn_dist_unet import AttnDistUNet


def test_model_output_contract_without_network() -> None:
    model = AttnDistUNet(encoder_name="resnet18", encoder_weights=None)
    image = torch.randn(1, 3, 64, 64)
    model.train()
    output = model(image)
    assert output.mask_logits.shape == (1, 1, 64, 64)
    assert output.distance.shape == (1, 1, 64, 64)
    assert len(output.deep_supervision) == 3
    model.eval()
    with torch.inference_mode():
        assert model(image).deep_supervision == ()
