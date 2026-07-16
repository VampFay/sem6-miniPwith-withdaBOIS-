from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter, label, maximum_filter
from skimage.segmentation import watershed


@dataclass(frozen=True)
class PostprocessConfig:
    mask_threshold: float = 0.5
    peak_threshold: float = 0.35
    min_size: int = 10
    gaussian_sigma: float = 1.0
    peak_window_size: int = 7

    def __post_init__(self) -> None:
        if not 0 < self.mask_threshold < 1 or not 0 < self.peak_threshold < 1:
            raise ValueError("Mask and peak thresholds must be in the interval (0, 1)")
        if self.min_size < 1:
            raise ValueError("Minimum instance size must be positive")
        if self.gaussian_sigma < 0:
            raise ValueError("Gaussian sigma must be non-negative")
        if self.peak_window_size < 1 or self.peak_window_size % 2 == 0:
            raise ValueError("Peak window size must be a positive odd integer")

    def as_dict(self) -> dict[str, float | int]:
        return {
            "mask_threshold": self.mask_threshold,
            "peak_threshold": self.peak_threshold,
            "min_size": self.min_size,
            "gaussian_sigma": self.gaussian_sigma,
            "peak_window_size": self.peak_window_size,
        }


def _validate_maps(
    mask_probability: np.ndarray, distance_map: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    mask = np.asarray(mask_probability)
    distance = np.asarray(distance_map)
    if mask.ndim != 2 or distance.ndim != 2 or mask.shape != distance.shape:
        raise ValueError("Mask probability and distance map must be same-shaped 2D arrays")
    if not np.isfinite(mask).all() or not np.isfinite(distance).all():
        raise ValueError("Postprocessing inputs must contain only finite values")
    return mask, distance


def _remove_small_components(foreground: np.ndarray, min_size: int) -> np.ndarray:
    components, _ = label(foreground)
    component_sizes = np.bincount(components.ravel())
    return np.asarray(foreground & (component_sizes[components] >= min_size), dtype=bool)


def _markers_for_every_component(
    foreground: np.ndarray,
    smooth_distance: np.ndarray,
    peak_threshold: float,
    peak_window_size: int,
) -> np.ndarray:
    components, component_count = label(foreground)
    peaks = (
        (smooth_distance == maximum_filter(smooth_distance, size=peak_window_size))
        & (smooth_distance >= peak_threshold)
        & foreground
    )
    markers, marker_count = label(peaks)

    # A global fallback is unsafe: if one component has a qualifying peak, every
    # disconnected component without one would otherwise be omitted by watershed.
    for component_id in range(1, component_count + 1):
        component = components == component_id
        if np.any(markers[component]):
            continue
        marker_count += 1
        candidate = np.where(component, smooth_distance, -np.inf)
        markers.flat[int(np.argmax(candidate))] = marker_count
    return np.asarray(markers, dtype=np.int32)


def postprocess_instances(
    mask_probability: np.ndarray,
    distance_map: np.ndarray,
    mask_threshold: float = 0.5,
    peak_threshold: float = 0.35,
    min_size: int = 10,
    gaussian_sigma: float = 1.0,
    peak_window_size: int = 7,
) -> np.ndarray:
    settings = PostprocessConfig(
        mask_threshold,
        peak_threshold,
        min_size,
        gaussian_sigma,
        peak_window_size,
    )
    mask, distance = _validate_maps(mask_probability, distance_map)
    foreground = _remove_small_components(mask >= settings.mask_threshold, settings.min_size)
    if not foreground.any():
        return np.zeros(foreground.shape, dtype=np.int32)

    smooth_distance = gaussian_filter(
        distance.astype(np.float32), sigma=settings.gaussian_sigma
    )
    markers = _markers_for_every_component(
        foreground,
        smooth_distance,
        settings.peak_threshold,
        settings.peak_window_size,
    )
    instances = watershed(-smooth_distance, markers, mask=foreground)
    return np.asarray(instances, dtype=np.int32)
