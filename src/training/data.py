from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch.utils.data import DataLoader

from src.config import Config
from src.preprocessing.dataset import PanNukeDataset
from src.preprocessing.transforms import training_transforms


@dataclass(frozen=True)
class DataLoaders:
    train: DataLoader
    validation: DataLoader
    test: DataLoader


def official_fold_split(
    folds: np.ndarray, train_fold: int, validation_fold: int, test_fold: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    selected = (train_fold, validation_fold, test_fold)
    if sorted(selected) != [1, 2, 3]:
        raise ValueError("Train, validation, and test folds must be a permutation of 1, 2, 3")
    if folds.ndim != 1 or not np.all(np.isin(folds, [1, 2, 3])):
        raise ValueError("Fold labels must be a one-dimensional array containing only 1, 2, and 3")
    split = tuple(np.asarray(np.flatnonzero(folds == fold), dtype=np.int64) for fold in selected)
    if any(len(indices) == 0 for indices in split):
        raise ValueError("Every configured PanNuke fold must contain at least one sample")
    return split[0], split[1], split[2]


def build_dataloaders(config: Config) -> DataLoaders:
    image_path = config.data_dir / "images.npy"
    instance_path = config.data_dir / "instances.npy"
    distance_path = config.data_dir / "distances.npy"
    folds = np.load(config.data_dir / "folds.npy", mmap_mode="r")
    probe = PanNukeDataset(image_path, instance_path, distance_path)
    if len(folds) != len(probe):
        raise ValueError("Fold labels must contain one value per sample")
    train_ids, val_ids, test_ids = official_fold_split(
        folds, config.train_fold, config.validation_fold, config.test_fold
    )

    def dataset(indices: np.ndarray, training: bool) -> PanNukeDataset:
        return PanNukeDataset(
            image_path,
            instance_path,
            distance_path,
            transforms=training_transforms() if training else None,
            stain_aug=training,
            indices=indices.tolist(),
        )

    generator = torch.Generator().manual_seed(config.seed)
    return DataLoaders(
        train=DataLoader(
            dataset(train_ids, True),
            batch_size=config.batch_size,
            shuffle=True,
            generator=generator,
            num_workers=config.num_workers,
            pin_memory=config.device.type == "cuda",
        ),
        validation=DataLoader(
            dataset(val_ids, False),
            batch_size=config.batch_size,
            shuffle=False,
            num_workers=config.num_workers,
            pin_memory=config.device.type == "cuda",
        ),
        test=DataLoader(
            dataset(test_ids, False),
            batch_size=config.batch_size,
            shuffle=False,
            num_workers=config.num_workers,
            pin_memory=config.device.type == "cuda",
        ),
    )
