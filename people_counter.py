"""
people_counter.py — minimal path validation for camera-based people counting.

Pipeline: YOLOv8 (person detection) -> ByteTrack (persistent IDs, built into
ultralytics) -> virtual line-crossing logic (in/out/net occupancy).

USAGE (via uv — see pyproject.toml alongside this script)
-----------------------------------------------------------
    # uv creates the venv and installs dependencies automatically on first run.

    # From an uploaded video file:
    uv run people_counter.py --source path/to/video.mp4 --output annotated.mp4

    # From a live stream (RTSP/HTTP camera URL):
    uv run people_counter.py --source rtsp://user:pass@camera-ip/stream --output annotated.mp4

    # From a webcam (device index):
    uv run people_counter.py --source 0

The counting line defaults to a horizontal line across the middle of the
frame. Override it with --line x1 y1 x2 y2 (pixel coordinates) to match
your camera's actual gate/corridor geometry — draw it perpendicular to the
direction people walk, not parallel to it.

OUTPUT
------
- An annotated video (boxes, IDs, the counting line, and a running
  IN / OUT / NET occupancy readout) written to --output, so you can
  eyeball it against a manual count on a short clip.
- Live counts printed to stdout as the video processes.
- On exit, final IN/OUT/NET totals are printed.

This is intentionally source-agnostic: swapping a file path for a live
camera URL later requires no code changes, only a different --source.
"""

import argparse
import sys

import cv2
from ultralytics import YOLO


def side_of_line(point, line_p1, line_p2):
    """Return which side of the line (p1->p2) a point falls on.

    Positive/negative sign indicates side; magnitude is unused. Crossing
    the line means this sign flips between two consecutive frames.
    """
    (x, y) = point
    (x1, y1) = line_p1
    (x2, y2) = line_p2
    return (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)


def parse_args():
    p = argparse.ArgumentParser(description="Camera-based people in/out counter (YOLO + ByteTrack).")
    p.add_argument("--source", required=True, help="Video file path, RTSP/HTTP URL, or webcam index (e.g. 0).")
    p.add_argument("--output", default="annotated_output.mp4", help="Path to write the annotated video.")
    p.add_argument("--model", default="yolov8n.pt", help="Ultralytics model weights (nano is fastest for CPU testing).")
    p.add_argument("--conf", type=float, default=0.35, help="Detection confidence threshold.")
    p.add_argument(
        "--line",
        type=float,
        nargs=4,
        metavar=("X1", "Y1", "X2", "Y2"),
        default=None,
        help="Counting line endpoints in pixels. Defaults to a horizontal line across the frame's vertical middle.",
    )
    p.add_argument(
        "--in-direction",
        choices=["positive-to-negative", "negative-to-positive"],
        default="negative-to-positive",
        help="Which side-of-line transition counts as 'in' vs 'out'. Flip this if your first test run shows in/out swapped.",
    )
    p.add_argument("--show", action="store_true", help="Also display the annotated video live in a window while processing.")
    return p.parse_args()


def main():
    args = parse_args()

    # Webcam indices arrive as strings from argparse; cv2 wants an int for those.
    source = int(args.source) if args.source.isdigit() else args.source

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        sys.exit(f"Could not open video source: {args.source}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    line_p1, line_p2 = (
        ((0, height // 2), (width, height // 2)) if args.line is None else ((args.line[0], args.line[1]), (args.line[2], args.line[3]))
    )

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(args.output, fourcc, fps, (width, height))

    model = YOLO(args.model)

    track_last_side = {}  # track_id -> last known sign relative to the line
    counted_in = 0
    counted_out = 0

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1

        # persist=True keeps ByteTrack's identity memory across frames.
        # classes=[0] restricts detection to the COCO "person" class.
        results = model.track(frame, persist=True, classes=[0], conf=args.conf, verbose=False)
        result = results[0]

        if result.boxes is not None and result.boxes.id is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            ids = result.boxes.id.cpu().numpy().astype(int)

            for box, track_id in zip(boxes, ids):
                x1, y1, x2, y2 = box
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

                sign = side_of_line((cx, cy), line_p1, line_p2)
                current_side = sign > 0

                if track_id in track_last_side:
                    prev_side = track_last_side[track_id]
                    if prev_side != current_side:
                        crossed_pos_to_neg = prev_side and not current_side
                        if args.in_direction == "negative-to-positive":
                            is_in = not crossed_pos_to_neg
                        else:
                            is_in = crossed_pos_to_neg

                        if is_in:
                            counted_in += 1
                        else:
                            counted_out += 1

                track_last_side[track_id] = current_side

                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(frame, f"ID {track_id}", (int(x1), int(y1) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.line(frame, line_p1, line_p2, (0, 0, 255), 2)
        net = counted_in - counted_out
        overlay = f"IN: {counted_in}  OUT: {counted_out}  NET (current): {net}"
        cv2.putText(frame, overlay, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
        cv2.putText(frame, overlay, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 1)

        writer.write(frame)
        if args.show:
            cv2.imshow("people_counter", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        if frame_idx % 30 == 0:
            print(f"frame {frame_idx}: IN={counted_in} OUT={counted_out} NET={net}")

    cap.release()
    writer.release()
    if args.show:
        cv2.destroyAllWindows()

    print("\n--- Final counts ---")
    print(f"IN:  {counted_in}")
    print(f"OUT: {counted_out}")
    print(f"NET (people currently inside, relative to start of clip): {counted_in - counted_out}")
    print(f"Annotated video written to: {args.output}")


if __name__ == "__main__":
    main()
