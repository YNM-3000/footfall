"""Runtime configuration for a counting run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .counting import InDirection

DEFAULT_MODEL = "yolov8n.pt"
DEFAULT_OUTPUT = Path("annotated_output.mp4")
DEFAULT_CONFIDENCE = 0.35
DEFAULT_FPS = 25.0
DEFAULT_PROGRESS_INTERVAL = 30
PERSON_CLASS_ID = 0  # COCO class index for "person"


@dataclass(frozen=True)
class AppConfig:
    """Everything a run needs, resolved from CLI arguments.

    `source` is kept source-agnostic: a file path, an RTSP/HTTP URL, or a
    webcam index. Swapping a recording for a live camera is a config change,
    not a code change.
    """

    source: str
    output: Path = DEFAULT_OUTPUT
    model: str = DEFAULT_MODEL
    confidence: float = DEFAULT_CONFIDENCE
    imgsz: int | None = None
    line: tuple[float, float, float, float] | None = None
    in_direction: InDirection = InDirection.NEGATIVE_TO_POSITIVE
    show: bool = False
    max_frames: int | None = None
    progress_interval: int = DEFAULT_PROGRESS_INTERVAL

    @property
    def webcam_index(self) -> int | None:
        """The webcam device index, when `source` names one."""
        return int(self.source) if self.source.isdigit() else None

    @property
    def capture_target(self) -> str | int:
        """What to hand to OpenCV: an int for webcams, the string otherwise."""
        index = self.webcam_index
        return self.source if index is None else index
