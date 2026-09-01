"""Line geometry for the virtual counting gate.

Pure functions and immutable value objects only — no OpenCV, no model code —
so the crossing maths stays trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass

Point = tuple[float, float]
IntPoint = tuple[int, int]


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned detection box in pixel coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def centroid(self) -> Point:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def top_left(self) -> IntPoint:
        return (int(self.x1), int(self.y1))

    @property
    def bottom_right(self) -> IntPoint:
        return (int(self.x2), int(self.y2))


@dataclass(frozen=True)
class Line:
    """A directed line segment used as the counting gate."""

    p1: Point
    p2: Point

    @classmethod
    def horizontal_midline(cls, width: int, height: int) -> Line:
        """Default gate: a horizontal line across the frame's vertical middle."""
        mid_y = height / 2
        return cls((0.0, mid_y), (float(width), mid_y))

    @classmethod
    def from_coordinates(cls, coordinates: tuple[float, float, float, float]) -> Line:
        x1, y1, x2, y2 = coordinates
        return cls((x1, y1), (x2, y2))

    def side_of(self, point: Point) -> float:
        """Signed cross product: which side of p1->p2 the point falls on.

        The sign indicates the side; the magnitude is unused. A track crosses
        the line when this sign flips between two consecutive frames.
        """
        x, y = point
        x1, y1 = self.p1
        x2, y2 = self.p2
        return (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)

    def is_positive_side(self, point: Point) -> bool:
        return self.side_of(point) > 0

    @property
    def int_endpoints(self) -> tuple[IntPoint, IntPoint]:
        """Endpoints rounded to ints — OpenCV drawing rejects floats."""
        return (
            (round(self.p1[0]), round(self.p1[1])),
            (round(self.p2[0]), round(self.p2[1])),
        )
