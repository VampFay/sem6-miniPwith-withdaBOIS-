import io

import numpy as np
import pytest
from PIL import Image

from src.input_validation import ImageInputError, decode_image


def encoded_image(format: str, frames: int = 1) -> bytes:
    images = [
        Image.fromarray(np.full((8, 9, 3), 64 + index, dtype=np.uint8))
        for index in range(frames)
    ]
    stream = io.BytesIO()
    if frames == 1:
        images[0].save(stream, format=format)
    else:
        images[0].save(stream, format=format, save_all=True, append_images=images[1:])
    return stream.getvalue()


def test_decode_image_returns_pixels_and_provenance() -> None:
    decoded = decode_image(encoded_image("PNG"), "image/png", max_pixels=100)

    assert decoded.pixels.shape == (8, 9, 3)
    assert decoded.format == "PNG"
    assert decoded.width == 9
    assert decoded.height == 8
    assert len(decoded.sha256) == 64


def test_decode_image_rejects_declared_format_mismatch() -> None:
    with pytest.raises(ImageInputError, match="does not contain") as captured:
        decode_image(encoded_image("BMP"), "image/png", max_pixels=100)

    assert captured.value.kind == "format_mismatch"


def test_decode_image_rejects_multi_frame_tiff() -> None:
    with pytest.raises(ImageInputError, match="Multi-frame") as captured:
        decode_image(encoded_image("TIFF", frames=2), "image/tiff", max_pixels=100)

    assert captured.value.kind == "multiple_frames"


def test_decode_image_enforces_pixel_limit() -> None:
    with pytest.raises(ImageInputError, match="pixel limit") as captured:
        decode_image(encoded_image("PNG"), "image/png", max_pixels=10)

    assert captured.value.kind == "pixel_limit"


def test_decoder_fails_safely_for_deterministic_malformed_corpus() -> None:
    generator = np.random.default_rng(20260716)
    declared_types = ("image/png", "image/jpeg", "image/tiff")
    for index in range(128):
        size = int(generator.integers(0, 4097))
        content = generator.integers(0, 256, size=size, dtype=np.uint8).tobytes()
        try:
            decoded = decode_image(
                content,
                declared_types[index % len(declared_types)],
                max_pixels=4096,
            )
        except ImageInputError:
            continue
        assert decoded.pixels.shape == (decoded.height, decoded.width, 3)
        assert decoded.width * decoded.height <= 4096
