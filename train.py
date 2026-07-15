from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Literal, cast

from src.config import Config, seed_everything
from src.models.factory import build_model
from src.training.data import build_dataloaders
from src.training.trainer import Trainer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Attn-Dist-Net on prepared PanNuke arrays")
    parser.add_argument("--resume", type=Path, help="Checkpoint to resume, usually last_model.pt")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--encoder", default="efficientnet-b0")
    parser.add_argument(
        "--model", choices=["attn-dist", "unet", "unetplusplus"], default="attn-dist"
    )
    parser.add_argument("--offline", action="store_true", help="Do not download pretrained weights")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs_v2"))
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=20,
        help="Validation epochs without improvement; 0 disables early stopping",
    )
    parser.add_argument(
        "--distance-activation", choices=["identity", "sigmoid"], default="sigmoid"
    )
    parser.add_argument("--distance-background-weight", type=float, default=0.1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    config = Config(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
        encoder=args.encoder,
        model_name=args.model,
        encoder_weights=None if args.offline else "imagenet",
        output_dir=args.output_dir,
        early_stopping_patience=args.early_stopping_patience,
        distance_activation=cast(Literal["identity", "sigmoid"], args.distance_activation),
        distance_background_weight=args.distance_background_weight,
    )
    config.setup_dirs()
    seed_everything(config.seed)
    model = build_model(config.model_name, config.encoder, config.encoder_weights)
    trainer = Trainer(config, model, build_dataloaders(config))
    if args.resume:
        trainer.resume(args.resume)
    trainer.fit()


if __name__ == "__main__":
    main()
