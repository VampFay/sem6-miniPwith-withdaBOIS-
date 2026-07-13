from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

EXPECTED_FOLD_COUNTS = {1: 2656, 2: 2523, 3: 2722}


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def describe(path: Path) -> tuple[np.ndarray, dict[str, object]]:
    array = np.load(path, mmap_mode="r")
    return array, {
        "file": path.name,
        "sha256": digest(path),
        "shape": list(array.shape),
        "dtype": str(array.dtype),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate prepared PanNuke arrays")
    parser.add_argument("data_dir", type=Path, nargs="?", default=Path("data/pannuke"))
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    images, image_info = describe(args.data_dir / "images.npy")
    instances, instance_info = describe(args.data_dir / "instances.npy")
    folds, fold_info = describe(args.data_dir / "folds.npy")
    distance_path = args.data_dir / "distances.npy"
    distances, distance_info = (
        describe(distance_path) if distance_path.exists() else (None, None)
    )

    if images.dtype != np.uint8 or images.ndim != 4 or images.shape[-1] != 3:
        raise ValueError("images.npy must be uint8 with shape [N, H, W, 3]")
    if instances.dtype != np.uint16 or instances.shape != images.shape[:3]:
        raise ValueError("instances.npy must be uint16 with shape [N, H, W]")
    if folds.dtype != np.uint8 or folds.shape != (len(images),):
        raise ValueError("folds.npy must be uint8 with shape [N]")
    if not np.all(np.isin(folds, [1, 2, 3])):
        raise ValueError("folds.npy contains a value outside the official folds 1, 2, and 3")
    if distances is not None:
        if distances.dtype != np.float16 or distances.shape != instances.shape:
            raise ValueError("distances.npy must be float16 with shape [N, H, W]")
        if float(distances.min()) < 0 or float(distances.max()) > 1:
            raise ValueError("distances.npy values must be in [0, 1]")

    fold_counts = {fold: int(np.count_nonzero(folds == fold)) for fold in (1, 2, 3)}
    if args.require_complete and fold_counts != EXPECTED_FOLD_COUNTS:
        raise ValueError(
            f"Complete PanNuke fold counts must be {EXPECTED_FOLD_COUNTS}, found {fold_counts}"
        )

    manifest = {
        "format": "prepared-pannuke-v2",
        "sample_count": len(images),
        "fold_counts": fold_counts,
        "arrays": [
            image_info,
            instance_info,
            fold_info,
            *([distance_info] if distance_info else []),
        ],
    }
    output = args.output or args.data_dir / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
