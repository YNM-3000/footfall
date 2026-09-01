"""Line-crossing counter: turns per-frame track positions into IN/OUT totals."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .geometry import Line, Point


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

    def update(self, track_id: int, point: Point) -> None:
        """Record a track's position for the current frame."""
        current_side = self._line.is_positive_side(point)
        previous_side = self._last_side.get(track_id)
        self._last_side[track_id] = current_side

        if previous_side is None or previous_side == current_side:
            return

        entered = self._is_entry(previous_side=previous_side, current_side=current_side)
        self._counts = self._counts.plus_entry() if entered else self._counts.plus_exit()

    def _is_entry(self, *, previous_side: bool, current_side: bool) -> bool:
        crossed_negative_to_positive = not previous_side and current_side
        if self._in_direction is InDirection.NEGATIVE_TO_POSITIVE:
            return crossed_negative_to_positive
        return not crossed_negative_to_positive
