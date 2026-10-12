"""JPEG encoding for browser previews."""

from __future__ import annotations

import cv2
import numpy as np

JPEG_QUALITY = 75


def encode_jpeg(frame: np.ndarray, max_width: int) -> bytes:
    """Downscale to `max_width` and encode.

    Source frames can be 4K; sending them to a browser tile wastes bandwidth
    that the dashboard has no use for.
    """
    scaled = _downscale(frame, max_width)
    ok, buffer = cv2.imencode(".jpg", scaled, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return buffer.tobytes()


def _downscale(frame: np.ndarray, max_width: int) -> np.ndarray:
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame
    scale = max_width / width
    return cv2.resize(frame, (max_width, round(height * scale)), interpolation=cv2.INTER_AREA)
