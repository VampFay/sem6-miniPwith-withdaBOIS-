from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.config import Config, seed_everything
from src.models.factory import build_model
from src.training.data import build_dataloaders
from src.training.trainer import Trainer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Attn-Dist-Net on prepared PanNuke arrays")
    parser.add_argument("--resume", type=Path, help="Checkpoint to resume, usually last_model.pt")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--encoder", default="efficientnet-b0")
    parser.add_argument(
        "--model", choices=["attn-dist", "unet", "unetplusplus"], default="attn-dist"
    )
    parser.add_argument("--offline", action="store_true", help="Do not download pretrained weights")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    config = Config(
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        encoder=args.encoder,
        model_name=args.model,
        encoder_weights=None if args.offline else "imagenet",
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
