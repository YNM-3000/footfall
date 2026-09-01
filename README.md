# Subway People Counter

Camera-based people counting for a subway station: detect and track people
via computer vision, count entries/exits across a virtual line, and (next
phase) feed the resulting occupancy numbers into a real-time 3D
visualization of the station.

## How it works

1. **Detection** — [YOLOv8](https://github.com/ultralytics/ultralytics)
   (`yolov8n.pt`) finds every person in each video frame.
2. **Tracking** — ByteTrack (built into `ultralytics`) assigns a persistent
   ID to each detected person across frames.
3. **Counting** — a virtual line is drawn across the frame (e.g. a gate or
   corridor). When a tracked person's centroid crosses it, an IN or OUT
   counter increments depending on direction.
4. **Occupancy** — running total = IN − OUT.

This repo currently covers step 1–4 (people_counter.py) as a **minimal
path validation**: proving detection → tracking → counting works
end-to-end on a video file or live camera stream, before wiring it into
the 3D station visualization.

## Requirements

- Python ≥ 3.10
- [`uv`](https://github.com/astral-sh/uv) for dependency management

## Setup

```bash
# install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh
```

No separate install step needed after that — `uv run` reads
`pyproject.toml` and creates the environment automatically on first run.

## Usage

```bash
# from an uploaded/recorded video file
uv run people_counter.py --source path/to/video.mp4 --output annotated.mp4

# from a live camera stream (RTSP/HTTP URL) — same code, different source
uv run people_counter.py --source rtsp://user:pass@camera-ip/stream --output annotated.mp4

# from a webcam, for quick local testing
uv run people_counter.py --source 0
```

### Important flags

| Flag                 | Purpose                                                                                                                                                                                                                                                            |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--line X1 Y1 X2 Y2` | Pixel coordinates of the counting line. **Set this per camera** — draw it perpendicular to the direction people walk, across the actual gate/corridor. Defaults to a horizontal line through the frame's vertical middle, which is unlikely to match your footage. |
| `--in-direction`     | `negative-to-positive` (default) or `positive-to-negative`. Flip this if a test run shows IN/OUT counts swapped for your camera's orientation.                                                                                                                     |
| `--conf`             | Detection confidence threshold (default `0.35`). Raise it if you're getting false-positive detections; lower it if people are being missed.                                                                                                                        |
| `--model`            | Ultralytics weights file. Defaults to `yolov8n.pt` (nano — fastest, good for CPU testing). Larger variants (`yolov8s/m/l/x.pt`) trade speed for accuracy.                                                                                                          |
| `--show`             | Display the annotated video live in a window while it processes.                                                                                                                                                                                                   |

### Output

- An annotated video (`--output`, default `annotated_output.mp4`) with
  bounding boxes, track IDs, the counting line, and a running
  IN/OUT/NET readout — use this to eyeball accuracy against a manual
  count on a short clip.
- Live counts printed to stdout every 30 frames.
- Final IN/OUT/NET totals printed on completion.

## Validating a new camera

1. Record or grab a short clip (1–2 minutes) from the target camera.
2. Set `--line` to match the actual gate/corridor in that footage.
3. Run the script, then manually count a handful of people entering/exiting
   in the same clip and compare against the printed totals.
4. Adjust `--line` placement, `--conf`, and `--in-direction` until the
   counts line up. Dense/rush-hour footage may need a larger model
   (`yolov8s.pt` or above) or additional tuning — expect count accuracy to
   degrade under heavy occlusion.
5. Once a file-based test is accurate, point `--source` at the live camera
   URL — no other code changes needed.

## Roadmap

- [x] Minimal path validation: detection + tracking + line-crossing count
      on a video file or live camera
- [ ] Publish per-camera/per-zone occupancy over WebSocket/MQTT
- [ ] 3D station model (Godot) subscribing to live occupancy data
- [ ] Per-zone density visualization / flow arrows in the 3D view
- [ ] Multi-camera calibration and periodic occupancy true-up
