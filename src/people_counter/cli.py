"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import (
    DEFAULT_CONFIDENCE,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT,
    DEFAULT_PROGRESS_INTERVAL,
    AppConfig,
)
from .counting import InDirection
from .pipeline import RunProgress, RunResult, run
from .video import VideoSourceError

DESCRIPTION = "Camera-based people in/out counter (YOLO + ByteTrack)."
EPILOG = """examples:
  people-counter pedestrian.mp4 --output annotated.mp4
  people-counter rtsp://user:pass@camera-ip/stream --output annotated.mp4
  people-counter 0 --show
"""
STREAM_PREFIXES = ("rtsp://", "rtmp://", "http://", "https://", "udp://", "tcp://")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="people-counter",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Video file path, RTSP/HTTP URL, or webcam index (e.g. 0).",
    )
    parser.add_argument(
        "--source",
        dest="source_flag",
        help="Deprecated alias for the positional SOURCE argument.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path to write the annotated video (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ultralytics weights (default: {DEFAULT_MODEL} — fastest for CPU testing).",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=DEFAULT_CONFIDENCE,
        help=f"Detection confidence threshold (default: {DEFAULT_CONFIDENCE}).",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=None,
        metavar="N",
        help="Inference resolution (default: the model's 640). Raise it (e.g. 1280) for "
        "high-resolution wide shots where people are small; costs speed.",
    )
    parser.add_argument(
        "--line",
        type=float,
        nargs=4,
        metavar=("X1", "Y1", "X2", "Y2"),
        default=None,
        help="Counting line endpoints in pixels (default: horizontal line across the frame's middle).",
    )
    parser.add_argument(
        "--in-direction",
        type=InDirection,
        choices=list(InDirection),
        default=InDirection.NEGATIVE_TO_POSITIVE,
        help="Which side-of-line transition counts as 'in'. Flip this if a test run shows IN/OUT swapped.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N frames — useful for a quick accuracy spot-check on a long clip.",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=DEFAULT_PROGRESS_INTERVAL,
        metavar="N",
        help=f"Print running counts every N frames (default: {DEFAULT_PROGRESS_INTERVAL}).",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Also display the annotated video live in a window while processing.",
    )
    return parser


def config_from_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> AppConfig:
    source = args.source or args.source_flag
    if not source:
        parser.error("a video SOURCE is required (positional argument, e.g. pedestrian.mp4)")
    if args.source and args.source_flag:
        parser.error("pass SOURCE either positionally or via --source, not both")
    if args.max_frames is not None and args.max_frames < 1:
        parser.error("--max-frames must be at least 1")
    if args.imgsz is not None and args.imgsz < 32:
        parser.error("--imgsz must be at least 32")
    if args.progress_interval < 1:
        parser.error("--progress-interval must be at least 1")

    return AppConfig(
        source=source,
        output=args.output,
        model=args.model,
        confidence=args.conf,
        imgsz=args.imgsz,
        line=tuple(args.line) if args.line is not None else None,
        in_direction=args.in_direction,
        show=args.show,
        max_frames=args.max_frames,
        progress_interval=args.progress_interval,
    )


def validate_source(config: AppConfig, parser: argparse.ArgumentParser) -> None:
    """Fail fast with a clear message when a local file simply is not there."""
    if config.webcam_index is not None:
        return
    if config.source.startswith(STREAM_PREFIXES):
        return
    if not Path(config.source).exists():
        parser.error(f"video file not found: {config.source}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = config_from_args(args, parser)
    validate_source(config, parser)

    try:
        result = run(config, on_progress=_print_progress)
    except VideoSourceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted — partial output kept.", file=sys.stderr)
        return 130

    _print_summary(result, config)
    return 0


def _print_progress(progress: RunProgress) -> None:
    total = f"/{progress.total_frames}" if progress.total_frames else ""
    counts = progress.counts
    print(
        f"frame {progress.frame_index}{total}: IN={counts.entries} OUT={counts.exits} NET={counts.net}",
        flush=True,
    )


def _print_summary(result: RunResult, config: AppConfig) -> None:
    counts = result.counts
    print("\n--- Final counts ---")
    print(f"Frames processed: {result.frames_processed}")
    print(f"IN:  {counts.entries}")
    print(f"OUT: {counts.exits}")
    print(f"NET (people currently inside, relative to start of clip): {counts.net}")
    print(f"Annotated video written to: {config.output}")
