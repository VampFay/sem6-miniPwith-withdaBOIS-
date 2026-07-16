from __future__ import annotations

import csv
import io
from dataclasses import dataclass

import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from skimage.color import label2rgb
from skimage.measure import regionprops_table

from src.provenance import AnalysisProvenance


@dataclass(frozen=True)
class AnalysisArtifacts:
    overlay: np.ndarray
    measurements: list[dict[str, float | int]]


def build_artifacts(image: np.ndarray, instances: np.ndarray) -> AnalysisArtifacts:
    overlay = (label2rgb(instances, image=image, alpha=0.45, bg_label=0) * 255).astype(np.uint8)
    table = regionprops_table(
        instances,
        properties=("label", "area", "perimeter", "eccentricity", "centroid"),
    )
    measurements = [
        {
            "instance_id": int(table["label"][index]),
            "area_px": int(table["area"][index]),
            "perimeter_px": float(table["perimeter"][index]),
            "eccentricity": float(table["eccentricity"][index]),
            "centroid_y": float(table["centroid-0"][index]),
            "centroid_x": float(table["centroid-1"][index]),
        }
        for index in range(len(table["label"]))
    ]
    return AnalysisArtifacts(overlay, measurements)


def measurements_csv(rows: list[dict[str, float | int]]) -> bytes:
    stream = io.StringIO()
    fieldnames = list(rows[0]) if rows else ["instance_id", "area_px", "perimeter_px"]
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def analysis_pdf(
    image: np.ndarray,
    overlay: np.ndarray,
    mask: np.ndarray,
    nucleus_count: int,
    provenance: AnalysisProvenance,
) -> bytes:
    stream = io.BytesIO()
    with PdfPages(stream) as pdf:
        figure = Figure(figsize=(12, 4))
        axes = figure.subplots(1, 3)
        for axis, content, title in zip(
            axes,
            (image, overlay, mask),
            ("Source", "Detected instances", "Foreground score"),
            strict=True,
        ):
            axis.imshow(content, cmap="gray" if content.ndim == 2 else None)
            axis.set_title(title)
            axis.axis("off")
        figure.suptitle(
            "Attn-Dist-Net analysis | "
            f"{provenance.analysis_id} | nuclei: {nucleus_count}"
        )
        figure.text(
            0.5,
            0.01,
            "Not cleared for diagnosis or patient-management decisions.",
            ha="center",
            fontsize=8,
        )
        figure.tight_layout(rect=(0, 0.04, 1, 0.95))
        pdf.savefig(figure)
        details = Figure(figsize=(8.5, 11))
        details.text(0.08, 0.94, "Analysis provenance", fontsize=18, weight="bold")
        lines = (
            ("Analysis UUID", provenance.analysis_uuid),
            ("Analysis ID", provenance.analysis_id),
            ("Created (UTC)", provenance.created_at_utc),
            ("Operating mode", provenance.operating_mode),
            ("Release ID", provenance.release_id),
            ("Software version", provenance.software_version),
            ("Input format", provenance.input_format),
            ("Input dimensions", f"{provenance.input_width} x {provenance.input_height}"),
            ("Input SHA-256", provenance.input_sha256),
            ("Checkpoint", provenance.checkpoint_name),
            ("Checkpoint SHA-256", provenance.checkpoint_sha256),
            ("Runtime device", provenance.runtime_device),
        )
        y = 0.89
        for label, value in lines:
            details.text(0.08, y, f"{label}:", fontsize=9, weight="bold")
            details.text(0.28, y, value, fontsize=9, family="monospace")
            y -= 0.045
        details.text(0.08, y - 0.01, "Locked analysis settings", fontsize=11, weight="bold")
        y -= 0.055
        for key, setting_value in provenance.settings.items():
            details.text(0.1, y, f"{key}: {setting_value}", fontsize=9, family="monospace")
            y -= 0.035
        details.text(
            0.08,
            0.08,
            "Verify the full SHA-256 values against the provenance JSON and controlled audit log.",
            fontsize=8,
        )
        details.text(
            0.08,
            0.05,
            "Not cleared for diagnosis or patient-management decisions.",
            fontsize=8,
            weight="bold",
        )
        pdf.savefig(details)
    return stream.getvalue()
