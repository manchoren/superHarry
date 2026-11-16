"""Dependency-free, bounded image ingress checks.

This is deliberately not an image decoder.  It validates enough of the
container header to reject mismatched/truncated inputs and dangerous canvas
sizes before any future decoder or OCR process is allowed to see the file.
"""
import struct
from pathlib import Path


class ImageValidationError(ValueError):
    pass


MAX_IMAGE_PIXELS = 25_000_000
MAX_DIMENSION = 10_000
MAX_EXPANSION_RATIO = 1_000


def _dimensions(width, height, source_size):
    if not (width > 0 and height > 0 and width <= MAX_DIMENSION and height <= MAX_DIMENSION):
        raise ImageValidationError("Image dimensions are unsafe.")
    pixels = width * height
    if pixels > MAX_IMAGE_PIXELS or pixels > source_size * MAX_EXPANSION_RATIO:
        raise ImageValidationError("Image decompression budget exceeded.")
    return {"width": width, "height": height, "pixels": pixels}


def _jpeg(data, source_size):
    if not data.startswith(b"\xff\xd8\xff"):
        raise ImageValidationError("Image signature is invalid.")
    pos = 2
    while pos < len(data):
        while pos < len(data) and data[pos] != 0xFF:
            pos += 1
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            break
        marker = data[pos]
        pos += 1
        if marker in (0xD8, 0xD9):
            continue
        if marker == 0xDA:
            raise ImageValidationError("JPEG metadata or dimensions are truncated.")
        if pos + 2 > len(data):
            raise ImageValidationError("JPEG segment is truncated.")
        length = struct.unpack_from(">H", data, pos)[0]
        if length < 2 or pos + length > len(data):
            raise ImageValidationError("JPEG segment is invalid.")
        segment = data[pos + 2:pos + length]
        if marker == 0xE1 and segment.startswith(b"Exif\x00\x00"):
            raise ImageValidationError("JPEG EXIF metadata is not allowed.")
        if marker in range(0xC0, 0xC4) or marker in range(0xC5, 0xC8) or marker in range(0xC9, 0xCC) or marker in range(0xCD, 0xD0):
            if len(segment) < 5:
                raise ImageValidationError("JPEG frame header is truncated.")
            height, width = struct.unpack_from(">HH", segment, 1)
            return _dimensions(width, height, source_size)
        pos += length
    raise ImageValidationError("JPEG dimensions are missing.")


def validate_image_bytes(data):
    """Validate a synthetic/in-memory bounded image payload without decoding it."""
    if not isinstance(data, bytes) or len(data) < 12:
        raise ImageValidationError("Image is too short.")
    size = len(data)
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if data[12:16] != b"IHDR" or len(data) < 33:
            raise ImageValidationError("PNG header is invalid.")
        width, height = struct.unpack_from(">II", data, 16)
        if b"eXIf" in data:
            raise ImageValidationError("PNG EXIF metadata is not allowed.")
        return {"format": "png", **_dimensions(width, height, size)}
    if data.startswith((b"GIF87a", b"GIF89a")):
        width, height = struct.unpack_from("<HH", data, 6)
        return {"format": "gif", **_dimensions(width, height, size)}
    if data.startswith(b"\xff\xd8\xff"):
        return {"format": "jpeg", **_jpeg(data, size)}
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        if data[12:16] == b"VP8X" and len(data) >= 30:
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            if b"EXIF" in data:
                raise ImageValidationError("WebP EXIF metadata is not allowed.")
            return {"format": "webp", **_dimensions(width, height, size)}
        raise ImageValidationError("WebP dimensions are unavailable.")
    raise ImageValidationError("Image signature is unsupported.")


def validate_image_file(path, *, content_type, size):
    if content_type not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        return None
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ImageValidationError("Image size is invalid.")
    with Path(path).open("rb") as source:
        data = source.read(size)
        if len(data) != size or source.read(1):
            raise ImageValidationError("Image size does not match the stored file.")
    # The application upload limit bounds this read; inspect the complete stored
    # payload so metadata after the header window cannot evade the policy.
    result = validate_image_bytes(data)
    if result["pixels"] > size * MAX_EXPANSION_RATIO:
        raise ImageValidationError("Image decompression budget exceeded.")
    return result
