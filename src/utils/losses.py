from __future__ import annotations

from dataclasses import dataclass

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
    deep_supervision: torch.Tensor


class AttnDistComboLoss(nn.Module):
    def __init__(
        self, mask_weight: float = 1.0, distance_weight: float = 0.5, auxiliary_weight: float = 0.2
    ) -> None:
        super().__init__()
        self.dice = DiceLoss()
        self.bce = nn.BCEWithLogitsLoss()
        self.mse = nn.MSELoss()
        self.mask_weight = mask_weight
        self.distance_weight = distance_weight
        self.auxiliary_weight = auxiliary_weight

    def forward(
        self, output: ModelOutput, mask_target: torch.Tensor, distance_target: torch.Tensor
    ) -> LossOutput:
        mask_loss = self.dice(output.mask_logits, mask_target) + self.bce(
            output.mask_logits, mask_target
        )
        distance_loss = self.mse(output.distance, distance_target)
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
        return LossOutput(total, mask_loss, distance_loss, auxiliary_loss)
