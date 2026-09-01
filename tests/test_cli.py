from pathlib import Path

import pytest

from people_counter.cli import build_parser, config_from_args, validate_source
from people_counter.counting import InDirection


def parse(argv: list[str]):
    parser = build_parser()
    return config_from_args(parser.parse_args(argv), parser)


def test_positional_source_is_accepted(tmp_path: Path):
    """Regression: `people_counter.py pedestrian.mp4 --output annotated.mp4`."""
    config = parse(["pedestrian.mp4", "--output", "annotated.mp4"])

    assert config.source == "pedestrian.mp4"
    assert config.output == Path("annotated.mp4")


def test_source_flag_still_works_for_backwards_compatibility():
    config = parse(["--source", "clip.mp4"])

    assert config.source == "clip.mp4"


def test_passing_source_both_ways_is_rejected():
    with pytest.raises(SystemExit):
        parse(["clip.mp4", "--source", "other.mp4"])


def test_missing_source_is_rejected():
    with pytest.raises(SystemExit):
        parse([])


def test_defaults_match_documented_values():
    config = parse(["clip.mp4"])

    assert config.model == "yolov8n.pt"
    assert config.confidence == pytest.approx(0.35)
    assert config.line is None
    assert config.in_direction is InDirection.NEGATIVE_TO_POSITIVE
    assert config.max_frames is None
    assert config.show is False


def test_line_is_parsed_as_four_floats():
    config = parse(["clip.mp4", "--line", "0", "10", "640", "10"])

    assert config.line == (0.0, 10.0, 640.0, 10.0)


def test_in_direction_accepts_the_documented_strings():
    config = parse(["clip.mp4", "--in-direction", "positive-to-negative"])

    assert config.in_direction is InDirection.POSITIVE_TO_NEGATIVE


def test_non_positive_max_frames_is_rejected():
    with pytest.raises(SystemExit):
        parse(["clip.mp4", "--max-frames", "0"])


def test_webcam_index_source_maps_to_int_capture_target():
    config = parse(["0"])

    assert config.webcam_index == 0
    assert config.capture_target == 0


def test_file_source_maps_to_string_capture_target():
    config = parse(["clip.mp4"])

    assert config.webcam_index is None
    assert config.capture_target == "clip.mp4"


def test_missing_file_fails_fast_before_loading_the_model():
    parser = build_parser()
    config = parse(["definitely-not-here.mp4"])

    with pytest.raises(SystemExit):
        validate_source(config, parser)


def test_stream_urls_are_not_checked_on_disk():
    parser = build_parser()
    config = parse(["rtsp://user:pass@camera/stream"])

    validate_source(config, parser)  # must not raise
