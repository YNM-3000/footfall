from pathlib import Path

from conftest import CLIP_FPS, FRAME_COUNT, FRAME_HEIGHT, FRAME_WIDTH
from fastapi.testclient import TestClient


def test_upload_returns_probed_geometry(uploaded_video: dict):
    assert uploaded_video["width"] == FRAME_WIDTH
    assert uploaded_video["height"] == FRAME_HEIGHT
    assert uploaded_video["fps"] == CLIP_FPS
    assert uploaded_video["frame_count"] == FRAME_COUNT


def test_uploaded_file_is_listed(client: TestClient, uploaded_video: dict):
    listed = client.get("/api/videos").json()

    assert [video["id"] for video in listed] == [uploaded_video["id"]]


def test_unsupported_file_type_is_rejected(client: TestClient):
    response = client.post("/api/videos", files={"file": ("notes.txt", b"hello", "text/plain")})

    assert response.status_code == 400


def test_unreadable_video_is_rejected_and_not_kept(client: TestClient, tmp_path: Path):
    response = client.post("/api/videos", files={"file": ("broken.mp4", b"not a video", "video/mp4")})

    assert response.status_code == 400
    assert list((tmp_path / "uploads").glob("*.mp4")) == []


def test_frame_endpoint_returns_a_jpeg(client: TestClient, uploaded_video: dict):
    """The dashboard draws the counting line on this still."""
    response = client.get(f"/api/videos/{uploaded_video['id']}/frame.jpg")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8")


def test_frame_endpoint_404s_for_unknown_video(client: TestClient):
    assert client.get("/api/videos/nope/frame.jpg").status_code == 404
