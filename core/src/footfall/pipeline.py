"""Orchestration: stream frames -> track people -> count crossings -> emit events.

Writing an annotated video is optional and secondary. The primary output is
the crossing event stream, which is what a live dashboard, a history store,
or a downstream visualization consumes.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import cv2
import numpy as np

from .config import AppConfig
from .counting import Counts, CrossingEvent, LineCrossingCounter
from .detection import PersonTracker, TrackedPerson, YoloByteTrackTracker
from .geometry import Line
from .rendering import annotate
from .video import AnnotatedVideoWriter, VideoStream

PREVIEW_WINDOW = "footfall"
QUIT_KEY = "q"

ProgressCallback = Callable[["RunProgress"], None]
EventCallback = Callable[[CrossingEvent], None]
FrameCallback = Callable[["AnnotatedFrame"], None]


@dataclass(frozen=True)
class RunProgress:
    frame_index: int
    """Index in the source stream."""
    processed_frames: int
    """How many frames actually went through detection (see frame_stride)."""
    total_frames: int | None
    counts: Counts


@dataclass(frozen=True)
class AnnotatedFrame:
    """An annotated frame handed to observers (e.g. a live preview endpoint)."""

    frame_index: int
    timestamp: float
    image: np.ndarray
    people: tuple[TrackedPerson, ...]


@dataclass(frozen=True)
class RunResult:
    counts: Counts
    frames_processed: int
    line: Line


def run(
    config: AppConfig,
    *,
    tracker: PersonTracker | None = None,
    on_progress: ProgressCallback | None = None,
    on_event: EventCallback | None = None,
    on_frame: FrameCallback | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> RunResult:
    """Process the configured source and return the final counts.

    Every seam here exists for a reason: `tracker` is injectable so tests and
    alternative detectors need no YOLO weights; `on_event`/`on_frame` let a
    caller observe a run without waiting for it to finish; `should_stop` lets
    a supervisor cancel a job or shut a camera worker down cleanly.
    """
    with VideoStream(config.capture_target) as stream:
        geometry = stream.geometry
        line = (
            Line.horizontal_midline(geometry.width, geometry.height)
            if config.line is None
            else Line.from_coordinates(config.line)
        )
        counter = LineCrossingCounter(line, config.in_direction)
        person_tracker = tracker or YoloByteTrackTracker(config.model, config.confidence, config.imgsz)

        processed = 0
        with _writer_for(config, geometry) as writer:
            for frame_index, frame in _sampled_frames(stream, config.frame_stride):
                if should_stop is not None and should_stop():
                    break
                if config.max_frames is not None and processed >= config.max_frames:
                    break
                processed += 1
                timestamp = frame_index / geometry.fps

                people = person_tracker.track(frame)
                counter.forget({person.track_id for person in people})
                for person in people:
                    direction = counter.update(person.track_id, person.box.centroid)
                    if direction is not None and on_event is not None:
                        on_event(CrossingEvent(person.track_id, direction, frame_index, timestamp))

                annotated = annotate(frame, people=people, line=line, counts=counter.counts)
                if writer is not None:
                    writer.write(annotated)
                if on_frame is not None:
                    on_frame(AnnotatedFrame(frame_index, timestamp, annotated, people))

                if config.show and _preview_quit_requested(annotated):
                    break
                if on_progress is not None and processed % config.progress_interval == 0:
                    on_progress(RunProgress(frame_index, processed, geometry.frame_count, counter.counts))

        if config.show:
            cv2.destroyAllWindows()

    return RunResult(counts=counter.counts, frames_processed=processed, line=line)


@contextmanager
def _writer_for(config: AppConfig, geometry):
    """Open an output video, or nothing at all when `output` is None."""
    if config.output is None:
        yield None
        return
    with AnnotatedVideoWriter(config.output, geometry.fps, geometry.size) as writer:
        yield writer


def _sampled_frames(stream: VideoStream, stride: int) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (index, frame), keeping every `stride`-th frame.

    Frames are still decoded — skipping the decode of an arbitrary frame is
    not possible on a live stream — but inference only sees the sampled ones.
    """
    for index, frame in enumerate(stream.frames()):
        if index % stride == 0:
            yield index, frame


def _preview_quit_requested(frame: np.ndarray) -> bool:
    cv2.imshow(PREVIEW_WINDOW, frame)
    return cv2.waitKey(1) & 0xFF == ord(QUIT_KEY)
