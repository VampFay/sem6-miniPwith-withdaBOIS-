import pytest

from scripts.load_test import percentile, summarize


def test_load_summary_uses_observed_requests_and_failures() -> None:
    summary = summarize([0.1, 0.2, 0.3, 0.4], failures=1, elapsed=1.0)
    assert summary.requests == 4
    assert summary.error_rate == 0.25
    assert summary.throughput_per_second == 4.0
    assert summary.latency_p50_ms == pytest.approx(200.0)
    assert summary.latency_p90_ms == pytest.approx(400.0)
    assert summary.latency_p95_ms == pytest.approx(400.0)
    assert summary.latency_p99_ms == pytest.approx(400.0)


def test_percentile_handles_no_observations() -> None:
    assert percentile([], 0.95) == 0.0
