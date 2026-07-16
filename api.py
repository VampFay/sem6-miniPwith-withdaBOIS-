from __future__ import annotations

import logging
import os
import re
import secrets
import time
from collections.abc import Awaitable, Callable
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from src.analysis_service import AnalysisOptions, perform_analysis
from src.config import select_device
from src.http_limits import RequestBodyLimitMiddleware
from src.inference import AttnDistInference
from src.input_validation import ImageInputError, decode_image
from src.provenance import AuditStore
from src.runtime import (
    RuntimeConfig,
    RuntimeConfigurationError,
    parse_allowed_origins,
    read_verified_checkpoint,
)

LOGGER = logging.getLogger("attn_dist.api")
ROOT = Path(__file__).resolve().parent
WEB_DIST = ROOT / "web" / "dist"


def read_integer_setting(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as error:
        raise RuntimeConfigurationError(f"{name} must be an integer.") from error
    if value < minimum:
        raise RuntimeConfigurationError(f"{name} must be at least {minimum}.")
    return value


MAX_UPLOAD_BYTES = read_integer_setting(
    "ATTNDIST_MAX_UPLOAD_BYTES", 25 * 1024 * 1024, 1
)
MAX_IMAGE_PIXELS = read_integer_setting("ATTNDIST_MAX_IMAGE_PIXELS", 2048 * 2048, 1)
MAX_MULTIPART_OVERHEAD_BYTES = read_integer_setting(
    "ATTNDIST_MAX_MULTIPART_OVERHEAD_BYTES", 256 * 1024, 0
)
CHECKPOINT_CANDIDATES = (
    Path("outputs_v2/checkpoints/best_iou_calibrated.pt"),
    Path("outputs_v2/checkpoints/best_iou.pt"),
    Path("outputs_v2/checkpoints/best_model.pth"),
)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
ACTOR_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@:-]{0,127}$")

app = FastAPI(
    title="Attn-Dist-Net API",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ATTNDIST_ENABLE_DOCS", "1") == "1" else None,
    redoc_url=None,
)

def maximum_request_bytes() -> int:
    return MAX_UPLOAD_BYTES + MAX_MULTIPART_OVERHEAD_BYTES


app.add_middleware(
    RequestBodyLimitMiddleware,
    limit_getter=maximum_request_bytes,
    paths=frozenset({"/api/analyze"}),
)

allowed_origins = list(parse_allowed_origins(os.getenv("ATTNDIST_ALLOWED_ORIGINS", "")))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=None
    if allowed_origins
    else r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Actor-ID", "X-Request-ID"],
)


@app.middleware("http")
async def secure_and_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    supplied_request_id = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied_request_id
        if REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
        else str(uuid4())
    )
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
def load_engine(path: str, digest: str) -> AttnDistInference:
    content, verified_digest = read_verified_checkpoint(Path(path), digest)
    if verified_digest != digest:
        raise RuntimeConfigurationError("Checkpoint changed while it was being loaded.")
    return AttnDistInference.from_checkpoint_bytes(content, select_device())


def active_engine(config: RuntimeConfig | None = None) -> tuple[Path, str, AttnDistInference]:
    config = config or RuntimeConfig.from_environment()
    checkpoint = checkpoint_path()
    if checkpoint is None:
        raise FileNotFoundError("No inference checkpoint is installed")
    resolved = checkpoint.resolve()
    _, digest = read_verified_checkpoint(resolved, config.approved_checkpoint_sha256)
    return resolved, digest, load_engine(str(resolved), digest)


def runtime_status() -> dict[str, object]:
    device = select_device().type.upper()
    try:
        config = RuntimeConfig.from_environment()
    except RuntimeConfigurationError:
        LOGGER.exception("Runtime configuration validation failed")
        return {
            "status": "configuration_error",
            "ready": False,
            "operating_mode": "invalid",
            "release_id": None,
            "device": device,
            "checkpoint": None,
            "checkpoint_sha256": None,
            "postprocessing": None,
            "detail": "Runtime safeguards are incomplete or invalid.",
        }
    if config.is_controlled and config.audit_dir is not None:
        try:
            AuditStore(config.audit_dir).ensure_ready()
        except (OSError, RuntimeError):
            LOGGER.exception("Controlled audit storage validation failed")
            return {
                "status": "configuration_error",
                "ready": False,
                "operating_mode": config.operating_mode,
                "release_id": config.release_id,
                "device": device,
                "checkpoint": None,
                "checkpoint_sha256": None,
                "postprocessing": None,
                "detail": "Controlled audit storage is unavailable or invalid.",
            }
    checkpoint = checkpoint_path()
    if checkpoint is None:
        return {
            "status": "setup_required",
            "ready": False,
            "operating_mode": config.operating_mode,
            "release_id": config.release_id,
            "device": device,
            "checkpoint": None,
            "checkpoint_sha256": None,
            "postprocessing": None,
            "detail": "No version-2 inference checkpoint is installed.",
        }
    try:
        resolved, digest, engine = active_engine(config)
        return {
            "status": "ready",
            "ready": True,
            "operating_mode": config.operating_mode,
            "release_id": config.release_id,
            "device": device,
            "checkpoint": resolved.name,
            "checkpoint_sha256": digest,
            "postprocessing": engine.postprocess.as_dict(),
            "detail": None,
        }
    except Exception:
        LOGGER.exception("Checkpoint validation failed")
        return {
            "status": "invalid_checkpoint",
            "ready": False,
            "operating_mode": config.operating_mode,
            "release_id": config.release_id,
            "device": device,
            "checkpoint": checkpoint.name,
            "checkpoint_sha256": None,
            "postprocessing": None,
            "detail": "Checkpoint failed schema or model compatibility validation.",
        }


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


def controlled_actor(request: Request, config: RuntimeConfig) -> str | None:
    if not config.is_controlled:
        return None
    authorization = request.headers.get("Authorization", "")
    expected = f"Bearer {config.api_token}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=401,
            detail="Authentication is required for controlled operation.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    actor = request.headers.get("X-Actor-ID", "").strip()
    if not ACTOR_ID_PATTERN.fullmatch(actor):
        raise HTTPException(
            status_code=400,
            detail="A valid X-Actor-ID is required for the audit record.",
        )
    return actor


@app.post("/api/analyze")
def analyze(
    request: Request,
    file: Annotated[UploadFile, File()],
    analysis_id: Annotated[
        str,
        Form(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
    ],
    use_tta: Annotated[bool | None, Form()] = None,
    mask_threshold: Annotated[float | None, Form(ge=0.1, le=0.9)] = None,
    peak_threshold: Annotated[float | None, Form(ge=0.1, le=0.9)] = None,
    min_size: Annotated[int | None, Form(ge=1, le=1000)] = None,
) -> dict[str, object]:
    try:
        config = RuntimeConfig.from_environment()
    except RuntimeConfigurationError as error:
        raise HTTPException(status_code=503, detail="Runtime safeguards are not ready.") from error
    actor = controlled_actor(request, config)
    if config.is_controlled and config.audit_dir is not None:
        try:
            AuditStore(config.audit_dir).ensure_ready()
        except (OSError, RuntimeError) as error:
            raise HTTPException(
                status_code=503, detail="Controlled audit storage is unavailable or invalid."
            ) from error
    try:
        checkpoint, checkpoint_digest, engine = active_engine(config)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except RuntimeConfigurationError as error:
        raise HTTPException(status_code=503, detail="Runtime safeguards are not ready.") from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Installed checkpoint is invalid.") from error
    if config.is_controlled and any(
        value is not None for value in (use_tta, mask_threshold, peak_threshold, min_size)
    ):
        raise HTTPException(
            status_code=422,
            detail="Controlled mode uses locked, approved inference settings.",
        )
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded image is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the upload limit.")
    try:
        decoded = decode_image(content, file.content_type, MAX_IMAGE_PIXELS)
    except ImageInputError as error:
        status_code = 415 if error.kind in {"unsupported_media_type", "format_mismatch"} else 422
        if error.kind == "pixel_limit":
            status_code = 413
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return perform_analysis(
        decoded=decoded,
        engine=engine,
        checkpoint=checkpoint,
        checkpoint_digest=checkpoint_digest,
        config=config,
        analysis_id=analysis_id,
        actor=actor,
        options=AnalysisOptions(
            use_tta=use_tta,
            mask_threshold=mask_threshold,
            peak_threshold=peak_threshold,
            min_size=min_size,
        ),
    )


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
