from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import resource
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image

from src.inference import AttnDistInference, postprocess_instances


@dataclass(frozen=True)
class Timing:
    repetition: int
    maps_seconds: float
    postprocess_seconds: float
    end_to_end_seconds: float
    output_sha256: str


def sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def array_sha256(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(value)
    checksum = hashlib.sha256()
    checksum.update(str(contiguous.dtype).encode())
    checksum.update(str(contiguous.shape).encode())
    checksum.update(contiguous.tobytes())
    return checksum.hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("At least one timing is required")
    return float(np.percentile(np.asarray(values, dtype=np.float64), fraction * 100))


def summarize_timings(timings: list[Timing]) -> dict[str, Any]:
    if not timings:
        raise ValueError("At least one timing is required")
    total = [timing.end_to_end_seconds for timing in timings]
    maps = [timing.maps_seconds for timing in timings]
    postprocess = [timing.postprocess_seconds for timing in timings]
    elapsed = sum(total)
    return {
        "repetitions": len(timings),
        "throughput_regions_per_second": len(timings) / elapsed if elapsed else 0.0,
        "end_to_end_seconds": {
            "p50": percentile(total, 0.50),
            "p90": percentile(total, 0.90),
            "p95": percentile(total, 0.95),
            "p99": percentile(total, 0.99),
            "maximum": max(total),
        },
        "maps_seconds": {
            "p50": percentile(maps, 0.50),
            "p95": percentile(maps, 0.95),
        },
        "postprocess_seconds": {
            "p50": percentile(postprocess, 0.50),
            "p95": percentile(postprocess, 0.95),
        },
        "deterministic_output": len({timing.output_sha256 for timing in timings}) == 1,
        "unique_output_hashes": sorted({timing.output_sha256 for timing in timings}),
    }


def synchronize(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elif device.type == "mps":
        torch.mps.synchronize()


def max_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if platform.system() == "Darwin" else value * 1024


def load_topology(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "status",
        "topology_id",
        "device_type",
        "model_sha256",
        "source_commit",
        "configuration_sha256",
        "hardware",
        "software",
    }
    if not isinstance(value, dict) or required - set(value):
        raise ValueError(f"Topology manifest is missing fields: {sorted(required - set(value))}")
    if value["schema_version"] != 1 or value["status"] != "frozen":
        raise ValueError("Topology manifest must use schema 1 and have frozen status")
    if value["device_type"] not in {"cpu", "cuda", "mps"}:
        raise ValueError("Topology device_type must be cpu, cuda, or mps")
    if not isinstance(value["hardware"], dict) or not isinstance(value["software"], dict):
        raise ValueError("Topology hardware and software identities must be objects")
    return value


def load_image(path: Path) -> np.ndarray:
    with Image.open(path) as source:
        source.load()
        return np.asarray(source.convert("RGB"), dtype=np.uint8)


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    topology = load_topology(args.topology_manifest)
    checkpoint_hash = sha256(args.checkpoint)
    if checkpoint_hash != str(topology["model_sha256"]).lower():
        raise ValueError("Checkpoint hash does not match the frozen topology manifest")
    if topology["device_type"] != args.device:
        raise ValueError("Requested device does not match the frozen topology manifest")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise ValueError("Frozen CUDA topology requested but CUDA is unavailable")
    if device.type == "mps" and not torch.backends.mps.is_available():
        raise ValueError("Frozen MPS topology requested but MPS is unavailable")

    image = load_image(args.image)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    load_started = time.perf_counter()
    engine = AttnDistInference.from_checkpoint(
        args.checkpoint,
        device,
        tile_size=args.tile_size,
        overlap=args.overlap,
    )
    synchronize(device)
    model_load_seconds = time.perf_counter() - load_started
    for _ in range(args.warmup):
        engine.predict_full(image, use_tta=args.tta)
    synchronize(device)

    timings: list[Timing] = []
    for repetition in range(args.repetitions):
        synchronize(device)
        started = time.perf_counter()
        maps = engine.predict_maps(image, use_tta=args.tta)
        synchronize(device)
        maps_finished = time.perf_counter()
        instances = postprocess_instances(
            maps["mask"],
            maps["dist_map"],
            engine.postprocess.mask_threshold,
            engine.postprocess.peak_threshold,
            engine.postprocess.min_size,
            engine.postprocess.gaussian_sigma,
            engine.postprocess.peak_window_size,
        )
        synchronize(device)
        finished = time.perf_counter()
        timings.append(
            Timing(
                repetition=repetition,
                maps_seconds=maps_finished - started,
                postprocess_seconds=finished - maps_finished,
                end_to_end_seconds=finished - started,
                output_sha256=array_sha256(instances),
            )
        )

    result = {
        "schema_version": 1,
        "evidence_status": "qualification_output_requires_independent_review",
        "authorized_use": "research_only_unless_separately_approved",
        "study_id": args.study_id,
        "created_at": datetime.now(UTC).isoformat(),
        "topology": topology,
        "topology_manifest_sha256": sha256(args.topology_manifest),
        "checkpoint_sha256": checkpoint_hash,
        "input": {
            "file": args.image.name,
            "sha256": sha256(args.image),
            "shape": list(image.shape),
        },
        "settings": {
            "device": str(device),
            "tile_size": args.tile_size,
            "overlap": args.overlap,
            "tta": args.tta,
            "warmup": args.warmup,
            "repetitions": args.repetitions,
            "torch_threads": torch.get_num_threads(),
        },
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "platform": platform.platform(),
            "model_load_seconds": model_load_seconds,
            "process_peak_rss_bytes": max_rss_bytes(),
            "gpu_peak_memory_bytes": (
                int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None
            ),
        },
        "summary": summarize_timings(timings),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / "raw_timings.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(asdict(timings[0])))
        writer.writeheader()
        writer.writerows(asdict(timing) for timing in timings)
    (args.output / "summary.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark a model bound to an exact frozen CPU/GPU topology"
    )
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("--topology-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda", "mps"), required=True)
    parser.add_argument("--tile-size", type=int, default=256)
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--repetitions", type=int, default=100)
    parser.add_argument("--tta", action="store_true")
    args = parser.parse_args()
    if args.tile_size < 32 or args.overlap < 0 or args.overlap >= args.tile_size:
        parser.error("Tile size/overlap are invalid")
    if args.warmup < 1 or args.repetitions < 2:
        parser.error("At least one warm-up and two measured repetitions are required")
    return args


def main() -> None:
    args = parse_args()
    try:
        result = run_benchmark(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"TOPOLOGY BENCHMARK FAILED: {error}") from error
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
