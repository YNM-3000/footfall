"""Person detection + tracking.

`PersonTracker` is the seam the rest of the pipeline depends on, so a
different detector or tracker can be dropped in without touching the
counting, rendering, or CLI layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .config import PERSON_CLASS_ID
from .geometry import BoundingBox


@dataclass(frozen=True)
class TrackedPerson:
    """One person in one frame, with an identity stable across frames."""

    track_id: int
    box: BoundingBox


class PersonTracker(Protocol):
    def track(self, frame: np.ndarray) -> tuple[TrackedPerson, ...]:
        """Return the tracked people visible in this frame."""
        ...


class YoloByteTrackTracker:
    """Ultralytics YOLO detection with ByteTrack identity persistence."""

    def __init__(self, model_path: str, confidence: float, imgsz: int | None = None) -> None:
        # Imported lazily: ultralytics pulls in torch, which is slow enough to
        # make `--help` feel broken if it loads at import time.
        from ultralytics import YOLO

        self._model = YOLO(model_path)
        self._confidence = confidence
        # None leaves ultralytics on its default (640). Raising it matters for
        # high-resolution wide shots, where people shrink to a few pixels once
        # the frame is letterboxed down.
        self._imgsz = imgsz

    def track(self, frame: np.ndarray) -> tuple[TrackedPerson, ...]:
        # persist=True keeps ByteTrack's identity memory across calls;
        # classes restricts detection to the COCO "person" class.
        results = self._model.track(
            frame,
            persist=True,
            classes=[PERSON_CLASS_ID],
            conf=self._confidence,
            verbose=False,
            **({} if self._imgsz is None else {"imgsz": self._imgsz}),
        )
        boxes = results[0].boxes
        if boxes is None or boxes.id is None:
            return ()

        coordinates = boxes.xyxy.cpu().numpy()
        track_ids = boxes.id.cpu().numpy().astype(int)
        return tuple(
            TrackedPerson(track_id=int(track_id), box=BoundingBox(*(float(v) for v in box)))
            for box, track_id in zip(coordinates, track_ids)
        )
