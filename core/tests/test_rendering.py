"""Overlay tests — cheap pixel-level checks that the annotation actually lands."""

import numpy as np

from footfall.counting import Counts
from footfall.detection import TrackedPerson
from footfall.geometry import BoundingBox, Line
from footfall.rendering import BOX_COLOR, _hud_font_scale, annotate


def blank(width: int = 640, height: int = 480) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_annotate_draws_onto_the_frame():
    frame = blank()

    annotated = annotate(
        frame,
        people=[TrackedPerson(1, BoundingBox(100.0, 100.0, 200.0, 300.0))],
        line=Line.horizontal_midline(640, 480),
        counts=Counts(),
    )

    assert annotated.any(), "expected the overlay to change some pixels"


def test_boxes_are_drawn_in_the_box_color():
    frame = blank()

    annotate(
        frame,
        people=[TrackedPerson(1, BoundingBox(100.0, 100.0, 200.0, 300.0))],
        line=Line.horizontal_midline(640, 480),
        counts=Counts(),
    )

    assert tuple(frame[100, 150]) == BOX_COLOR


def test_float_line_coordinates_do_not_crash_opencv():
    frame = blank()

    annotate(
        frame,
        people=[],
        line=Line((0.5, 10.25), (639.75, 470.5)),
        counts=Counts(entries=1, exits=1),
    )

    assert frame.any()


def test_hud_font_scale_grows_with_frame_width():
    text = "IN: 0  OUT: 0  NET (current): 0"

    assert _hud_font_scale(text, frame_width=2160) > _hud_font_scale(text, frame_width=640)
