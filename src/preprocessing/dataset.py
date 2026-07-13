from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import albumentations as A
import numpy as np
import torch
import torchvision.transforms.functional as TF
from torch.utils.data import Dataset

from src.config import IMAGENET_MEAN, IMAGENET_STD
from src.preprocessing.instances import instance_distance_map


def _load_array(path: str | Path) -> np.ndarray:
    path = Path(path)
    if path.suffix != ".npy":
        raise ValueError(f"Prepared arrays must use the memory-mappable .npy format: {path}")
    return cast(np.ndarray, np.load(path, mmap_mode="r"))


class PanNukeDataset(Dataset[dict[str, torch.Tensor]]):
    """PanNuke patches with semantic, instance, and normalized distance targets."""

    def __init__(
        self,
        img_path: str | Path,
        instance_path: str | Path,
        dist_path: str | Path | None = None,
        transforms: A.Compose | None = None,
        stain_aug: bool = False,
        indices: Sequence[int] | None = None,
    ) -> None:
        self.images = _load_array(img_path)
        self.instances = _load_array(instance_path)
        self.dists = _load_array(dist_path) if dist_path and Path(dist_path).exists() else None
        if len(self.images) != len(self.instances):
            raise ValueError("Image and instance arrays must contain the same number of samples")
        if self.dists is not None and len(self.dists) != len(self.images):
            raise ValueError("Distance array must contain the same number of samples as images")
        if self.images.ndim != 4 or self.images.shape[-1] != 3:
            raise ValueError("Images must have shape [N, H, W, 3]")
        if self.instances.ndim != 3 or self.instances.shape != self.images.shape[:3]:
            raise ValueError("Instances must have shape [N, H, W]")

        self.indices = np.asarray(
            indices if indices is not None else np.arange(len(self.images)), dtype=np.int64
        )
        if np.any(self.indices < 0) or np.any(self.indices >= len(self.images)):
            raise IndexError("Dataset indices are outside the source arrays")
        self.transforms = transforms
        self.stain_transform = (
            A.Compose(
                [
                    A.RandomBrightnessContrast(0.2, 0.2, p=0.5),
                    A.HueSaturationValue(10, 20, 10, p=0.5),
                    A.CLAHE(p=0.5),
                ]
            )
            if stain_aug
            else None
        )

    def __len__(self) -> int:
        return len(self.indices)

    @staticmethod
    def _generate_distance_map(instance_mask: np.ndarray) -> np.ndarray:
        return instance_distance_map(instance_mask)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        source_index = int(self.indices[index])
        image = self.images[source_index].copy()
        instances = self.instances[source_index].astype(np.int32)
        semantic = (instances > 0).astype(np.uint8)
        distance = (
            self.dists[source_index].astype(np.float32)
            if self.dists is not None
            else self._generate_distance_map(instances)
        )

        if self.stain_transform is not None:
            image = self.stain_transform(image=image)["image"]
        if self.transforms is not None:
            transformed: dict[str, Any] = self.transforms(
                image=image, mask=semantic, distance=distance, instances=instances
            )
            image = transformed["image"]
            semantic = transformed["mask"]
            distance = transformed["distance"]
            instances = transformed["instances"]

        return {
            "image": TF.normalize(
                TF.to_tensor(np.ascontiguousarray(image)), IMAGENET_MEAN, IMAGENET_STD
            ),
            "mask": torch.from_numpy(np.ascontiguousarray(semantic)).unsqueeze(0).float(),
            "dist": torch.from_numpy(np.ascontiguousarray(distance)).unsqueeze(0).float(),
            "instances": torch.from_numpy(np.ascontiguousarray(instances)).long(),
            "index": torch.tensor(source_index, dtype=torch.long),
        }
