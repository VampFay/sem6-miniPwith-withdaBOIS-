from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from src.preprocessing.instances import instance_distance_map

DATASET_ID = "MedOtter/PanNuke"
DATASET_REVISION = "8bfedc274e5df3c5afcf258e4d05a968b197e88f"
FOLD_COUNTS = {1: 2656, 2: 2523, 3: 2722}
HEIGHT = 256
WIDTH = 256


def required_bytes(include_distances: bool) -> int:
    bytes_per_pixel = 3 + 2 + (2 if include_distances else 0)
    return sum(FOLD_COUNTS.values()) * HEIGHT * WIDTH * bytes_per_pixel + sum(
        FOLD_COUNTS.values()
    )


def check_space(output_dir: Path, include_distances: bool) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    needed = required_bytes(include_distances)
    available = shutil.disk_usage(output_dir.parent).free
    minimum = int(needed * 1.1)
    if available < minimum:
        raise OSError(
            f"PanNuke preparation needs at least {minimum / 2**30:.1f} GiB free; "
            f"only {available / 2**30:.1f} GiB is available"
        )


def load_streams() -> Any:
    try:
        from datasets import load_dataset
    except ImportError as error:
        raise SystemExit(
            'PanNuke preparation requires the data extra: python -m pip install -e ".[data]"'
        ) from error
    return load_dataset(DATASET_ID, revision=DATASET_REVISION, streaming=True)


def prepare(output_dir: Path, include_distances: bool) -> None:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to replace existing dataset directory: {output_dir}")
    check_space(output_dir, include_distances)
    partial = output_dir.with_name(f"{output_dir.name}.partial")
    if partial.exists():
        raise FileExistsError(f"Remove the incomplete preparation directory first: {partial}")

    partial.mkdir()
    sample_count = sum(FOLD_COUNTS.values())
    images = np.lib.format.open_memmap(
        partial / "images.npy", mode="w+", dtype=np.uint8, shape=(sample_count, 256, 256, 3)
    )
    instances = np.lib.format.open_memmap(
        partial / "instances.npy", mode="w+", dtype=np.uint16, shape=(sample_count, 256, 256)
    )
    folds = np.lib.format.open_memmap(
        partial / "folds.npy", mode="w+", dtype=np.uint8, shape=(sample_count,)
    )
    distances = (
        np.lib.format.open_memmap(
            partial / "distances.npy",
            mode="w+",
            dtype=np.float16,
            shape=(sample_count, 256, 256),
        )
        if include_distances
        else None
    )

    streams = load_streams()
    offset = 0
    for fold, expected_count in FOLD_COUNTS.items():
        split_name = f"fold{fold}"
        if split_name not in streams:
            raise KeyError(f"Pinned dataset revision is missing split {split_name}")
        seen = 0
        for row in tqdm(streams[split_name], total=expected_count, desc=split_name):
            image = np.asarray(row["image"].convert("RGB"), dtype=np.uint8)
            instance_map = np.asarray(row["inst_map"], dtype=np.uint16)
            if image.shape != (HEIGHT, WIDTH, 3):
                raise ValueError(f"Unexpected image shape in {split_name}: {image.shape}")
            if instance_map.shape != (HEIGHT, WIDTH):
                raise ValueError(
                    f"Unexpected instance-map shape in {split_name}: {instance_map.shape}"
                )
            index = offset + seen
            images[index] = image
            instances[index] = instance_map
            folds[index] = fold
            if distances is not None:
                distances[index] = instance_distance_map(instance_map).astype(np.float16)
            seen += 1
        if seen != expected_count:
            raise ValueError(f"{split_name} contains {seen} rows; expected {expected_count}")
        offset += seen

    for array in (images, instances, folds, distances):
        if array is not None:
            array.flush()
    provenance = {
        "source": DATASET_ID,
        "revision": DATASET_REVISION,
        "license": "CC BY-NC-SA 4.0",
        "fold_counts": FOLD_COUNTS,
        "distance_maps": include_distances,
    }
    (partial / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    os.replace(partial, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the pinned PanNuke dataset mirror")
    parser.add_argument("--output", type=Path, default=Path("data/pannuke"))
    parser.add_argument("--no-distances", action="store_true")
    parser.add_argument("--preflight", action="store_true", help="Check disk space and exit")
    args = parser.parse_args()
    include_distances = not args.no_distances
    try:
        if args.preflight:
            check_space(args.output, include_distances)
            print("PanNuke preparation disk-space preflight passed")
        else:
            prepare(args.output, include_distances)
    except (FileExistsError, OSError) as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
