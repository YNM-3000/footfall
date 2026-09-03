"""Video input/output wrappers.

Both classes are context managers so capture/writer handles are always
released, including when the pipeline raises part-way through a clip.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

import cv2
import numpy as np

from .config import DEFAULT_FPS

FOURCC = "mp4v"


class VideoSourceError(RuntimeError):
    """Raised when a source cannot be opened or an output cannot be written."""


@dataclass(frozen=True)
class FrameGeometry:
    width: int
    height: int
    fps: float
    frame_count: int | None

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)


class VideoStream:
    """Reads frames from a file, stream URL, or webcam index."""

    def __init__(self, target: str | int) -> None:
        self._target = target
        self._capture: cv2.VideoCapture | None = None

    def __enter__(self) -> VideoStream:
        capture = cv2.VideoCapture(self._target)
        if not capture.isOpened():
            capture.release()
            raise VideoSourceError(f"Could not open video source: {self._target}")
        self._capture = capture
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    @property
    def geometry(self) -> FrameGeometry:
        capture = self._require_capture()
        declared_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        return FrameGeometry(
            width=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            # Live streams often report 0 fps; fall back to a sane default so
            # the output video is not written with an invalid frame rate.
            fps=capture.get(cv2.CAP_PROP_FPS) or DEFAULT_FPS,
            # Streams and some containers report 0 or a negative count.
            frame_count=declared_frames if declared_frames > 0 else None,
        )

    def frames(self) -> Iterator[np.ndarray]:
        capture = self._require_capture()
        while True:
            ok, frame = capture.read()
            if not ok:
                return
            yield frame

    def frame_at(self, frame_index: int) -> np.ndarray:
        capture = self._require_capture()
        if frame_index > 0:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            raise VideoSourceError(f"Could not read frame {frame_index} from {self._target}")
        return frame

    def _require_capture(self) -> cv2.VideoCapture:
        if self._capture is None:
            raise VideoSourceError("VideoStream used outside of its context manager.")
        return self._capture


def grab_frame(target: str | int, frame_index: int = 0) -> np.ndarray:
    """Read a single frame — used to show an operator where to put the line."""
    with VideoStream(target) as stream:
        return stream.frame_at(frame_index)


class AnnotatedVideoWriter:
    """Writes annotated frames to an mp4, creating parent directories."""

    def __init__(self, path: Path, fps: float, size: tuple[int, int]) -> None:
        self._path = path
        self._fps = fps
        self._size = size
        self._writer: cv2.VideoWriter | None = None

    def __enter__(self) -> AnnotatedVideoWriter:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(self._path),
            cv2.VideoWriter.fourcc(*FOURCC),
            self._fps,
            self._size,
        )
        if not writer.isOpened():
            writer.release()
            raise VideoSourceError(
                f"Could not open '{self._path}' for writing "
                f"({self._size[0]}x{self._size[1]} @ {self._fps:.2f} fps, codec {FOURCC})."
            )
        self._writer = writer
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None

    def write(self, frame: np.ndarray) -> None:
        if self._writer is None:
            raise VideoSourceError("AnnotatedVideoWriter used outside of its context manager.")
        self._writer.write(frame)
