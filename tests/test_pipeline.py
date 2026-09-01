"""End-to-end pipeline test on a synthetic clip, with a stubbed tracker.

Covers the wiring (video in -> counting -> annotated video out) without
downloading YOLO weights or running inference.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from people_counter.config import AppConfig
from people_counter.detection import TrackedPerson
from people_counter.geometry import BoundingBox
from people_counter.pipeline import run
from people_counter.video import VideoSourceError

FRAME_WIDTH = 320
FRAME_HEIGHT = 240
FRAME_COUNT = 10


class WalkingPersonTracker:
    """One person walking top-to-bottom, crossing the midline once."""

    def __init__(self) -> None:
        self._frame = 0

    def track(self, frame: np.ndarray) -> tuple[TrackedPerson, ...]:
        y = self._frame * (FRAME_HEIGHT / FRAME_COUNT)
        self._frame += 1
        return (TrackedPerson(track_id=1, box=BoundingBox(100.0, y, 140.0, y + 20.0)),)


@pytest.fixture
def clip(tmp_path: Path) -> Path:
    path = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (FRAME_WIDTH, FRAME_HEIGHT),
    )
    assert writer.isOpened(), "OpenCV could not create the fixture clip"
    for _ in range(FRAME_COUNT):
        writer.write(np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8))
    writer.release()
    return path


def test_run_counts_the_crossing_and_writes_an_annotated_video(clip: Path, tmp_path: Path):
    output = tmp_path / "nested" / "annotated.mp4"
    config = AppConfig(source=str(clip), output=output)

    result = run(config, tracker=WalkingPersonTracker())

    assert result.counts.entries == 1
    assert result.counts.exits == 0
    assert result.frames_processed == FRAME_COUNT
    assert output.exists() and output.stat().st_size > 0


def test_max_frames_stops_early(clip: Path, tmp_path: Path):
    config = AppConfig(source=str(clip), output=tmp_path / "annotated.mp4", max_frames=3)

    result = run(config, tracker=WalkingPersonTracker())

    assert result.frames_processed == 3


def test_unopenable_source_raises_video_source_error(tmp_path: Path):
    config = AppConfig(source=str(tmp_path / "missing.mp4"), output=tmp_path / "out.mp4")

    with pytest.raises(VideoSourceError):
        run(config, tracker=WalkingPersonTracker())
