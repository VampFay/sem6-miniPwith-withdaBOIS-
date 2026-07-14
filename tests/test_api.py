import anyio
import httpx

import api
from api import app


def request(method: str, path: str, **kwargs) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return anyio.run(send)


def test_health_exposes_runtime_without_private_paths() -> None:
    response = request("GET", "/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "setup_required", "invalid_checkpoint"}
    assert isinstance(payload["ready"], bool)
    assert payload["device"] in {"CPU", "CUDA", "MPS"}
    assert not payload.get("checkpoint") or "/" not in payload["checkpoint"]
    assert payload["postprocessing"] is None or set(payload["postprocessing"]) == {
        "mask_threshold",
        "peak_threshold",
        "min_size",
        "gaussian_sigma",
        "peak_window_size",
    }
    assert response.headers["cache-control"] == "no-store"


def test_readiness_fails_without_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr(api, "checkpoint_path", lambda: None)
    response = request("GET", "/api/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "setup_required"


def test_analyze_reports_missing_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr(api, "checkpoint_path", lambda: None)
    response = request(
        "POST",
        "/api/analyze",
        data={"analysis_id": "ANALYSIS-TEST"},
        files={"file": ("sample.png", b"not-read-without-model", "image/png")},
    )
    assert response.status_code == 503
    assert "checkpoint" in response.json()["detail"].lower()
