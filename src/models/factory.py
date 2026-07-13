from __future__ import annotations

import segmentation_models_pytorch as smp
import torch
from torch import nn

from src.models.attn_dist_unet import AttnDistUNet, ModelOutput


class SMPBaseline(nn.Module):
    """Two-output baseline using a standard SMP decoder and shared encoder."""

    def __init__(self, architecture: str, encoder_name: str, encoder_weights: str | None) -> None:
        super().__init__()
        constructors = {"unet": smp.Unet, "unetplusplus": smp.UnetPlusPlus}
        try:
            constructor = constructors[architecture]
        except KeyError as error:
            raise ValueError(f"Unknown baseline architecture: {architecture}") from error
        self.network = constructor(
            encoder_name=encoder_name,
            encoder_weights=encoder_weights,
            in_channels=3,
            classes=2,
        )

    def forward(self, image: torch.Tensor) -> ModelOutput:
        prediction = self.network(image)
        return ModelOutput(prediction[:, :1], prediction[:, 1:2])


def build_model(model_name: str, encoder_name: str, encoder_weights: str | None) -> nn.Module:
    if model_name == "attn-dist":
        return AttnDistUNet(encoder_name=encoder_name, encoder_weights=encoder_weights)
    return SMPBaseline(model_name, encoder_name, encoder_weights)
