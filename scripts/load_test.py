from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx


@dataclass(frozen=True)
class LoadSummary:
    requests: int
    failures: int
    error_rate: float
    elapsed_seconds: float
    throughput_per_second: float
    latency_p50_ms: float
    latency_p90_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_max_ms: float


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(max(math.ceil(fraction * len(ordered)) - 1, 0), len(ordered) - 1)
    return ordered[index]


def summarize(latencies: list[float], failures: int, elapsed: float) -> LoadSummary:
    requests = len(latencies)
    milliseconds = [value * 1000 for value in latencies]
    return LoadSummary(
        requests=requests,
        failures=failures,
        error_rate=failures / requests if requests else 1.0,
        elapsed_seconds=elapsed,
        throughput_per_second=requests / elapsed if elapsed else 0.0,
        latency_p50_ms=percentile(milliseconds, 0.50),
        latency_p90_ms=percentile(milliseconds, 0.90),
        latency_p95_ms=percentile(milliseconds, 0.95),
        latency_p99_ms=percentile(milliseconds, 0.99),
        latency_max_ms=max(milliseconds, default=0.0),
    )


async def run(args: argparse.Namespace) -> LoadSummary:
    content = args.image.read_bytes()
    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }.get(args.image.suffix.lower())
    if content_type is None:
        raise ValueError("Load-test image must be JPEG, PNG, or TIFF.")
    headers: dict[str, str] = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
        headers["X-Actor-ID"] = args.actor_id
    semaphore = asyncio.Semaphore(args.concurrency)
    latencies: list[float] = []
    failures = 0

    async with httpx.AsyncClient(base_url=args.url, timeout=args.timeout) as client:
        async def request(index: int) -> None:
            nonlocal failures
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.post(
                        "/api/analyze",
                        headers=headers,
                        data={"analysis_id": f"LOAD-{index:06d}"},
                        files={"file": (args.image.name, content, content_type)},
                    )
                    if response.status_code != 200:
                        failures += 1
                except httpx.HTTPError:
                    failures += 1
                finally:
                    latencies.append(time.perf_counter() - started)

        started = time.perf_counter()
        await asyncio.gather(*(request(index) for index in range(args.requests)))
        elapsed = time.perf_counter() - started
    return summarize(latencies, failures, elapsed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bounded Attn-Dist-Net API load qualification")
    parser.add_argument("image", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-p95-ms", type=float, required=True)
    parser.add_argument("--max-error-rate", type=float, default=0.0)
    parser.add_argument("--token")
    parser.add_argument("--actor-id", default="load-qualification")
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.timeout <= 0:
        parser.error("requests, concurrency, and timeout must be positive")
    if args.max_p95_ms <= 0 or not 0 <= args.max_error_rate <= 1:
        parser.error("acceptance thresholds are invalid")
    return args


def main() -> None:
    args = parse_args()
    summary = asyncio.run(run(args))
    print(json.dumps(asdict(summary), indent=2))
    if summary.error_rate > args.max_error_rate:
        raise SystemExit("LOAD QUALIFICATION FAILED: error-rate limit exceeded")
    if summary.latency_p95_ms > args.max_p95_ms:
        raise SystemExit("LOAD QUALIFICATION FAILED: p95 latency limit exceeded")


if __name__ == "__main__":
    main()
