from __future__ import annotations

import os
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


@dataclass(slots=True)
class Config:
    project_name: str = "Attn-Dist-Net"
    seed: int = 42
    encoder: str = "efficientnet-b0"
    model_name: str = "attn-dist"
    encoder_weights: str | None = "imagenet"
    batch_size: int = 8
    epochs: int = 150
    learning_rate: float = 5e-5
    weight_decay: float = 1e-4
    train_fold: int = 1
    validation_fold: int = 2
    test_fold: int = 3
    num_workers: int = 0
    threshold: float = 0.5
    peak_threshold: float = 0.35
    min_instance_area: int = 10
    distance_smoothing_sigma: float = 1.0
    peak_window_size: int = 7
    gradient_clip: float = 1.0
    early_stopping_patience: int = 20
    mask_loss_weight: float = 1.0
    distance_loss_weight: float = 0.5
    auxiliary_loss_weight: float = 0.2
    distance_activation: Literal["identity", "sigmoid"] = "sigmoid"
    distance_background_weight: float = 0.1
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("ATTNDIST_DATA_DIR", "data/pannuke"))
    )
    output_dir: Path = field(
        default_factory=lambda: Path(os.getenv("ATTNDIST_OUTPUT_DIR", "outputs_v2"))
    )
    device: torch.device = field(default_factory=select_device)

    def __post_init__(self) -> None:
        if self.epochs < 1 or self.batch_size < 1:
            raise ValueError("Epochs and batch size must be positive")
        if self.learning_rate <= 0 or self.weight_decay < 0:
            raise ValueError("Learning rate must be positive and weight decay non-negative")
        if self.early_stopping_patience < 0:
            raise ValueError("Early-stopping patience must be non-negative")
        if min(
            self.mask_loss_weight,
            self.distance_loss_weight,
            self.auxiliary_loss_weight,
            self.distance_background_weight,
        ) < 0:
            raise ValueError("Loss weights must be non-negative")

    @property
    def checkpoint_dir(self) -> Path:
        return self.output_dir / "checkpoints"

    @property
    def log_dir(self) -> Path:
        return self.output_dir / "logs"

    def setup_dirs(self) -> None:
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def as_serializable_dict(self) -> dict[str, Any]:
        values = asdict(self)
        values["data_dir"] = str(self.data_dir)
        values["output_dir"] = str(self.output_dir)
        values["device"] = str(self.device)
        return values


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
