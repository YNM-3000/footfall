import pytest

from footfall.counting import Counts, Direction, InDirection, LineCrossingCounter
from footfall.geometry import Line

ABOVE = (50.0, 10.0)  # negative side of the midline
BELOW = (50.0, 90.0)  # positive side of the midline


@pytest.fixture
def line() -> Line:
    return Line((0.0, 50.0), (100.0, 50.0))


def test_counts_net_is_entries_minus_exits():
    assert Counts(entries=5, exits=2).net == 3


def test_counts_updates_return_new_snapshots():
    original = Counts()

    entered = original.plus_entry()

    assert (original.entries, entered.entries) == (0, 1)


def test_first_sighting_never_counts(line):
    counter = LineCrossingCounter(line, InDirection.NEGATIVE_TO_POSITIVE)

    counter.update(track_id=1, point=BELOW)

    assert counter.counts == Counts(entries=0, exits=0)


def test_negative_to_positive_crossing_counts_as_entry(line):
    counter = LineCrossingCounter(line, InDirection.NEGATIVE_TO_POSITIVE)

    counter.update(1, ABOVE)
    counter.update(1, BELOW)

    assert counter.counts == Counts(entries=1, exits=0)


def test_positive_to_negative_crossing_counts_as_exit(line):
    counter = LineCrossingCounter(line, InDirection.NEGATIVE_TO_POSITIVE)

    counter.update(1, BELOW)
    counter.update(1, ABOVE)

    assert counter.counts == Counts(entries=0, exits=1)


def test_in_direction_flag_swaps_entries_and_exits(line):
    counter = LineCrossingCounter(line, InDirection.POSITIVE_TO_NEGATIVE)

    counter.update(1, ABOVE)
    counter.update(1, BELOW)

    assert counter.counts == Counts(entries=0, exits=1)


def test_staying_on_one_side_never_counts(line):
    counter = LineCrossingCounter(line, InDirection.NEGATIVE_TO_POSITIVE)

    for _ in range(5):
        counter.update(1, ABOVE)

    assert counter.counts == Counts(entries=0, exits=0)


def test_tracks_are_counted_independently(line):
    counter = LineCrossingCounter(line, InDirection.NEGATIVE_TO_POSITIVE)

    counter.update(1, ABOVE)
    counter.update(2, BELOW)
    counter.update(1, BELOW)
    counter.update(2, ABOVE)

    assert counter.counts == Counts(entries=1, exits=1)


def test_round_trip_nets_to_zero(line):
    counter = LineCrossingCounter(line, InDirection.NEGATIVE_TO_POSITIVE)

    for point in (ABOVE, BELOW, ABOVE):
        counter.update(1, point)

    assert counter.counts.net == 0


def test_update_returns_the_crossing_direction(line):
    counter = LineCrossingCounter(line, InDirection.NEGATIVE_TO_POSITIVE)

    assert counter.update(1, ABOVE) is None
    assert counter.update(1, BELOW) is Direction.IN
    assert counter.update(1, ABOVE) is Direction.OUT


def test_forget_prunes_tracks_that_are_gone(line):
    """A live camera runs for days; per-track state cannot grow forever."""
    counter = LineCrossingCounter(line, InDirection.NEGATIVE_TO_POSITIVE)
    counter.update(1, ABOVE)

    counter.forget(active_track_ids={2})
    counter.update(1, BELOW)

    assert counter.counts == Counts(), "a forgotten track must be treated as newly seen"
