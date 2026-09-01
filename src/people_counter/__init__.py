"""Camera-based people counting: YOLO detection -> ByteTrack IDs -> line crossings."""

from .config import AppConfig
from .counting import Counts, InDirection, LineCrossingCounter
from .geometry import BoundingBox, Line
from .pipeline import RunResult, run

__version__ = "0.2.0"

__all__ = [
    "AppConfig",
    "BoundingBox",
    "Counts",
    "InDirection",
    "Line",
    "LineCrossingCounter",
    "RunResult",
    "__version__",
    "run",
]
