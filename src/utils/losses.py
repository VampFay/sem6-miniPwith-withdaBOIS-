from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import torch
import torch.nn.functional as F
from torch import nn

from src.models.attn_dist_unet import ModelOutput


class DiceLoss(nn.Module):
    def __init__(self, smooth: float = 1e-6) -> None:
        super().__init__()
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        probability = torch.sigmoid(logits)
        intersection = (probability * target).sum(dim=(2, 3))
        denominator = probability.sum(dim=(2, 3)) + target.sum(dim=(2, 3))
        return 1 - ((2 * intersection + self.smooth) / (denominator + self.smooth)).mean()


@dataclass(frozen=True)
class LossOutput:
    total: torch.Tensor
    mask: torch.Tensor
    distance: torch.Tensor
    distance_foreground: torch.Tensor
    distance_background: torch.Tensor
    deep_supervision: torch.Tensor


class ForegroundDistanceLoss(nn.Module):
    def __init__(
        self,
        activation: Literal["identity", "sigmoid"] = "sigmoid",
        background_weight: float = 0.1,
    ) -> None:
        super().__init__()
        if activation not in {"identity", "sigmoid"}:
            raise ValueError(f"Unsupported distance activation: {activation}")
        if background_weight < 0:
            raise ValueError("Background weight must be non-negative")
        self.activation = activation
        self.background_weight = background_weight

    def activate(self, prediction: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(prediction) if self.activation == "sigmoid" else prediction

    def forward(
        self,
        prediction: torch.Tensor,
        target: torch.Tensor,
        foreground_target: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        bounded = self.activate(prediction)
        foreground = foreground_target >= 0.5
        background = ~foreground
        pixel_loss = F.smooth_l1_loss(bounded, target, reduction="none")
        foreground_loss = (pixel_loss * foreground).sum() / foreground.sum().clamp_min(1)
        background_loss = (bounded.square() * background).sum() / background.sum().clamp_min(1)
        total = foreground_loss + self.background_weight * background_loss
        return total, foreground_loss, background_loss


class AttnDistComboLoss(nn.Module):
    def __init__(
        self,
        mask_weight: float = 1.0,
        distance_weight: float = 0.5,
        auxiliary_weight: float = 0.2,
        distance_activation: Literal["identity", "sigmoid"] = "sigmoid",
        distance_background_weight: float = 0.1,
    ) -> None:
        super().__init__()
        self.dice = DiceLoss()
        self.bce = nn.BCEWithLogitsLoss()
        self.distance_criterion = ForegroundDistanceLoss(
            distance_activation, distance_background_weight
        )
        self.mask_weight = mask_weight
        self.distance_weight = distance_weight
        self.auxiliary_weight = auxiliary_weight

    def forward(
        self, output: ModelOutput, mask_target: torch.Tensor, distance_target: torch.Tensor
    ) -> LossOutput:
        mask_loss = self.dice(output.mask_logits, mask_target) + self.bce(
            output.mask_logits, mask_target
        )
        distance_loss, distance_foreground, distance_background = self.distance_criterion(
            output.distance, distance_target, mask_target
        )
        auxiliary_loss = output.mask_logits.new_zeros(())
        if output.deep_supervision:
            for prediction in output.deep_supervision:
                target = F.interpolate(mask_target, size=prediction.shape[-2:], mode="nearest")
                auxiliary_loss = (
                    auxiliary_loss + self.dice(prediction, target) + self.bce(prediction, target)
                )
            auxiliary_loss = auxiliary_loss / len(output.deep_supervision)
        total = (
            self.mask_weight * mask_loss
            + self.distance_weight * distance_loss
            + self.auxiliary_weight * auxiliary_loss
        )
        return LossOutput(
            total,
            mask_loss,
            distance_loss,
            distance_foreground,
            distance_background,
            auxiliary_loss,
        )
