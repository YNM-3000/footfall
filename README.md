# People Counter

Camera-based people counting: detect and track people via computer vision,
count entries/exits across a virtual line, and (next phase) feed the
resulting occupancy numbers into a real-time 3D visualization of the
station.

## How it works

1. **Detection** — [YOLOv8](https://github.com/ultralytics/ultralytics)
   (`models/yolov8n.pt`) finds every person in each video frame.
2. **Tracking** — ByteTrack (built into `ultralytics`) assigns a persistent
   ID to each detected person across frames.
3. **Counting** — a virtual line is drawn across the frame (e.g. a gate or
   corridor). When a tracked person's centroid crosses it, an IN or OUT
   counter increments depending on direction.
4. **Occupancy** — running total = IN − OUT.

## Requirements

- Python ≥ 3.10
- [`uv`](https://github.com/astral-sh/uv) for dependency management

```bash
# install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh
```

No separate install step after that — `uv run` reads `pyproject.toml` and
creates the environment automatically on first run.

## Usage

```bash
# from a recorded video file
uv run people-counter --source data/pedestrian.mp4 --output out/annotated.mp4

# from a live camera stream (RTSP/HTTP URL) — same code, different source
uv run people-counter --source rtsp://user:pass@camera-ip/stream --output out/annotated.mp4

# from a webcam, for quick local testing
uv run people-counter --source 0 --show

# quick spot-check on the first 100 frames of a long clip
uv run people-counter --source data/pedestrian.mp4 --max-frames 100
```

`uv run python -m people_counter --source ...` is equivalent.

### Flags

| Flag                 | Purpose                                                                                                                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--source`           | Required. Video file path, RTSP/HTTP URL, or webcam index.                                                                                                       |
| `--output`           | Annotated video path (default `out/annotated.mp4`). Parent directories are created automatically.                                                                |
| `--line X1 Y1 X2 Y2` | Counting line in pixels. **Set this per camera** — perpendicular to the walking direction, across the actual gate. Defaults to a horizontal line across the middle. |
| `--in-direction`     | `negative-to-positive` (default) or `positive-to-negative`. Flip if a test run shows IN/OUT swapped.                                                             |
| `--conf`             | Detection confidence threshold (default `0.35`). Raise for fewer false positives, lower to catch more people.                                                    |
| `--imgsz`            | Inference resolution (model default is 640). Raise to `1280`+ on high-resolution wide shots where people are small — costs speed.                                |
| `--model`            | Ultralytics weights (default `models/yolov8n.pt`, auto-downloaded on first run). `yolov8s/m/l/x.pt` trade speed for accuracy.                                                                         |
| `--max-frames N`     | Stop after N frames — fast accuracy spot-check on a long clip.                                                                                                   |
| `--progress-interval`| Print running counts every N frames (default `30`).                                                                                                              |
| `--show`             | Display the annotated video live while processing (press `q` to stop).                                                                                           |

### Output

- Annotated video with bounding boxes, track IDs, the counting line, and a
  running IN/OUT/NET readout. Overlay sizes scale with the frame, so 720p and
  4K footage are both legible.
- Running counts on stdout, final IN/OUT/NET totals on completion.
- Exit code `0` on success, `1` on an unusable source/output, `130` on Ctrl-C.

## Project layout

```
src/people_counter/
├── cli.py                   # argument parsing, validation, reporting
├── config.py                # AppConfig + defaults (single source of truth)
├── pipeline.py              # orchestration: frames -> tracking -> counting -> writing
├── detection.py             # PersonTracker protocol + YOLO/ByteTrack implementation
├── counting.py              # LineCrossingCounter, immutable Counts snapshots
├── geometry.py              # Line / BoundingBox value objects, side-of-line maths
├── rendering.py             # all OpenCV drawing
└── video.py                 # VideoStream / AnnotatedVideoWriter context managers
tests/                       # pytest suite (no model weights or footage required)
data/                        # input footage (git-ignored)
out/                         # annotated videos and other artifacts (git-ignored)
models/                      # YOLO weights, auto-downloaded here (git-ignored)
```

`data/`, `out/`, and `models/` are tracked as empty directories only; their
contents stay out of git — clips and weights are large and reproducible.

The layers are deliberately separable: `detection.PersonTracker` is a
`Protocol`, so a different detector or tracker drops in without touching the
counting, rendering, or CLI code, and `pipeline.run()` accepts an injected
tracker. Publishing occupancy over WebSocket/MQTT is a new module plus a
callback on `run()`, not a rewrite.

## Development

```bash
uv sync --extra dev      # install runtime + test dependencies
uv run pytest            # full suite, no weights or footage needed
uv run pytest --cov=src  # with coverage
```

Tests stub the tracker and generate a synthetic clip, so the suite runs in
under a second and never downloads model weights.

## Validating a new camera

1. Record a short clip (1–2 minutes) from the target camera.
2. Set `--line` to match the actual gate/corridor in that footage.
3. Run with `--max-frames` first, then manually count a handful of people
   entering/exiting in the same clip and compare with the printed totals.
4. Adjust `--line`, `--conf`, `--imgsz`, and `--in-direction` until counts
   line up. Dense/rush-hour footage may need a larger model (`yolov8s.pt`+)
   and a higher `--imgsz` — expect accuracy to degrade under heavy occlusion.
5. Once a file-based test is accurate, point `--source` at the live camera
   URL — no other code changes needed.

### Known accuracy limits

Centroid line-crossing counts every sign flip, so a person loitering on the
gate can be double-counted, and ByteTrack ID switches under occlusion cost
counts in both directions. On dense crowd footage at default `--imgsz 640`,
a 4K frame is letterboxed down far enough that distant people go undetected;
raise `--imgsz` before trusting the totals.

## Roadmap

- [x] Detection + tracking + line-crossing count on a video file or live camera
- [ ] Publish per-camera/per-zone occupancy over WebSocket/MQTT
- [ ] 3D station model (Godot) subscribing to live occupancy data
- [ ] Per-zone density visualization / flow arrows in the 3D view
- [ ] Multi-camera calibration and periodic occupancy true-up
