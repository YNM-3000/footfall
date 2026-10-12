# Footfall

[![CI](https://github.com/YNM-3000/footfall/actions/workflows/ci.yml/badge.svg)](https://github.com/YNM-3000/footfall/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

English | [简体中文](README.zh-CN.md)

Camera-based people counting: detect and track people via computer vision,
count entries and exits across a virtual line, and watch the numbers live in
a browser.

Today it counts uploaded recordings. It is built to grow into continuous
monitoring of several live camera streams — see
[Built for live streams](#built-for-live-streams).

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

Three layers in a uv workspace. Each depends only on the one below it.

```
core/                        # the counting library — no web, no HTTP
├── src/people_counter/
│   ├── cli.py               # command line entry point
│   ├── config.py            # AppConfig + defaults (single source of truth)
│   ├── pipeline.py          # frames -> tracking -> counting -> events
│   ├── detection.py         # PersonTracker protocol + YOLO/ByteTrack
│   ├── counting.py          # LineCrossingCounter, Counts, CrossingEvent
│   ├── geometry.py          # Line / BoundingBox, side-of-line maths
│   ├── rendering.py         # all OpenCV drawing
│   └── video.py             # VideoStream / writer / grab_frame
└── tests/

backend/                     # FastAPI service over the library
├── src/people_counter_api/
│   ├── app.py               # application factory
│   ├── routes/              # videos, jobs, WebSocket stream
│   ├── jobs.py              # JobRunner: pipeline execution off the event loop
│   ├── storage.py           # SQLite: videos, jobs, crossing events
│   ├── bus.py               # fan-out of live updates to dashboards
│   └── preview.py           # JPEG encoding for browser previews
└── tests/

frontend/                    # React + Vite dashboard
└── src/
    ├── api/                 # typed client and wire types
    ├── i18n/                # zh (default) + en catalogues, type-checked
    ├── hooks/useJobStream   # WebSocket subscription with reconnect
    └── components/          # line editor, counts readout, feed, history

data/  out/  models/         # footage, artifacts, weights (git-ignored)
```

The seams are deliberate. `detection.PersonTracker` is a `Protocol` and
`pipeline.run()` takes an injected tracker, so a different detector drops in
— and the whole test suite runs without model weights. The backend consumes
the library the same way any other client would, so a publisher for another
transport is a new module, not a rewrite.

## The dashboard

Upload a recording, drag the counting line onto the frame where people
actually walk, and watch counts arrive while it processes.

```bash
uv sync                              # installs core + backend
uv run people-counter-api            # http://127.0.0.1:8000

cd frontend && npm install
npm run dev                          # http://localhost:5173, proxies /api
```

For a single-origin deployment, `npm run build` writes `frontend/dist`,
which the API serves at `/` when present.

### Languages

The dashboard ships in Chinese (default) and English; the switcher sits in the
masthead and the choice persists per browser. To change the default, set
`DEFAULT_LANGUAGE` in `frontend/src/i18n/index.ts`.

Adding a locale means one file:

```ts
// frontend/src/i18n/locales/ja.ts
import type { zh } from "./zh";
export const ja: typeof zh = { /* the compiler lists every missing key */ };
```

`zh.ts` types every other catalogue, so a missing or misspelled key is a build
error rather than a blank label in production. API errors carry a stable
`code` (`unsupported_file_type`, `job_not_found`, …) which the client
translates, falling back to the server's English message for anything not yet
in the catalogue — so failures are localized too, not just chrome.

### API

| Endpoint | Purpose |
| -------- | ------- |
| `POST /api/videos` | Upload a recording; returns probed geometry |
| `GET /api/videos/{id}/frame.jpg` | Still frame, for placing the counting line |
| `POST /api/jobs` | Start counting with a line and settings |
| `GET /api/jobs/{id}` | Status, progress, running totals |
| `GET /api/jobs/{id}/crossings` | Every individual crossing event |
| `GET /api/jobs/{id}/preview.jpg` | Latest annotated frame |
| `POST /api/jobs/{id}/cancel` | Stop a running job |
| `WS /api/jobs/{id}/stream` | Snapshot, then live progress and crossings |

The socket sends a snapshot on connect, so a browser that joins late — or
reconnects — starts from the truth rather than from whatever happens next.

## Built for live streams

Counting a file and monitoring a camera differ in ways that are painful to
retrofit, so the core already accounts for them:

- **Events, not totals, are the durable output.** Every crossing is stored
  individually (`track_id`, direction, frame, timestamp). Totals are derived,
  so they can be recomputed after a line or threshold changes.
- **Video output is optional.** `output=None` skips writing entirely; a camera
  that runs for days should not produce a forever-growing file.
- **Frame sampling.** `frame_stride` keeps decoding real time while inference
  runs slower, which is the lever that lets one host serve several cameras.
- **Bounded state.** `LineCrossingCounter.forget()` prunes departed tracks, so
  per-track memory does not grow without bound.
- **Cancellable runs.** `should_stop` lets a supervisor shut a worker down
  cleanly. A live camera is simply a job that never finishes.

Still to build for live cameras: RTSP reconnect with latest-frame-wins
(a live stream must *drop* backlog, never queue it, or each camera drifts
further behind real time), and moving `JobRunner` from threads to processes
or separate hosts.

### Throughput

Measured on an Apple Silicon Mac (CPU, `yolov8n`, per stream):

| `imgsz` | Throughput | People detected per frame |
| ------- | ---------- | ------------------------- |
| 640 (model default) | 17.3 fps | 3.8 |
| 1280 | 11.0 fps | 23.3 |

On dense 4K footage the default resolution misses most of the crowd, so the
dashboard defaults to 1280. At ~11 fps, one CPU host handles roughly two
cameras at 5 fps each; more than that wants a GPU.

## Development

```bash
uv sync --group dev              # runtime + test dependencies
uv run pytest                    # core + backend, no weights or footage
uv run pytest --cov=core/src --cov=backend/src
uv run ruff check . && uv run ruff format --check .
uv run pyright                   # type check (config in pyrightconfig.json)

cd frontend
npm run build                    # type-check and bundle
npm run e2e                      # drives the real UI in Chromium
```

Tests stub the tracker and generate synthetic clips, so the suite runs in
under a second and never downloads model weights. The e2e smoke test needs a
running API and a real video (`VIDEO=../data/pedestrian.mp4`).

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

## Responsible use

This project counts people. It doesn't identify them. It does no face
recognition and no re-identification across cameras or sessions, and a track ID
is only a per-run number. The durable output is anonymous crossing events: a
direction, a frame number, and a timestamp.

The footage itself is personal data, though. In many jurisdictions (GDPR in
the EU, PIPL in China, and others) recording people, even only to count them,
comes with obligations. Before you point this at a real camera:

- Check the local rules for video recording, and put up signage where it's
  required.
- Keep only what you need. Counting doesn't require keeping footage. Delete
  uploads and annotated videos under `data/` and `out/` once you've validated
  a camera, and run live cameras with no video output.
- Restrict access to the dashboard and the `data/` directory. See
  [Security](#security).

Don't use this project to track specific individuals, to profile people, or
to monitor anyone covertly.

## Security

The API has **no authentication**. It binds to `127.0.0.1` by default, and
it's meant for a trusted machine or network. If you expose it beyond that,
put it behind a reverse proxy that handles authentication and TLS. See
[SECURITY.md](SECURITY.md) for the deployment model and for how to report
vulnerabilities privately.

## Roadmap

- [x] Detection + tracking + line-crossing counting (CLI)
- [x] Counting API with crossing events, live updates, and persistence
- [x] Dashboard: upload, place the line on the frame, watch counts live
- [ ] Camera registry: RTSP sources with reconnect and health, replacing
      upload-only input
- [ ] Multi-camera tile grid with per-camera occupancy
- [ ] Occupancy baseline and daily true-up (net drifts over long runs)
- [ ] History charts from stored crossing events
- [ ] Process- or host-level workers, and GPU inference

## Contributing

Issues and pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md)
covers setup, the checks CI runs, and the project conventions.

## License

Footfall is licensed under the [GNU Affero General Public License v3.0](LICENSE).

The license follows from the detector. Footfall depends on
[Ultralytics](https://github.com/ultralytics/ultralytics), and both the
library and its YOLO weights are AGPL-3.0. So if you modify this project and
let people use it over a network, for example a hosted counting dashboard,
you must offer them the source of your modified version. If you need
different terms, you'll need a commercial license from Ultralytics, or you'll
need to swap in a detector with a permissive license through the
`detection.PersonTracker` protocol.
