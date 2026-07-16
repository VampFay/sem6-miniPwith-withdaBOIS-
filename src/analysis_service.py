from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from PIL import Image

from src.inference import AttnDistInference, PostprocessConfig
from src.input_validation import DecodedImage
from src.provenance import AnalysisProvenance, AuditStore
from src.reporting import analysis_pdf, build_artifacts, measurements_csv
from src.runtime import RuntimeConfig, sha256_bytes

INFERENCE_LOCK = Lock()


@dataclass(frozen=True)
class AnalysisOptions:
    use_tta: bool | None = None
    mask_threshold: float | None = None
    peak_threshold: float | None = None
    min_size: int | None = None

    def resolve(self, engine: AttnDistInference) -> tuple[bool, PostprocessConfig]:
        settings = engine.postprocess
        return (
            False if self.use_tta is None else self.use_tta,
            PostprocessConfig(
                mask_threshold=settings.mask_threshold
                if self.mask_threshold is None
                else self.mask_threshold,
                peak_threshold=settings.peak_threshold
                if self.peak_threshold is None
                else self.peak_threshold,
                min_size=settings.min_size if self.min_size is None else self.min_size,
                gaussian_sigma=settings.gaussian_sigma,
                peak_window_size=settings.peak_window_size,
            ),
        )


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


def audit_analysis(
    config: RuntimeConfig,
    actor: str | None,
    provenance: AnalysisProvenance,
    instances: np.ndarray,
    nucleus_count: int,
    csv_content: bytes,
    pdf_content: bytes,
) -> dict[str, int | str | None] | None:
    if config.audit_dir is None:
        return None
    receipt = AuditStore(config.audit_dir).append(
        {
            "event_type": "analysis_completed",
            "actor_id": actor,
            "provenance": provenance.as_dict(),
            "outputs": {
                "csv_sha256": sha256_bytes(csv_content),
                "pdf_sha256": sha256_bytes(pdf_content),
                "instances_sha256": sha256_bytes(instances.tobytes()),
                "nucleus_count": nucleus_count,
            },
        }
    )
    return {
        "sequence": receipt.sequence,
        "record_sha256": receipt.record_sha256,
        "previous_record_sha256": receipt.previous_record_sha256,
    }


def perform_analysis(
    *,
    decoded: DecodedImage,
    engine: AttnDistInference,
    checkpoint: Path,
    checkpoint_digest: str,
    config: RuntimeConfig,
    analysis_id: str,
    actor: str | None,
    options: AnalysisOptions,
) -> dict[str, object]:
    use_tta, postprocessing = options.resolve(engine)
    with INFERENCE_LOCK:
        result = engine.predict_full(
            decoded.pixels,
            use_tta=use_tta,
            mask_threshold=postprocessing.mask_threshold,
            peak_threshold=postprocessing.peak_threshold,
            min_size=postprocessing.min_size,
            gaussian_sigma=postprocessing.gaussian_sigma,
            peak_window_size=postprocessing.peak_window_size,
        )
    artifacts = build_artifacts(decoded.pixels, result["instances"])
    count = len(artifacts.measurements)
    mean_area = (
        float(np.mean([row["area_px"] for row in artifacts.measurements])) if count else 0.0
    )
    settings: dict[str, bool | float | int] = {
        "use_tta": use_tta,
        **postprocessing.as_dict(),
    }
    provenance = AnalysisProvenance.create(
        analysis_id=analysis_id,
        release_id=config.release_id,
        operating_mode=config.operating_mode,
        input_sha256=decoded.sha256,
        input_format=decoded.format,
        input_width=decoded.width,
        input_height=decoded.height,
        checkpoint_name=checkpoint.name,
        checkpoint_sha256=checkpoint_digest,
        runtime_device=engine.device.type.upper(),
        settings=settings,
    )
    csv_content = measurements_csv(artifacts.measurements)
    pdf_content = analysis_pdf(
        decoded.pixels, artifacts.overlay, result["mask"], count, provenance
    )
    audit_receipt = audit_analysis(
        config,
        actor,
        provenance,
        result["instances"],
        count,
        csv_content,
        pdf_content,
    )
    foreground_score = (np.clip(result["mask"], 0, 1) * 255).astype(np.uint8)
    return {
        "analysis_id": analysis_id,
        "provenance": provenance.as_dict(),
        "audit_receipt": audit_receipt,
        "settings": settings,
        "metrics": {
            "nucleus_count": count,
            "mean_area_px": mean_area,
            "mean_tta_disagreement": (
                float(result["tta_disagreement"].mean()) if use_tta else None
            ),
        },
        "images": {
            "overlay": encode_png(artifacts.overlay),
            "foreground_score": encode_png(foreground_score),
            "instances": encode_png(color_map(result["instances"], cv2.COLORMAP_TURBO)),
            "distance": encode_png(color_map(result["dist_map"], cv2.COLORMAP_TURBO)),
            "tta_disagreement": (
                encode_png(color_map(result["tta_disagreement"], cv2.COLORMAP_MAGMA))
                if use_tta
                else None
            ),
        },
        "measurements": artifacts.measurements,
        "downloads": {
            "csv": base64.b64encode(csv_content).decode("ascii"),
            "pdf": base64.b64encode(pdf_content).decode("ascii"),
            "provenance_json": base64.b64encode(provenance.to_json()).decode("ascii"),
        },
    }
