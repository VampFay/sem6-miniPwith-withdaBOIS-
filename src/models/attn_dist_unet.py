from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import segmentation_models_pytorch as smp
import torch
import torch.nn.functional as F
from torch import nn


@dataclass(frozen=True)
class ModelOutput:
    mask_logits: torch.Tensor
    distance: torch.Tensor
    deep_supervision: tuple[torch.Tensor, ...] = ()


class AttentionGate(nn.Module):
    def __init__(self, gate_channels: int, skip_channels: int, hidden_channels: int) -> None:
        super().__init__()
        self.gate_projection = self._projection(gate_channels, hidden_channels)
        self.skip_projection = self._projection(skip_channels, hidden_channels)
        self.attention = nn.Sequential(
            nn.Conv2d(hidden_channels, 1, 1), nn.BatchNorm2d(1), nn.Sigmoid()
        )
        self.activation = nn.ReLU(inplace=True)

    @staticmethod
    def _projection(in_channels: int, out_channels: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 1, bias=True),
            nn.BatchNorm2d(out_channels),
        )

    def forward(self, gate: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        gate = F.interpolate(gate, size=skip.shape[-2:], mode="bilinear", align_corners=False)
        score = self.activation(self.gate_projection(gate) + self.skip_projection(skip))
        return cast(torch.Tensor, skip * self.attention(score))


class ConvBlock(nn.Sequential):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__(
            nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=True),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=True),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )


class DecoderStage(nn.Module):
    def __init__(self, in_channels: int, skip_channels: int) -> None:
        super().__init__()
        self.upsample = nn.ConvTranspose2d(in_channels, skip_channels, 2, stride=2)
        self.attention = AttentionGate(in_channels, skip_channels, max(skip_channels // 2, 1))
        self.fuse = ConvBlock(skip_channels * 2, skip_channels)

    def forward(self, decoder: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        upsampled = self.upsample(decoder)
        attended = self.attention(decoder, skip)
        if upsampled.shape[-2:] != attended.shape[-2:]:
            upsampled = F.interpolate(
                upsampled, size=attended.shape[-2:], mode="bilinear", align_corners=False
            )
        return cast(torch.Tensor, self.fuse(torch.cat((attended, upsampled), dim=1)))


class AttnDistUNet(nn.Module):
    def __init__(
        self,
        encoder_name: str = "efficientnet-b0",
        classes: int = 1,
        encoder_weights: str | None = "imagenet",
    ) -> None:
        super().__init__()
        self.encoder = smp.encoders.get_encoder(
            encoder_name, in_channels=3, depth=5, weights=encoder_weights
        )
        channels = self.encoder.out_channels
        self.decoder5 = DecoderStage(channels[5], channels[4])
        self.decoder4 = DecoderStage(channels[4], channels[3])
        self.decoder3 = DecoderStage(channels[3], channels[2])
        self.decoder2 = DecoderStage(channels[2], channels[1])
        self.mask_head = self._head(channels[1], classes)
        self.distance_head = self._head(channels[1], 1)
        self.auxiliary_heads = nn.ModuleList(
            [
                nn.Conv2d(channels[1], classes, 1),
                nn.Conv2d(channels[2], classes, 1),
                nn.Conv2d(channels[3], classes, 1),
            ]
        )

    @staticmethod
    def _head(in_channels: int, out_channels: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, out_channels, 1),
        )

    def forward(self, image: torch.Tensor) -> ModelOutput:
        features = self.encoder(image)
        d5 = self.decoder5(features[5], features[4])
        d4 = self.decoder4(d5, features[3])
        d3 = self.decoder3(d4, features[2])
        d2 = self.decoder2(d3, features[1])
        decoded = F.interpolate(d2, size=image.shape[-2:], mode="bilinear", align_corners=False)
        auxiliary = tuple(
            head(feature) for head, feature in zip(self.auxiliary_heads, (d2, d3, d4), strict=True)
        )
        return ModelOutput(
            mask_logits=self.mask_head(decoded),
            distance=self.distance_head(decoded),
            deep_supervision=auxiliary if self.training else (),
        )
