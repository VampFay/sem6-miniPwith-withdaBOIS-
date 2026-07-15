from __future__ import annotations

import csv
import hashlib
import logging
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

from src.config import Config
from src.inference import PostprocessConfig
from src.training.data import DataLoaders
from src.utils.losses import AttnDistComboLoss, LossOutput
from src.utils.metrics import calculate_metrics

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EpochResult:
    loss: float
    mask_loss: float = 0.0
    distance_loss: float = 0.0
    distance_foreground_loss: float = 0.0
    distance_background_loss: float = 0.0
    deep_supervision_loss: float = 0.0
    dice: float = 0.0
    iou: float = 0.0


class Trainer:
    def __init__(self, config: Config, model: nn.Module, loaders: DataLoaders) -> None:
        self.config = config
        self.model = model.to(config.device)
        self.loaders = loaders
        self.criterion = AttnDistComboLoss(
            mask_weight=config.mask_loss_weight,
            distance_weight=config.distance_loss_weight,
            auxiliary_weight=config.auxiliary_loss_weight,
            distance_activation=config.distance_activation,
            distance_background_weight=config.distance_background_weight,
        )
        self.optimizer = AdamW(
            model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
        )
        self.scheduler = CosineAnnealingLR(self.optimizer, T_max=config.epochs)
        self.scaler = torch.amp.GradScaler("cuda", enabled=config.device.type == "cuda")
        self.writer = SummaryWriter(config.log_dir)
        self.start_epoch = 0
        self.best_iou = -1.0
        self.stale_epochs = 0

    def _autocast(self) -> AbstractContextManager[None]:
        if self.config.device.type == "cuda":
            return torch.amp.autocast("cuda")
        return nullcontext()

    def _batch_targets(self, batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, ...]:
        return (
            batch["image"].to(self.config.device),
            batch["mask"].to(self.config.device),
            batch["dist"].to(self.config.device),
        )

    @staticmethod
    def _accumulate_loss(totals: dict[str, list[float]], output: LossOutput) -> None:
        components = {
            "loss": output.total,
            "mask_loss": output.mask,
            "distance_loss": output.distance,
            "distance_foreground_loss": output.distance_foreground,
            "distance_background_loss": output.distance_background,
            "deep_supervision_loss": output.deep_supervision,
        }
        for name, value in components.items():
            totals[name].append(float(value.detach()))

    @staticmethod
    def _epoch_result(totals: dict[str, list[float]], **metrics: float) -> EpochResult:
        return EpochResult(
            loss=float(np.mean(totals["loss"])),
            mask_loss=float(np.mean(totals["mask_loss"])),
            distance_loss=float(np.mean(totals["distance_loss"])),
            distance_foreground_loss=float(np.mean(totals["distance_foreground_loss"])),
            distance_background_loss=float(np.mean(totals["distance_background_loss"])),
            deep_supervision_loss=float(np.mean(totals["deep_supervision_loss"])),
            dice=metrics.get("dice", 0.0),
            iou=metrics.get("iou", 0.0),
        )

    @staticmethod
    def _loss_totals() -> dict[str, list[float]]:
        return {
            "loss": [],
            "mask_loss": [],
            "distance_loss": [],
            "distance_foreground_loss": [],
            "distance_background_loss": [],
            "deep_supervision_loss": [],
        }

    def train_epoch(self, epoch: int) -> EpochResult:
        self.model.train()
        totals = self._loss_totals()
        progress = tqdm(self.loaders.train, desc=f"Epoch {epoch + 1}/{self.config.epochs} train")
        for batch in progress:
            images, masks, distances = self._batch_targets(batch)
            self.optimizer.zero_grad(set_to_none=True)
            with self._autocast():
                loss_output = self.criterion(self.model(images), masks, distances)
                loss = loss_output.total
            if not torch.isfinite(loss):
                raise FloatingPointError(f"Non-finite training loss at epoch {epoch + 1}")
            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimizer)
            nn.utils.clip_grad_norm_(self.model.parameters(), self.config.gradient_clip)
            self.scaler.step(self.optimizer)
            self.scaler.update()
            self._accumulate_loss(totals, loss_output)
            progress.set_postfix(loss=f"{totals['loss'][-1]:.4f}")
        return self._epoch_result(totals)

    @torch.inference_mode()
    def validate(self) -> EpochResult:
        self.model.eval()
        totals = self._loss_totals()
        metrics: list[dict[str, float]] = []
        for batch in tqdm(self.loaders.validation, desc="validation"):
            images, masks, distances = self._batch_targets(batch)
            output = self.model(images)
            self._accumulate_loss(totals, self.criterion(output, masks, distances))
            predictions = torch.sigmoid(output.mask_logits) >= self.config.threshold
            for target, prediction in zip(
                masks.cpu().numpy(), predictions.cpu().numpy(), strict=True
            ):
                metrics.append(calculate_metrics(target[0], prediction[0]))
        return self._epoch_result(
            totals,
            dice=float(np.mean([metric["Dice"] for metric in metrics])),
            iou=float(np.mean([metric["IoU"] for metric in metrics])),
        )

    def checkpoint_state(self, epoch: int) -> dict[str, Any]:
        return {
            "format_version": 2,
            "artifact_type": "attn-dist-training",
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "scaler_state_dict": self.scaler.state_dict(),
            "best_iou": self.best_iou,
            "stale_epochs": self.stale_epochs,
            "config": self.config.as_serializable_dict(),
            "torch_rng_state": torch.get_rng_state(),
            "numpy_rng_state": np.random.get_state(),
        }

    @staticmethod
    def _save_state(path: Path, state: dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        torch.save(state, temporary)
        temporary.replace(path)

    def save_training_checkpoint(self, path: Path, epoch: int) -> None:
        self._save_state(path, self.checkpoint_state(epoch))

    def save_inference_checkpoint(
        self, path: Path, epoch: int, validation: EpochResult
    ) -> None:
        manifest_path = self.config.data_dir / "manifest.json"
        manifest_sha256 = (
            hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            if manifest_path.is_file()
            else None
        )
        self._save_state(
            path,
            {
                "format_version": 2,
                "artifact_type": "attn-dist-inference",
                "epoch": epoch,
                "model_state_dict": self.model.state_dict(),
                "config": self.config.as_serializable_dict(),
                "model_contract": {
                    "distance_activation": self.config.distance_activation,
                },
                "validation": {
                    "loss": validation.loss,
                    "dice": validation.dice,
                    "iou": validation.iou,
                },
                "postprocessing": PostprocessConfig(
                    mask_threshold=self.config.threshold,
                    peak_threshold=self.config.peak_threshold,
                    min_size=self.config.min_instance_area,
                    gaussian_sigma=self.config.distance_smoothing_sigma,
                    peak_window_size=self.config.peak_window_size,
                ).as_dict(),
                "dataset": {
                    "manifest_sha256": manifest_sha256,
                    "train_fold": self.config.train_fold,
                    "validation_fold": self.config.validation_fold,
                    "test_fold": self.config.test_fold,
                },
            },
        )

    def resume(self, path: Path) -> None:
        # RNG state is always a CPU ByteTensor. Loading the complete training
        # state onto MPS makes torch.set_rng_state reject that tensor.
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        if checkpoint.get("format_version") != 2:
            raise ValueError(f"Unsupported checkpoint format: {checkpoint.get('format_version')}")
        if checkpoint.get("artifact_type") != "attn-dist-training":
            raise ValueError("Resume requires a training checkpoint, not an inference artifact")
        self.model.load_state_dict(checkpoint["model_state_dict"], strict=True)
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        self.scaler.load_state_dict(checkpoint["scaler_state_dict"])
        self.start_epoch = int(checkpoint["epoch"]) + 1
        self.best_iou = float(checkpoint["best_iou"])
        self.stale_epochs = int(checkpoint.get("stale_epochs", 0))
        torch.set_rng_state(checkpoint["torch_rng_state"])
        np.random.set_state(checkpoint["numpy_rng_state"])

    def _record(self, epoch: int, train: EpochResult, validation: EpochResult) -> None:
        values = {
            "epoch": epoch + 1,
            "train_loss": train.loss,
            "train_mask_loss": train.mask_loss,
            "train_distance_loss": train.distance_loss,
            "train_distance_foreground_loss": train.distance_foreground_loss,
            "train_distance_background_loss": train.distance_background_loss,
            "train_deep_supervision_loss": train.deep_supervision_loss,
            "validation_loss": validation.loss,
            "validation_mask_loss": validation.mask_loss,
            "validation_distance_loss": validation.distance_loss,
            "validation_distance_foreground_loss": validation.distance_foreground_loss,
            "validation_distance_background_loss": validation.distance_background_loss,
            "validation_deep_supervision_loss": validation.deep_supervision_loss,
            "validation_dice": validation.dice,
            "validation_iou": validation.iou,
            "learning_rate": self.optimizer.param_groups[0]["lr"],
        }
        csv_path = self.config.log_dir / "metrics.csv"
        write_header = not csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=values.keys())
            if write_header:
                writer.writeheader()
            writer.writerow(values)
        for name, value in values.items():
            if name != "epoch":
                self.writer.add_scalar(name, value, epoch)

    def fit(self) -> None:
        try:
            for epoch in range(self.start_epoch, self.config.epochs):
                train_result = self.train_epoch(epoch)
                validation_result = self.validate()
                self.scheduler.step()
                improved = validation_result.iou > self.best_iou
                if improved:
                    self.best_iou = validation_result.iou
                    self.stale_epochs = 0
                else:
                    self.stale_epochs += 1
                self._record(epoch, train_result, validation_result)
                self.save_training_checkpoint(self.config.checkpoint_dir / "last_model.pt", epoch)
                if improved:
                    self.save_inference_checkpoint(
                        self.config.checkpoint_dir / "best_iou.pt", epoch, validation_result
                    )
                LOGGER.info(
                    "epoch=%d train_loss=%.4f val_loss=%.4f val_dice=%.4f val_iou=%.4f",
                    epoch + 1,
                    train_result.loss,
                    validation_result.loss,
                    validation_result.dice,
                    validation_result.iou,
                )
                if (
                    self.config.early_stopping_patience > 0
                    and self.stale_epochs >= self.config.early_stopping_patience
                ):
                    LOGGER.info("Early stopping after %d stale epochs", self.stale_epochs)
                    break
        finally:
            self.writer.close()
