from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from tqdm import tqdm

from src.config import Config, select_device
from src.inference import AttnDistInference, PostprocessConfig, postprocess_instances
from src.training.data import official_fold_split
from src.utils.metrics import calculate_instance_metrics, calculate_metrics


def sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def parse_floats(value: str) -> list[float]:
    try:
        values = [float(item) for item in value.split(",")]
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected comma-separated numbers") from error
    if not values:
        raise argparse.ArgumentTypeError("At least one value is required")
    return values


def parse_ints(value: str) -> list[int]:
    try:
        values = [int(item) for item in value.split(",")]
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected comma-separated integers") from error
    if not values:
        raise argparse.ArgumentTypeError("At least one value is required")
    return values


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def write_calibrated_checkpoint(
    source: Path,
    destination: Path,
    settings: PostprocessConfig,
    validation_result: dict[str, float],
) -> str:
    if source.resolve() == destination.resolve():
        raise ValueError("Calibrated checkpoint must not overwrite its source checkpoint")
    checkpoint = torch.load(source, map_location="cpu", weights_only=True)
    if checkpoint.get("format_version") != 2 or checkpoint.get("artifact_type") != (
        "attn-dist-inference"
    ):
        raise ValueError("Calibration requires a version-2 inference checkpoint")
    checkpoint["postprocessing"] = settings.as_dict()
    checkpoint["calibration"] = {
        "scope": "validation_fold_2_only",
        "selection_metric": "pq",
        "source_checkpoint_sha256": sha256(source),
        "samples": int(validation_result["samples"]),
        "validation_metrics": {
            name: float(validation_result[name])
            for name in ("dice", "aji", "pq", "detection_f1", "sq")
        },
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    torch.save(checkpoint, temporary)
    temporary.replace(destination)
    return sha256(destination)


def selected_positions(sample_count: int, search_samples: int, seed: int) -> np.ndarray:
    if search_samples >= sample_count:
        return np.arange(sample_count, dtype=np.int64)
    generator = np.random.default_rng(seed)
    return np.sort(generator.choice(sample_count, size=search_samples, replace=False))


def cache_identity(
    checkpoint: Path, data_dir: Path, validation_ids: np.ndarray, use_tta: bool
) -> dict[str, Any]:
    manifest = data_dir / "manifest.json"
    return {
        "format": "attn-dist-prediction-cache-v1",
        "checkpoint_sha256": sha256(checkpoint),
        "dataset_manifest_sha256": sha256(manifest) if manifest.is_file() else None,
        "fold": "validation",
        "samples": len(validation_ids),
        "indices_sha256": hashlib.sha256(validation_ids.tobytes()).hexdigest(),
        "tta": use_tta,
        "dtype": "float32",
    }


def valid_cache(cache_dir: Path, identity: dict[str, Any]) -> bool:
    metadata_path = cache_dir / "metadata.json"
    if not metadata_path.is_file():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        masks = np.load(cache_dir / "masks.npy", mmap_mode="r")
        distances = np.load(cache_dir / "distances.npy", mmap_mode="r")
        indices = np.load(cache_dir / "indices.npy")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    expected_shape = (identity["samples"], 256, 256)
    return bool(
        metadata == identity
        and masks.shape == expected_shape
        and distances.shape == expected_shape
        and masks.dtype == np.float32
        and distances.dtype == np.float32
        and hashlib.sha256(indices.tobytes()).hexdigest() == identity["indices_sha256"]
    )


def build_prediction_cache(
    checkpoint: Path,
    cache_dir: Path,
    images: np.ndarray,
    validation_ids: np.ndarray,
    identity: dict[str, Any],
    use_tta: bool,
) -> None:
    required = len(validation_ids) * 256 * 256 * np.dtype(np.float32).itemsize * 2
    cache_dir.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(cache_dir).free < int(required * 1.1):
        raise OSError(f"Prediction cache requires at least {required * 1.1 / 2**30:.1f} GiB free")
    masks = np.lib.format.open_memmap(
        cache_dir / "masks.npy",
        mode="w+",
        dtype=np.float32,
        shape=(len(validation_ids), 256, 256),
    )
    distances = np.lib.format.open_memmap(
        cache_dir / "distances.npy",
        mode="w+",
        dtype=np.float32,
        shape=(len(validation_ids), 256, 256),
    )
    np.save(cache_dir / "indices.npy", validation_ids)
    engine = AttnDistInference.from_checkpoint(checkpoint, select_device())
    for position, index in enumerate(tqdm(validation_ids, desc="validation inference")):
        prediction = engine.predict_maps(images[index], use_tta=use_tta)
        masks[position] = prediction["mask"]
        distances[position] = prediction["dist_map"]
    masks.flush()
    distances.flush()
    atomic_json(cache_dir / "metadata.json", identity)


def score_settings(
    settings: PostprocessConfig,
    positions: np.ndarray,
    masks: np.ndarray,
    distances: np.ndarray,
    instances: np.ndarray,
    validation_ids: np.ndarray,
) -> dict[str, float]:
    totals = {"dice": 0.0, "aji": 0.0, "pq": 0.0, "detection_f1": 0.0, "sq": 0.0}
    started = time.perf_counter()
    for position in positions:
        prediction = postprocess_instances(
            masks[position],
            distances[position],
            settings.mask_threshold,
            settings.peak_threshold,
            settings.min_size,
            settings.gaussian_sigma,
            settings.peak_window_size,
        )
        truth = instances[validation_ids[position]]
        instance_metrics = calculate_instance_metrics(truth, prediction)
        semantic = calculate_metrics(truth > 0, masks[position] >= settings.mask_threshold)
        totals["dice"] += semantic["Dice"]
        totals["aji"] += instance_metrics.aji
        totals["pq"] += instance_metrics.pq
        totals["detection_f1"] += instance_metrics.detection_f1
        totals["sq"] += instance_metrics.segmentation_quality
    count = len(positions)
    return {
        **settings.as_dict(),
        **{name: value / count for name, value in totals.items()},
        "samples": float(count),
        "seconds": time.perf_counter() - started,
    }


def rank_key(row: dict[str, float | int]) -> tuple[float, float, float]:
    return (-float(row["pq"]), -float(row["detection_f1"]), -float(row["aji"]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tune instance postprocessing on PanNuke validation fold 2 only"
    )
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--cache", type=Path, default=Path("outputs_v2/tuning/fold2_cache"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs_v2/tuning/postprocessing_search.json"),
    )
    parser.add_argument(
        "--calibrated-checkpoint",
        type=Path,
        help="Write a deployment checkpoint containing the selected fold-2 parameters",
    )
    parser.add_argument("--search-samples", type=int, default=384)
    parser.add_argument("--finalists", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tta", action="store_true")
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument(
        "--mask-thresholds", type=parse_floats, default=parse_floats("0.35,0.4,0.45,0.5,0.55,0.6")
    )
    parser.add_argument(
        "--peak-thresholds",
        type=parse_floats,
        default=parse_floats("0.2,0.25,0.3,0.35,0.4,0.45"),
    )
    parser.add_argument("--min-sizes", type=parse_ints, default=parse_ints("5,10,20,30"))
    parser.add_argument("--gaussian-sigmas", type=parse_floats, default=[1.0])
    parser.add_argument("--peak-window-sizes", type=parse_ints, default=[7])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.search_samples < 1 or args.finalists < 1:
        raise ValueError("Search samples and finalist count must be positive")
    config = Config()
    images = np.load(config.data_dir / "images.npy", mmap_mode="r")
    instances = np.load(config.data_dir / "instances.npy", mmap_mode="r")
    folds = np.load(config.data_dir / "folds.npy", mmap_mode="r")
    _, validation_ids, _ = official_fold_split(
        folds, config.train_fold, config.validation_fold, config.test_fold
    )
    identity = cache_identity(args.checkpoint, config.data_dir, validation_ids, args.tta)
    if args.rebuild_cache or not valid_cache(args.cache, identity):
        build_prediction_cache(
            args.checkpoint, args.cache, images, validation_ids, identity, args.tta
        )
    masks = np.load(args.cache / "masks.npy", mmap_mode="r")
    distances = np.load(args.cache / "distances.npy", mmap_mode="r")
    positions = selected_positions(len(validation_ids), args.search_samples, args.seed)
    grid = [
        PostprocessConfig(mask, peak, size, sigma, window)
        for mask, peak, size, sigma, window in itertools.product(
            args.mask_thresholds,
            args.peak_thresholds,
            args.min_sizes,
            args.gaussian_sigmas,
            args.peak_window_sizes,
        )
    ]
    coarse = [
        score_settings(settings, positions, masks, distances, instances, validation_ids)
        for settings in tqdm(grid, desc="coarse search")
    ]
    coarse.sort(key=rank_key)
    baseline = PostprocessConfig()
    finalist_settings = [
        PostprocessConfig(
            float(row["mask_threshold"]),
            float(row["peak_threshold"]),
            int(row["min_size"]),
            float(row["gaussian_sigma"]),
            int(row["peak_window_size"]),
        )
        for row in coarse[: args.finalists]
    ]
    if baseline not in finalist_settings:
        finalist_settings.append(baseline)
    full_positions = np.arange(len(validation_ids), dtype=np.int64)
    finalists = [
        score_settings(settings, full_positions, masks, distances, instances, validation_ids)
        for settings in tqdm(finalist_settings, desc="full validation")
    ]
    finalists.sort(key=rank_key)
    baseline_result = next(
        row
        for row in finalists
        if all(row[name] == value for name, value in baseline.as_dict().items())
    )
    best = finalists[0]
    report = {
        "format": "attn-dist-postprocessing-search-v1",
        "scope": "validation_fold_2_only",
        "checkpoint_sha256": identity["checkpoint_sha256"],
        "dataset_manifest_sha256": identity["dataset_manifest_sha256"],
        "cache": identity,
        "search": {
            "seed": args.seed,
            "coarse_samples": len(positions),
            "grid_size": len(grid),
            "finalists": len(finalist_settings),
        },
        "baseline": baseline_result,
        "best": best,
        "absolute_gain": {
            name: float(best[name]) - float(baseline_result[name])
            for name in ("dice", "aji", "pq", "detection_f1", "sq")
        },
        "full_validation_leaderboard": finalists,
        "coarse_leaderboard": coarse,
    }
    if args.calibrated_checkpoint is not None:
        best_settings = PostprocessConfig(
            float(best["mask_threshold"]),
            float(best["peak_threshold"]),
            int(best["min_size"]),
            float(best["gaussian_sigma"]),
            int(best["peak_window_size"]),
        )
        calibrated_sha256 = write_calibrated_checkpoint(
            args.checkpoint, args.calibrated_checkpoint, best_settings, best
        )
        report["calibrated_checkpoint"] = {
            "file": args.calibrated_checkpoint.name,
            "sha256": calibrated_sha256,
        }
    atomic_json(args.output, report)
    concise = {key: report[key] for key in ("scope", "baseline", "best", "absolute_gain")}
    print(json.dumps(concise, indent=2))


if __name__ == "__main__":
    main()
