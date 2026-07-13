from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import time
import warnings
from collections.abc import Awaitable, Callable
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Annotated
from uuid import uuid4

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from src.config import select_device
from src.inference import AttnDistInference
from src.reporting import analysis_pdf, build_artifacts, measurements_csv

LOGGER = logging.getLogger("attn_dist.api")
ROOT = Path(__file__).resolve().parent
WEB_DIST = ROOT / "web" / "dist"
MAX_UPLOAD_BYTES = int(os.getenv("ATTNDIST_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
MAX_IMAGE_PIXELS = int(os.getenv("ATTNDIST_MAX_IMAGE_PIXELS", str(2048 * 2048)))
CHECKPOINT_CANDIDATES = (
    Path("outputs_v2/checkpoints/best_iou.pt"),
    Path("outputs_v2/checkpoints/best_model.pth"),
)
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/tiff"}
INFERENCE_LOCK = Lock()

app = FastAPI(
    title="Attn-Dist-Net API",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ATTNDIST_ENABLE_DOCS", "1") == "1" else None,
    redoc_url=None,
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ATTNDIST_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=None
    if allowed_origins
    else r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def secure_and_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid4()))[:128]
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    LOGGER.info(
        "request_id=%s method=%s path=%s status=%d duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


def checkpoint_path() -> Path | None:
    configured = os.getenv("ATTNDIST_CHECKPOINT")
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_file() else None
    return next((path for path in CHECKPOINT_CANDIDATES if path.is_file()), None)


@lru_cache(maxsize=2)
def load_engine(path: str, modified_ns: int) -> AttnDistInference:
    del modified_ns
    return AttnDistInference.from_checkpoint(path, select_device())


@lru_cache(maxsize=2)
def checkpoint_sha256(path: str, modified_ns: int) -> str:
    del modified_ns
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def active_engine() -> tuple[Path, AttnDistInference]:
    checkpoint = checkpoint_path()
    if checkpoint is None:
        raise FileNotFoundError("No inference checkpoint is installed")
    resolved = checkpoint.resolve()
    modified_ns = resolved.stat().st_mtime_ns
    return resolved, load_engine(str(resolved), modified_ns)


def runtime_status() -> dict[str, object]:
    device = select_device().type.upper()
    checkpoint = checkpoint_path()
    if checkpoint is None:
        return {
            "status": "setup_required",
            "ready": False,
            "device": device,
            "checkpoint": None,
            "checkpoint_sha256": None,
            "detail": "No version-2 inference checkpoint is installed.",
        }
    try:
        resolved, _ = active_engine()
        modified_ns = resolved.stat().st_mtime_ns
        return {
            "status": "ready",
            "ready": True,
            "device": device,
            "checkpoint": resolved.name,
            "checkpoint_sha256": checkpoint_sha256(str(resolved), modified_ns),
            "detail": None,
        }
    except Exception:
        LOGGER.exception("Checkpoint validation failed")
        return {
            "status": "invalid_checkpoint",
            "ready": False,
            "device": device,
            "checkpoint": checkpoint.name,
            "checkpoint_sha256": None,
            "detail": "Checkpoint failed schema or model compatibility validation.",
        }


def encode_png(image: np.ndarray) -> str:
    array = np.asarray(image)
    if array.dtype != np.uint8:
        array = np.clip(array, 0, 255).astype(np.uint8)
    stream = io.BytesIO()
    Image.fromarray(array).save(stream, format="PNG")
    return base64.b64encode(stream.getvalue()).decode("ascii")


def color_map(values: np.ndarray, palette: int) -> np.ndarray:
    finite = np.nan_to_num(values.astype(np.float32), copy=False)
    minimum = float(finite.min())
    span = float(finite.max()) - minimum
    normalized = ((finite - minimum) * (255.0 / span)).astype(np.uint8) if span else np.zeros(
        finite.shape, dtype=np.uint8
    )
    colored = cv2.applyColorMap(normalized, palette)
    return np.asarray(cv2.cvtColor(colored, cv2.COLOR_BGR2RGB))


@app.get("/api/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/api/health")
def health() -> dict[str, object]:
    return runtime_status()


@app.get("/api/ready")
def ready() -> Response:
    status = runtime_status()
    return JSONResponse(status_code=200 if status["ready"] else 503, content=status)


@app.post("/api/analyze")
def analyze(
    file: Annotated[UploadFile, File()],
    analysis_id: Annotated[str, Form(min_length=1, max_length=64, pattern=r".*\S.*")],
    use_tta: Annotated[bool, Form()] = True,
    mask_threshold: Annotated[float, Form(ge=0.1, le=0.9)] = 0.5,
    peak_threshold: Annotated[float, Form(ge=0.1, le=0.9)] = 0.35,
    min_size: Annotated[int, Form(ge=1, le=1000)] = 10,
) -> dict[str, object]:
    try:
        _, engine = active_engine()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Installed checkpoint is invalid.") from error
    if file.content_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, or TIFF image.")
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded image is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the upload limit.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            source = Image.open(io.BytesIO(content))
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="Image exceeds the pixel limit.")
            image = np.asarray(source.convert("RGB"))
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise HTTPException(status_code=413, detail="Image exceeds the pixel limit.") from error
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(
            status_code=422, detail="Uploaded file is not a valid image."
        ) from error

    with INFERENCE_LOCK:
        result = engine.predict_full(
            image,
            use_tta=use_tta,
            mask_threshold=mask_threshold,
            peak_threshold=peak_threshold,
            min_size=min_size,
        )
    artifacts = build_artifacts(image, result["instances"])
    count = len(artifacts.measurements)
    mean_area = (
        float(np.mean([row["area_px"] for row in artifacts.measurements])) if count else 0.0
    )
    probability = (np.clip(result["mask"], 0, 1) * 255).astype(np.uint8)
    return {
        "analysis_id": analysis_id,
        "metrics": {
            "nucleus_count": count,
            "mean_area_px": mean_area,
            "mean_uncertainty": float(result["uncertainty"].mean()),
        },
        "images": {
            "overlay": encode_png(artifacts.overlay),
            "probability": encode_png(probability),
            "instances": encode_png(color_map(result["instances"], cv2.COLORMAP_TURBO)),
            "distance": encode_png(color_map(result["dist_map"], cv2.COLORMAP_TURBO)),
            "uncertainty": encode_png(color_map(result["uncertainty"], cv2.COLORMAP_MAGMA)),
        },
        "measurements": artifacts.measurements,
        "downloads": {
            "csv": base64.b64encode(measurements_csv(artifacts.measurements)).decode("ascii"),
            "pdf": base64.b64encode(
                analysis_pdf(image, artifacts.overlay, result["mask"], count, analysis_id)
            ).decode("ascii"),
        },
    }


if (WEB_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def web_app(path: str) -> FileResponse:
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found.")
    index = WEB_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Web build is not installed.")
    return FileResponse(index)
