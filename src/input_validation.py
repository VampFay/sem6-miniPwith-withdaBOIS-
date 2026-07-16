from __future__ import annotations

import hashlib
import io
import warnings
from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image, UnidentifiedImageError

SUPPORTED_IMAGE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/tiff": "TIFF",
}

ImageInputErrorKind = Literal[
    "unsupported_media_type",
    "format_mismatch",
    "invalid_image",
    "pixel_limit",
    "multiple_frames",
]


class ImageInputError(ValueError):
    def __init__(self, kind: ImageInputErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class DecodedImage:
    pixels: np.ndarray
    format: str
    width: int
    height: int
    sha256: str


def decode_image(content: bytes, declared_type: str | None, max_pixels: int) -> DecodedImage:
    expected_format = SUPPORTED_IMAGE_FORMATS.get(declared_type or "")
    if expected_format is None:
        raise ImageInputError(
            "unsupported_media_type", "Upload a PNG, JPEG, or single-frame TIFF image."
        )
    if max_pixels < 1:
        raise ValueError("max_pixels must be positive")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                actual_format = source.format
                if actual_format != expected_format:
                    raise ImageInputError(
                        "format_mismatch",
                        (
                            f"Declared {expected_format} content does not contain "
                            f"a {expected_format} image."
                        ),
                    )
                width, height = source.size
                if width < 1 or height < 1 or width * height > max_pixels:
                    raise ImageInputError("pixel_limit", "Image exceeds the permitted pixel limit.")
                if getattr(source, "n_frames", 1) != 1:
                    raise ImageInputError(
                        "multiple_frames",
                        "Multi-frame and whole-slide TIFF files are not supported.",
                    )
                source.load()
                pixels = np.asarray(source.convert("RGB"), dtype=np.uint8)
    except ImageInputError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ImageInputError("pixel_limit", "Image exceeds the permitted pixel limit.") from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise ImageInputError("invalid_image", "Uploaded file is not a valid image.") from error

    if pixels.shape != (height, width, 3):
        raise ImageInputError(
            "invalid_image", "Decoded image does not have the expected RGB shape."
        )
    return DecodedImage(
        pixels=np.ascontiguousarray(pixels),
        format=actual_format,
        width=width,
        height=height,
        sha256=hashlib.sha256(content).hexdigest(),
    )
