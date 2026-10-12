"""Line-crossing counter: turns per-frame track positions into IN/OUT totals."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .geometry import Line, Point


class Direction(str, Enum):
    """The direction of a single counted crossing."""

    IN = "in"
    OUT = "out"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CrossingEvent:
    """One person crossing the gate, at a point in time.

    Events — not running totals — are the durable output of the pipeline:
    totals can always be recomputed from events, but events cannot be
    recovered from a total. Live dashboards, history charts, and occupancy
    true-ups all read from this.
    """

    track_id: int
    direction: Direction
    frame_index: int
    timestamp: float
    """Seconds since the start of the stream or clip."""


class InDirection(str, Enum):
    """Which side-of-line transition is treated as an entry."""

    NEGATIVE_TO_POSITIVE = "negative-to-positive"
    POSITIVE_TO_NEGATIVE = "positive-to-negative"

    def __str__(self) -> str:
        # Keeps argparse help/choices readable ("negative-to-positive").
        return self.value


@dataclass(frozen=True)
class Counts:
    """Immutable snapshot of the running totals."""

    entries: int = 0
    exits: int = 0

    @property
    def net(self) -> int:
        return self.entries - self.exits

    def plus_entry(self) -> Counts:
        return Counts(self.entries + 1, self.exits)

    def plus_exit(self) -> Counts:
        return Counts(self.entries, self.exits + 1)


class LineCrossingCounter:
    """Tracks each ID's side of the gate and counts sign flips as crossings.

    State is deliberately minimal: the last known side per track ID, plus an
    immutable `Counts` snapshot that is replaced (never mutated) on each event.
    """

    def __init__(self, line: Line, in_direction: InDirection) -> None:
        self._line = line
        self._in_direction = in_direction
        self._last_side: dict[int, bool] = {}
        self._counts = Counts()

    @property
    def counts(self) -> Counts:
        return self._counts

    def update(self, track_id: int, point: Point) -> Direction | None:
        """Record a track's position; return the direction if it just crossed."""
        current_side = self._line.is_positive_side(point)
        previous_side = self._last_side.get(track_id)
        self._last_side[track_id] = current_side

        if previous_side is None or previous_side == current_side:
            return None

        entered = self._is_entry(previous_side=previous_side, current_side=current_side)
        self._counts = self._counts.plus_entry() if entered else self._counts.plus_exit()
        return Direction.IN if entered else Direction.OUT

    def forget(self, active_track_ids: set[int]) -> None:
        """Drop state for tracks that are gone.

        On a live stream this runs for days; without pruning, the per-track
        side map grows without bound.
        """
        self._last_side = {
            track_id: side for track_id, side in self._last_side.items() if track_id in active_track_ids
        }

    def _is_entry(self, *, previous_side: bool, current_side: bool) -> bool:
        crossed_negative_to_positive = not previous_side and current_side
        if self._in_direction is InDirection.NEGATIVE_TO_POSITIVE:
            return crossed_negative_to_positive
        return not crossed_negative_to_positive
