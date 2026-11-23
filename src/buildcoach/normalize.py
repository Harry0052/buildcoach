"""Decode local image bytes and refuse oversized input before detection."""

from __future__ import annotations

import cv2
import numpy as np

from buildcoach.errors import InputError


def decode_image(data: bytes, limits: dict) -> np.ndarray:
    """Return a uint8 grayscale image or raise InputError."""
    if not isinstance(data, (bytes, bytearray)):
        raise InputError("malformed_input", "Image bytes are missing.")
    size = len(data)
    max_bytes = int(limits["max_bytes"])
    if size > max_bytes:
        raise InputError(
            "oversized_input",
            f"Image is {size} bytes. The limit is {max_bytes} bytes. Submit a smaller file.",
        )
    if size < 32:
        raise InputError("unreadable_image", "The file is too small to be a PNG or JPEG.")
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise InputError(
            "unreadable_image",
            "The file is not a readable PNG or JPEG. Export a still photo and try again.",
        )
    height, width = image.shape[:2]
    max_edge = int(limits["max_edge_px"])
    max_pixels = int(limits["max_pixels"])
    if width > max_edge or height > max_edge or width * height > max_pixels:
        raise InputError(
            "oversized_input",
            (
                f"Image is {width}x{height} pixels. The limit is {max_edge} px on a side "
                f"and {max_pixels} pixels total. The file was not resized, because resizing "
                "could hide a tag."
            ),
        )
    if height < 16 or width < 16:
        raise InputError("unreadable_image", "Image is smaller than 16 pixels on a side.")
    if image.ndim == 2:
        gray = image
    elif image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if gray.dtype != np.uint8:
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return gray
