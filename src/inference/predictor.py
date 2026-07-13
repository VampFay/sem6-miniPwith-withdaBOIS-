from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import numpy as np
import torch
import torchvision.transforms.functional as TF
from scipy.ndimage import gaussian_filter, label, maximum_filter
from skimage.segmentation import watershed
from torch import nn

from src.config import IMAGENET_MEAN, IMAGENET_STD
from src.models.factory import build_model


def postprocess_instances(
    mask_probability: np.ndarray,
    distance_map: np.ndarray,
    mask_threshold: float = 0.5,
    peak_threshold: float = 0.35,
    min_size: int = 10,
) -> np.ndarray:
    foreground = mask_probability >= mask_threshold
    components, _ = label(foreground)
    component_sizes = np.bincount(components.ravel())
    foreground = foreground & (component_sizes[components] >= min_size)
    if not foreground.any():
        return np.zeros(foreground.shape, dtype=np.int32)
    smooth_distance = gaussian_filter(distance_map.astype(np.float32), sigma=1.0)
    peaks = (
        (smooth_distance == maximum_filter(smooth_distance, size=7))
        & (smooth_distance >= peak_threshold)
        & foreground
    )
    markers, marker_count = label(peaks)
    if marker_count == 0:
        markers, _ = label(foreground)
    segmented = cast(np.ndarray, watershed(-smooth_distance, markers, mask=foreground))
    return segmented.astype(np.int32)


class AttnDistInference:
    def __init__(
        self,
        model: nn.Module,
        device: torch.device | str,
        tile_size: int = 256,
        overlap: int = 64,
    ) -> None:
        if overlap < 0 or overlap >= tile_size:
            raise ValueError("Overlap must be non-negative and smaller than tile size")
        self.model = model.to(device).eval()
        self.device = torch.device(device)
        self.tile_size = tile_size
        self.overlap = overlap

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        device: torch.device | str = "cpu",
        encoder_name: str = "efficientnet-b0",
        **kwargs: int,
    ) -> AttnDistInference:
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
        if checkpoint.get("format_version") != 2:
            raise ValueError("Checkpoint does not use the supported inference format version 2")
        if checkpoint.get("artifact_type") != "attn-dist-inference":
            raise ValueError("Checkpoint is not a deployable Attn-Dist-Net inference artifact")
        saved_config = checkpoint["config"]
        model_name = str(saved_config.get("model_name", "attn-dist"))
        encoder_name = str(saved_config.get("encoder", encoder_name))
        model = build_model(model_name, encoder_name, encoder_weights=None)
        model.load_state_dict(checkpoint["model_state_dict"], strict=True)
        return cls(model, device, **kwargs)

    @staticmethod
    def _to_tensor(image: np.ndarray) -> torch.Tensor:
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Expected an RGB image with shape [H, W, 3]")
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        tensor = TF.to_tensor(np.ascontiguousarray(image))
        return cast(
            torch.Tensor, TF.normalize(tensor, IMAGENET_MEAN, IMAGENET_STD).unsqueeze(0)
        )

    @torch.inference_mode()
    def _predict_patch(self, image: np.ndarray, use_tta: bool) -> tuple[np.ndarray, ...]:
        tensor = self._to_tensor(image).to(self.device)
        height, width = image.shape[:2]
        pad_height = (-height) % 32
        pad_width = (-width) % 32
        tensor = torch.nn.functional.pad(tensor, (0, pad_width, 0, pad_height))
        transforms: list[
            tuple[Callable[[torch.Tensor], torch.Tensor], Callable[[torch.Tensor], torch.Tensor]]
        ] = [(lambda value: value, lambda value: value)]
        if use_tta:
            transforms.extend(
                [
                    (
                        lambda value: torch.flip(value, (-1,)),
                        lambda value: torch.flip(value, (-1,)),
                    ),
                    (
                        lambda value: torch.flip(value, (-2,)),
                        lambda value: torch.flip(value, (-2,)),
                    ),
                    (
                        lambda value: torch.flip(value, (-2, -1)),
                        lambda value: torch.flip(value, (-2, -1)),
                    ),
                ]
            )
        masks, distances = [], []
        for forward, inverse in transforms:
            output = self.model(forward(tensor))
            masks.append(
                inverse(torch.sigmoid(output.mask_logits))[0, 0, :height, :width].cpu().numpy()
            )
            distance = inverse(output.distance)[0, 0, :height, :width].cpu().numpy()
            distances.append(np.clip(distance, 0.0, 1.0))
        mask_stack = np.stack(masks)
        return mask_stack.mean(0), np.stack(distances).mean(0), mask_stack.std(0)

    @staticmethod
    def _starts(length: int, tile_size: int, step: int) -> list[int]:
        if length <= tile_size:
            return [0]
        starts = list(range(0, length - tile_size + 1, step))
        if starts[-1] != length - tile_size:
            starts.append(length - tile_size)
        return starts

    def _predict_tiled(self, image: np.ndarray, use_tta: bool) -> tuple[np.ndarray, ...]:
        height, width = image.shape[:2]
        if height <= self.tile_size and width <= self.tile_size:
            return self._predict_patch(image, use_tta)
        totals = [np.zeros((height, width), dtype=np.float32) for _ in range(3)]
        weights = np.zeros((height, width), dtype=np.float32)
        axis = np.hanning(self.tile_size).astype(np.float32)
        blending = np.maximum(np.outer(axis, axis), 0.05)
        step = self.tile_size - self.overlap
        for y in self._starts(height, self.tile_size, step):
            for x in self._starts(width, self.tile_size, step):
                patch = image[y : y + self.tile_size, x : x + self.tile_size]
                predictions = self._predict_patch(patch, use_tta)
                patch_height, patch_width = patch.shape[:2]
                weight = blending[:patch_height, :patch_width]
                for total, prediction in zip(totals, predictions, strict=True):
                    total[y : y + patch_height, x : x + patch_width] += prediction * weight
                weights[y : y + patch_height, x : x + patch_width] += weight
        return tuple(total / np.maximum(weights, 1e-6) for total in totals)

    def predict_full(
        self,
        image: np.ndarray,
        use_tta: bool = False,
        mask_threshold: float = 0.5,
        peak_threshold: float = 0.35,
        min_size: int = 10,
    ) -> dict[str, np.ndarray]:
        mask, distance, uncertainty = self._predict_tiled(image, use_tta)
        instances = postprocess_instances(mask, distance, mask_threshold, peak_threshold, min_size)
        return {
            "mask": mask,
            "dist_map": distance,
            "uncertainty": uncertainty,
            "instances": instances,
        }
