from __future__ import annotations

import csv
import io
from dataclasses import dataclass

import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from skimage.color import label2rgb
from skimage.measure import regionprops_table


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
    analysis_id: str,
) -> bytes:
    stream = io.BytesIO()
    with PdfPages(stream) as pdf:
        figure = Figure(figsize=(12, 4))
        axes = figure.subplots(1, 3)
        for axis, content, title in zip(
            axes,
            (image, overlay, mask),
            ("Source", "Detected instances", "Mask probability"),
            strict=True,
        ):
            axis.imshow(content, cmap="gray" if content.ndim == 2 else None)
            axis.set_title(title)
            axis.axis("off")
        figure.suptitle(
            f"Attn-Dist-Net research analysis | {analysis_id} | nuclei: {nucleus_count}"
        )
        figure.text(
            0.5,
            0.01,
            "Research use only. This output is not a medical diagnosis.",
            ha="center",
            fontsize=8,
        )
        figure.tight_layout(rect=(0, 0.04, 1, 0.95))
        pdf.savefig(figure)
    return stream.getvalue()
