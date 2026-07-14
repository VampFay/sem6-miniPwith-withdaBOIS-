from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

from src.config import Config, select_device
from src.inference import AttnDistInference, PostprocessConfig
from src.training.data import official_fold_split
from src.utils.metrics import calculate_instance_metrics, calculate_metrics


def sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def bootstrap_interval(values: list[float], seed: int, samples: int = 2000) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    array = np.asarray(values)
    generator = np.random.default_rng(seed)
    means = generator.choice(array, size=(samples, len(array)), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a checkpoint on the untouched test split"
    )
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=Path("outputs_v2/evaluation"))
    parser.add_argument("--tta", action="store_true")
    parser.add_argument("--limit", type=int, help="Optional smoke-test limit")
    parser.add_argument("--mask-threshold", type=float)
    parser.add_argument("--peak-threshold", type=float)
    parser.add_argument("--min-size", type=int)
    parser.add_argument("--gaussian-sigma", type=float)
    parser.add_argument("--peak-window-size", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be a positive integer")
    config = Config()
    images = np.load(config.data_dir / "images.npy", mmap_mode="r")
    instances = np.load(config.data_dir / "instances.npy", mmap_mode="r")
    folds = np.load(config.data_dir / "folds.npy", mmap_mode="r")
    _, _, test_ids = official_fold_split(
        folds, config.train_fold, config.validation_fold, config.test_fold
    )
    if args.limit:
        test_ids = test_ids[: args.limit]
    engine = AttnDistInference.from_checkpoint(args.checkpoint, select_device())
    postprocessing = PostprocessConfig(
        mask_threshold=engine.postprocess.mask_threshold
        if args.mask_threshold is None
        else args.mask_threshold,
        peak_threshold=engine.postprocess.peak_threshold
        if args.peak_threshold is None
        else args.peak_threshold,
        min_size=engine.postprocess.min_size if args.min_size is None else args.min_size,
        gaussian_sigma=engine.postprocess.gaussian_sigma
        if args.gaussian_sigma is None
        else args.gaussian_sigma,
        peak_window_size=engine.postprocess.peak_window_size
        if args.peak_window_size is None
        else args.peak_window_size,
    )
    rows: list[dict[str, float | int]] = []
    for index in tqdm(test_ids, desc="test evaluation"):
        result = engine.predict_full(
            images[index],
            use_tta=args.tta,
            mask_threshold=postprocessing.mask_threshold,
            peak_threshold=postprocessing.peak_threshold,
            min_size=postprocessing.min_size,
            gaussian_sigma=postprocessing.gaussian_sigma,
            peak_window_size=postprocessing.peak_window_size,
        )
        truth = instances[index]
        binary = (truth > 0).astype(np.uint8)
        semantic = calculate_metrics(binary, result["mask"] >= postprocessing.mask_threshold)
        instance_metrics = calculate_instance_metrics(truth, result["instances"])
        rows.append({"index": int(index), **semantic, **asdict(instance_metrics)})

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "per_image.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    metric_names = [name for name in rows[0] if name != "index"]
    summary = {
        "evaluation_scope": "official_test_fold" if args.limit is None else "smoke_test_subset",
        "created_at": datetime.now(UTC).isoformat(),
        "checkpoint": {
            "file": args.checkpoint.name,
            "sha256": sha256(args.checkpoint),
        },
        "test_samples": len(rows),
        "fold_protocol": {
            "train": config.train_fold,
            "validation": config.validation_fold,
            "test": config.test_fold,
        },
        "settings": {"tta": args.tta, **postprocessing.as_dict()},
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": str(engine.device),
        },
        "metrics": {
            name: {
                "mean": float(np.mean([float(row[name]) for row in rows])),
                "std": float(np.std([float(row[name]) for row in rows])),
                "ci95": bootstrap_interval([float(row[name]) for row in rows], config.seed),
            }
            for name in metric_names
        },
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
