import hashlib
import io
from pathlib import Path

import anyio
import httpx
import numpy as np
import pytest
import torch
from PIL import Image

import api
from api import app
from src.inference import PostprocessConfig


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
    assert payload["status"] in {
        "ready",
        "setup_required",
        "invalid_checkpoint",
        "configuration_error",
    }
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


class FakeEngine:
    postprocess = PostprocessConfig()
    device = torch.device("cpu")

    def predict_full(self, image: np.ndarray, **kwargs: object) -> dict[str, np.ndarray]:
        del kwargs
        height, width = image.shape[:2]
        mask = np.zeros((height, width), dtype=np.float32)
        mask[2:6, 2:6] = 0.9
        instances = np.zeros((height, width), dtype=np.int32)
        instances[2:6, 2:6] = 1
        return {
            "mask": mask,
            "dist_map": mask,
            "tta_disagreement": np.zeros_like(mask),
            "instances": instances,
        }


def png_image() -> bytes:
    stream = io.BytesIO()
    Image.fromarray(np.full((8, 8, 3), 128, dtype=np.uint8)).save(stream, format="PNG")
    return stream.getvalue()


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


def test_analysis_returns_verifiable_provenance(monkeypatch) -> None:
    content = png_image()
    monkeypatch.setattr(
        api,
        "active_engine",
        lambda config=None: (Path("model.pt"), "b" * 64, FakeEngine()),
    )
    response = request(
        "POST",
        "/api/analyze",
        data={"analysis_id": "ANALYSIS-TEST"},
        files={"file": ("sample.png", content, "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["input_sha256"] == hashlib.sha256(content).hexdigest()
    assert payload["provenance"]["checkpoint_sha256"] == "b" * 64
    assert payload["metrics"]["mean_tta_disagreement"] is None
    assert payload["images"]["tta_disagreement"] is None
    assert payload["downloads"]["provenance_json"]


def test_controlled_mode_requires_authentication(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ATTNDIST_OPERATING_MODE", "controlled")
    monkeypatch.setenv("ATTNDIST_RELEASE_ID", "release-1")
    monkeypatch.setenv("ATTNDIST_APPROVED_CHECKPOINT_SHA256", "b" * 64)
    monkeypatch.setenv("ATTNDIST_AUDIT_DIR", str(tmp_path))
    monkeypatch.setenv("ATTNDIST_API_TOKEN", "s" * 32)
    monkeypatch.setenv("ATTNDIST_ALLOWED_ORIGINS", "https://lab.example")
    response = request(
        "POST",
        "/api/analyze",
        data={"analysis_id": "ANALYSIS-TEST"},
        files={"file": ("sample.png", png_image(), "image/png")},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_controlled_mode_rejects_setting_overrides(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ATTNDIST_OPERATING_MODE", "controlled")
    monkeypatch.setenv("ATTNDIST_RELEASE_ID", "release-1")
    monkeypatch.setenv("ATTNDIST_APPROVED_CHECKPOINT_SHA256", "b" * 64)
    monkeypatch.setenv("ATTNDIST_AUDIT_DIR", str(tmp_path))
    monkeypatch.setenv("ATTNDIST_API_TOKEN", "s" * 32)
    monkeypatch.setenv("ATTNDIST_ALLOWED_ORIGINS", "https://lab.example")
    monkeypatch.setattr(
        api,
        "active_engine",
        lambda config=None: (Path("model.pt"), "b" * 64, FakeEngine()),
    )
    response = request(
        "POST",
        "/api/analyze",
        headers={"Authorization": f"Bearer {'s' * 32}", "X-Actor-ID": "laboratory-user"},
        data={"analysis_id": "ANALYSIS-TEST", "use_tta": "true"},
        files={"file": ("sample.png", png_image(), "image/png")},
    )
    assert response.status_code == 422
    assert "locked" in response.json()["detail"].lower()


def test_controlled_analysis_writes_auditable_record(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ATTNDIST_OPERATING_MODE", "controlled")
    monkeypatch.setenv("ATTNDIST_RELEASE_ID", "release-1")
    monkeypatch.setenv("ATTNDIST_APPROVED_CHECKPOINT_SHA256", "b" * 64)
    monkeypatch.setenv("ATTNDIST_AUDIT_DIR", str(tmp_path))
    monkeypatch.setenv("ATTNDIST_API_TOKEN", "s" * 32)
    monkeypatch.setenv("ATTNDIST_ALLOWED_ORIGINS", "https://lab.example")
    monkeypatch.setattr(
        api,
        "active_engine",
        lambda config=None: (Path("model.pt"), "b" * 64, FakeEngine()),
    )
    response = request(
        "POST",
        "/api/analyze",
        headers={"Authorization": f"Bearer {'s' * 32}", "X-Actor-ID": "laboratory-user"},
        data={"analysis_id": "ANALYSIS-TEST"},
        files={"file": ("sample.png", png_image(), "image/png")},
    )
    assert response.status_code == 200
    receipt = response.json()["audit_receipt"]
    assert receipt["sequence"] == 1
    assert receipt["record_sha256"]
    assert receipt["previous_record_sha256"] is None
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_api_rejects_declared_format_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "active_engine",
        lambda config=None: (Path("model.pt"), "b" * 64, FakeEngine()),
    )
    stream = io.BytesIO()
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(stream, format="BMP")
    response = request(
        "POST",
        "/api/analyze",
        data={"analysis_id": "ANALYSIS-TEST"},
        files={"file": ("sample.png", stream.getvalue(), "image/png")},
    )
    assert response.status_code == 415


def test_api_rejects_oversized_upload_before_decode(monkeypatch) -> None:
    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 8)
    monkeypatch.setattr(
        api,
        "active_engine",
        lambda config=None: (Path("model.pt"), "b" * 64, FakeEngine()),
    )
    response = request(
        "POST",
        "/api/analyze",
        data={"analysis_id": "ANALYSIS-TEST"},
        files={"file": ("sample.png", b"x" * 9, "image/png")},
    )
    assert response.status_code == 413


def test_api_rejects_oversized_content_length_before_multipart_parse(monkeypatch) -> None:
    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 8)
    monkeypatch.setattr(api, "MAX_MULTIPART_OVERHEAD_BYTES", 0)
    response = request(
        "POST",
        "/api/analyze",
        content=b"x" * 9,
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request exceeds the upload limit."}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_api_counts_streamed_body_without_content_length(monkeypatch) -> None:
    boundary = "attndist-boundary"
    multipart = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="analysis_id"\r\n\r\n'
        "ANALYSIS-TEST\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="sample.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + b"x" * 16 + f"\r\n--{boundary}--\r\n".encode()

    async def chunks():
        for offset in range(0, len(multipart), 5):
            yield multipart[offset : offset + 5]

    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 8)
    monkeypatch.setattr(api, "MAX_MULTIPART_OVERHEAD_BYTES", 0)
    response = request(
        "POST",
        "/api/analyze",
        content=chunks(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request exceeds the upload limit."}


def test_api_rejects_unsafe_analysis_identifier(monkeypatch) -> None:
    response = request(
        "POST",
        "/api/analyze",
        data={"analysis_id": "patient name"},
        files={"file": ("sample.png", png_image(), "image/png")},
    )
    assert response.status_code == 422


def test_api_size_settings_fail_closed(monkeypatch) -> None:
    monkeypatch.setenv("ATTNDIST_TEST_LIMIT", "not-an-integer")
    with pytest.raises(api.RuntimeConfigurationError, match="must be an integer"):
        api.read_integer_setting("ATTNDIST_TEST_LIMIT", 10, 1)

    monkeypatch.setenv("ATTNDIST_TEST_LIMIT", "0")
    with pytest.raises(api.RuntimeConfigurationError, match="at least 1"):
        api.read_integer_setting("ATTNDIST_TEST_LIMIT", 10, 1)
