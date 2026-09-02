"""Camera-based people counting: YOLO detection -> ByteTrack IDs -> line crossings."""

from .config import AppConfig
from .counting import Counts, CrossingEvent, Direction, InDirection, LineCrossingCounter
from .geometry import BoundingBox, Line
from .pipeline import AnnotatedFrame, RunResult, run

__version__ = "0.3.0"

__all__ = [
    "AnnotatedFrame",
    "AppConfig",
    "BoundingBox",
    "Counts",
    "CrossingEvent",
    "Direction",
    "InDirection",
    "Line",
    "LineCrossingCounter",
    "RunResult",
    "__version__",
    "run",
]
