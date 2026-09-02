"""End-to-end pipeline test on a synthetic clip, with a stubbed tracker.

Covers the wiring (video in -> counting -> annotated video out) without
downloading YOLO weights or running inference.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from people_counter.config import AppConfig
from people_counter.counting import Direction
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


def test_run_emits_crossing_events_with_timestamps(clip: Path, tmp_path: Path):
    events = []
    config = AppConfig(source=str(clip), output=None)

    run(config, tracker=WalkingPersonTracker(), on_event=events.append)

    assert len(events) == 1
    event = events[0]
    assert event.direction is Direction.IN
    assert event.track_id == 1
    assert event.timestamp == pytest.approx(event.frame_index / 10.0)


def test_output_none_writes_no_video(clip: Path, tmp_path: Path):
    config = AppConfig(source=str(clip), output=None)

    result = run(config, tracker=WalkingPersonTracker())

    assert result.frames_processed == FRAME_COUNT
    assert list(tmp_path.glob("*.mp4")) == [clip]


def test_frame_stride_samples_frames(clip: Path, tmp_path: Path):
    config = AppConfig(source=str(clip), output=None, frame_stride=2)

    result = run(config, tracker=WalkingPersonTracker())

    assert result.frames_processed == FRAME_COUNT // 2


def test_should_stop_cancels_the_run(clip: Path, tmp_path: Path):
    calls = {"n": 0}

    def should_stop() -> bool:
        calls["n"] += 1
        return calls["n"] > 4

    result = run(
        AppConfig(source=str(clip), output=None),
        tracker=WalkingPersonTracker(),
        should_stop=should_stop,
    )

    assert result.frames_processed == 4


def test_on_frame_receives_annotated_images(clip: Path, tmp_path: Path):
    frames = []

    run(
        AppConfig(source=str(clip), output=None, max_frames=3),
        tracker=WalkingPersonTracker(),
        on_frame=frames.append,
    )

    assert len(frames) == 3
    assert frames[0].image.shape == (FRAME_HEIGHT, FRAME_WIDTH, 3)
    assert frames[0].people[0].track_id == 1
