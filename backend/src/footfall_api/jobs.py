"""Job execution: runs the counting pipeline off the event loop.

Threads, not processes, because OpenCV and torch release the GIL during the
work that matters. The seam that counts for later is `JobRunner`'s
interface: moving execution to separate processes (or hosts, for many live
cameras) replaces this class without touching the routes.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from footfall.config import AppConfig
from footfall.counting import CrossingEvent
from footfall.detection import PersonTracker
from footfall.pipeline import AnnotatedFrame, RunProgress, run
from footfall.video import VideoSourceError

from .bus import EventBus
from .preview import encode_jpeg
from .storage import Database

PROGRESS_EVERY_N_FRAMES = 5
# Encoding a preview on every frame would cost more than the inference does.
PREVIEW_MIN_INTERVAL_SECONDS = 0.5


@dataclass
class JobHandle:
    """Live, in-memory state for one running job."""

    job_id: str
    cancel_requested: threading.Event = field(default_factory=threading.Event)
    preview: bytes | None = None
    _last_preview_at: float = 0.0

    def wants_preview(self, now: float) -> bool:
        return now - self._last_preview_at >= PREVIEW_MIN_INTERVAL_SECONDS

    def set_preview(self, image: bytes, now: float) -> None:
        self.preview = image
        self._last_preview_at = now


TrackerFactory = Callable[[AppConfig], PersonTracker]


class JobRunner:
    def __init__(
        self,
        database: Database,
        bus: EventBus,
        *,
        max_workers: int,
        preview_width: int,
        tracker_factory: TrackerFactory | None = None,
    ) -> None:
        self._database = database
        self._bus = bus
        self._preview_width = preview_width
        # Injectable so tests (and, later, alternative detectors) do not have
        # to load YOLO weights.
        self._tracker_factory = tracker_factory
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="counting")
        self._handles: dict[str, JobHandle] = {}

    def submit(self, config: AppConfig, *, video_id: str, total_frames: int | None) -> str:
        job_id = uuid.uuid4().hex
        self._database.add_job(job_id, video_id, _config_summary(config), total_frames)
        self._handles[job_id] = JobHandle(job_id)
        self._executor.submit(self._execute, job_id, config)
        return job_id

    def cancel(self, job_id: str) -> bool:
        handle = self._handles.get(job_id)
        if handle is None:
            return False
        handle.cancel_requested.set()
        return True

    def preview_of(self, job_id: str) -> bytes | None:
        handle = self._handles.get(job_id)
        return handle.preview if handle else None

    def shutdown(self) -> None:
        for handle in self._handles.values():
            handle.cancel_requested.set()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _execute(self, job_id: str, config: AppConfig) -> None:
        handle = self._handles[job_id]
        self._set_status(job_id, "running")
        try:
            result = run(
                config,
                tracker=self._tracker_factory(config) if self._tracker_factory else None,
                on_progress=lambda progress: self._on_progress(job_id, progress),
                on_event=lambda event: self._on_event(job_id, event),
                on_frame=lambda frame: self._on_frame(handle, frame),
                should_stop=handle.cancel_requested.is_set,
            )
        except VideoSourceError as error:
            self._set_status(job_id, "failed", error=str(error))
            return
        except Exception as error:  # noqa: BLE001 - surfaced to the operator, never swallowed
            self._set_status(job_id, "failed", error=f"{type(error).__name__}: {error}")
            return

        self._database.set_job_counts(
            job_id,
            entries=result.counts.entries,
            exits=result.counts.exits,
            processed_frames=result.frames_processed,
        )
        self._publish_counts(job_id, result.counts, result.frames_processed)
        self._set_status(job_id, "cancelled" if handle.cancel_requested.is_set() else "completed")

    def _on_progress(self, job_id: str, progress: RunProgress) -> None:
        self._database.set_job_counts(
            job_id,
            entries=progress.counts.entries,
            exits=progress.counts.exits,
            processed_frames=progress.processed_frames,
        )
        self._publish_counts(job_id, progress.counts, progress.processed_frames)

    def _on_event(self, job_id: str, event: CrossingEvent) -> None:
        self._database.add_crossing(job_id, event)
        self._bus.publish_from_thread(
            job_id,
            {
                "type": "crossing",
                "track_id": event.track_id,
                "direction": str(event.direction),
                "frame_index": event.frame_index,
                "timestamp": event.timestamp,
            },
        )

    def _on_frame(self, handle: JobHandle, frame: AnnotatedFrame) -> None:
        now = time.monotonic()
        if handle.wants_preview(now):
            handle.set_preview(encode_jpeg(frame.image, self._preview_width), now)

    def _publish_counts(self, job_id: str, counts, processed_frames: int) -> None:
        self._bus.publish_from_thread(
            job_id,
            {
                "type": "progress",
                "processed_frames": processed_frames,
                "counts": {"entries": counts.entries, "exits": counts.exits, "net": counts.net},
            },
        )

    def _set_status(self, job_id: str, status: str, *, error: str | None = None) -> None:
        self._database.set_job_status(job_id, status, error=error)
        self._bus.publish_from_thread(job_id, {"type": "status", "status": status, "error": error})


def _config_summary(config: AppConfig) -> dict:
    """The knobs an operator chose, stored so a run stays reproducible."""
    return {
        "source": str(config.source),
        "line": list(config.line) if config.line else None,
        "in_direction": str(config.in_direction),
        "confidence": config.confidence,
        "imgsz": config.imgsz,
        "frame_stride": config.frame_stride,
        "max_frames": config.max_frames,
        "model": config.model,
    }


def build_config(
    *,
    source: Path,
    model: str,
    line,
    in_direction,
    confidence: float,
    imgsz: int | None,
    frame_stride: int,
    max_frames: int | None,
) -> AppConfig:
    """A monitoring run writes no video — events are the output."""
    return AppConfig(
        source=str(source),
        output=None,
        model=model,
        confidence=confidence,
        imgsz=imgsz,
        line=line,
        in_direction=in_direction,
        max_frames=max_frames,
        frame_stride=frame_stride,
        progress_interval=PROGRESS_EVERY_N_FRAMES,
    )
