"""Fixtures: a real API on a temp directory, with detection stubbed out."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from footfall.detection import TrackedPerson
from footfall.geometry import BoundingBox
from footfall_api.app import create_app
from footfall_api.settings import Settings

FRAME_WIDTH = 320
FRAME_HEIGHT = 240
FRAME_COUNT = 12
CLIP_FPS = 10.0
JOB_TIMEOUT_SECONDS = 15.0
TERMINAL = {"completed", "failed", "cancelled"}


class WalkingPersonTracker:
    """One person walking top-to-bottom, crossing the midline exactly once."""

    def __init__(self) -> None:
        self._frame = 0

    def track(self, frame: np.ndarray) -> tuple[TrackedPerson, ...]:
        y = self._frame * (FRAME_HEIGHT / FRAME_COUNT)
        self._frame += 1
        return (TrackedPerson(track_id=1, box=BoundingBox(100.0, y, 140.0, y + 20.0)),)


@pytest.fixture
def clip(tmp_path: Path) -> Path:
    path = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter.fourcc(*"mp4v"), CLIP_FPS, (FRAME_WIDTH, FRAME_HEIGHT)
    )
    assert writer.isOpened()
    for _ in range(FRAME_COUNT):
        writer.write(np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8))
    writer.release()
    return path


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        uploads_dir=tmp_path / "uploads",
        database_path=tmp_path / "db.sqlite",
        model="unused-because-detection-is-stubbed",
        max_concurrent_jobs=1,
        preview_width=160,
    )
    app = create_app(settings, tracker_factory=lambda _config: WalkingPersonTracker())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def uploaded_video(client: TestClient, clip: Path) -> dict:
    with clip.open("rb") as handle:
        response = client.post("/api/videos", files={"file": ("clip.mp4", handle, "video/mp4")})
    assert response.status_code == 201, response.text
    return response.json()


def wait_for_terminal(client: TestClient, job_id: str) -> dict:
    """Poll until the job finishes — it runs on a worker thread."""
    deadline = time.monotonic() + JOB_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in TERMINAL:
            return job
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not finish within {JOB_TIMEOUT_SECONDS}s")
