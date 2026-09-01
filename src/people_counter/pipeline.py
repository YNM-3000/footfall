"""Orchestration: stream frames -> track people -> count crossings -> write video."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import cv2

from .config import AppConfig
from .counting import Counts, LineCrossingCounter
from .detection import PersonTracker, YoloByteTrackTracker
from .geometry import Line
from .rendering import annotate
from .video import AnnotatedVideoWriter, VideoStream

PREVIEW_WINDOW = "people_counter"
QUIT_KEY = "q"

ProgressCallback = Callable[["RunProgress"], None]


@dataclass(frozen=True)
class RunProgress:
    frame_index: int
    total_frames: int | None
    counts: Counts


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
) -> RunResult:
    """Process the configured source and return the final counts.

    `tracker` is injectable so tests (and future detector swaps) do not have
    to load YOLO weights.
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

        frame_index = 0
        with AnnotatedVideoWriter(config.output, geometry.fps, geometry.size) as writer:
            for frame in stream.frames():
                if config.max_frames is not None and frame_index >= config.max_frames:
                    break
                frame_index += 1

                people = person_tracker.track(frame)
                for person in people:
                    counter.update(person.track_id, person.box.centroid)

                writer.write(annotate(frame, people=people, line=line, counts=counter.counts))

                if config.show and _preview_quit_requested(frame):
                    break
                if on_progress is not None and frame_index % config.progress_interval == 0:
                    on_progress(RunProgress(frame_index, geometry.frame_count, counter.counts))

        if config.show:
            cv2.destroyAllWindows()

    return RunResult(counts=counter.counts, frames_processed=frame_index, line=line)


def _preview_quit_requested(frame) -> bool:
    cv2.imshow(PREVIEW_WINDOW, frame)
    return cv2.waitKey(1) & 0xFF == ord(QUIT_KEY)
