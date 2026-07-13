from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt


def merge_instance_channels(mask: np.ndarray) -> np.ndarray:
    """Convert PanNuke's five class-specific ID channels to one global instance map."""
    if mask.ndim != 3 or mask.shape[-1] < 5:
        raise ValueError("PanNuke masks must have shape [H, W, >=5]")
    output = np.zeros(mask.shape[:2], dtype=np.uint16)
    next_id = 1
    for channel_index in range(5):
        channel = mask[..., channel_index]
        occupied = channel > 0
        if np.any(occupied & (output > 0)):
            raise ValueError("PanNuke class channels overlap within a patch")
        for source_id in np.unique(channel[occupied]):
            if next_id > np.iinfo(np.uint16).max:
                raise OverflowError("Patch contains too many nuclei for uint16 instance IDs")
            output[channel == source_id] = next_id
            next_id += 1
    return output


def instance_distance_map(instance_mask: np.ndarray) -> np.ndarray:
    if instance_mask.ndim != 2:
        raise ValueError("Instance masks must have shape [H, W]")
    output = np.zeros(instance_mask.shape, dtype=np.float32)
    for instance_id in np.unique(instance_mask):
        if instance_id == 0:
            continue
        distance = distance_transform_edt(instance_mask == instance_id)
        maximum = distance.max()
        if maximum > 0:
            output = np.maximum(output, distance / maximum)
    return output.astype(np.float32)
