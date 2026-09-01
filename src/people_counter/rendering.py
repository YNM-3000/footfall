"""Frame annotation: boxes, track IDs, the counting line, and the HUD.

All drawing is isolated here so the pipeline stays about counting, and so
overlay tweaks never risk touching detection or tracking logic.
"""

from __future__ import annotations

from collections.abc import Iterable

import cv2
import numpy as np

from .counting import Counts
from .detection import TrackedPerson
from .geometry import Line

BOX_COLOR = (0, 255, 0)
LINE_COLOR = (0, 0, 255)
HUD_COLOR = (255, 255, 255)
HUD_OUTLINE_COLOR = (0, 0, 0)
FONT = cv2.FONT_HERSHEY_SIMPLEX

# Annotation sizes are expressed relative to frame width so 720p and 4K
# footage both come out legible.
REFERENCE_WIDTH = 1280
MIN_SCALE = 0.6
MAX_SCALE = 4.0
ID_FONT_SCALE = 0.5
HUD_ORIGIN = (20, 40)
ID_LABEL_OFFSET_Y = -8
# The HUD is sized to occupy this fraction of the frame width, so the readout
# stays legible on 4K footage without running off the edge.
HUD_WIDTH_FRACTION = 0.55
BASE_THICKNESS = 2


def _scale_for(frame: np.ndarray) -> float:
    width = frame.shape[1]
    return max(MIN_SCALE, min(MAX_SCALE, width / REFERENCE_WIDTH))


def annotate(
    frame: np.ndarray,
    *,
    people: Iterable[TrackedPerson],
    line: Line,
    counts: Counts,
) -> np.ndarray:
    """Draw the full overlay onto `frame` and return it.

    The frame is annotated in place — OpenCV frames are large buffers and
    copying every one of them is a needless per-frame allocation.
    """
    scale = _scale_for(frame)
    thickness = max(1, round(BASE_THICKNESS * scale))

    for person in people:
        _draw_person(frame, person, scale=scale, thickness=thickness)

    p1, p2 = line.int_endpoints
    cv2.line(frame, p1, p2, LINE_COLOR, thickness)
    _draw_hud(frame, counts, scale=scale, thickness=thickness)
    return frame


def _draw_person(frame: np.ndarray, person: TrackedPerson, *, scale: float, thickness: int) -> None:
    cv2.rectangle(frame, person.box.top_left, person.box.bottom_right, BOX_COLOR, thickness)
    label_x, label_y = person.box.top_left
    cv2.putText(
        frame,
        f"ID {person.track_id}",
        (label_x, label_y + int(ID_LABEL_OFFSET_Y * scale)),
        FONT,
        ID_FONT_SCALE * scale,
        BOX_COLOR,
        thickness,
    )


def _draw_hud(frame: np.ndarray, counts: Counts, *, scale: float, thickness: int) -> None:
    text = f"IN: {counts.entries}  OUT: {counts.exits}  NET (current): {counts.net}"
    font_scale = _hud_font_scale(text, frame_width=frame.shape[1])
    origin = (int(HUD_ORIGIN[0] * scale), int(HUD_ORIGIN[1] * scale + _text_height(text, font_scale)))
    # Drawn twice: a thick light pass for contrast, a thin dark pass on top.
    cv2.putText(frame, text, origin, FONT, font_scale, HUD_COLOR, thickness + 2)
    cv2.putText(frame, text, origin, FONT, font_scale, HUD_OUTLINE_COLOR, max(1, thickness - 1))


def _hud_font_scale(text: str, *, frame_width: int) -> float:
    """Largest font scale whose rendered text still fits the HUD width budget."""
    unit_width, _ = cv2.getTextSize(text, FONT, fontScale=1.0, thickness=1)[0]
    return (frame_width * HUD_WIDTH_FRACTION) / max(unit_width, 1)


def _text_height(text: str, font_scale: float) -> int:
    (_, height), _ = cv2.getTextSize(text, FONT, fontScale=font_scale, thickness=1)
    return height
