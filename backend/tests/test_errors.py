"""Errors carry a stable code so clients can translate them."""

from fastapi.testclient import TestClient


def test_unsupported_file_type_reports_a_code(client: TestClient):
    response = client.post("/api/videos", files={"file": ("notes.txt", b"hi", "text/plain")})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "unsupported_file_type"
    assert response.json()["detail"]["params"]["suffix"] == ".txt"


def test_unreadable_video_reports_a_code(client: TestClient):
    response = client.post("/api/videos", files={"file": ("broken.mp4", b"nope", "video/mp4")})

    assert response.json()["detail"]["code"] == "unreadable_video"


def test_missing_video_reports_a_code(client: TestClient):
    response = client.get("/api/videos/nope/frame.jpg")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "video_not_found"


def test_missing_job_reports_a_code(client: TestClient):
    assert client.get("/api/jobs/nope").json()["detail"]["code"] == "job_not_found"


def test_preview_before_first_frame_reports_a_code(client: TestClient, uploaded_video: dict):
    job = client.post("/api/jobs", json={"video_id": uploaded_video["id"]}).json()

    response = client.get(f"/api/jobs/{job['id']}/preview.jpg")

    if response.status_code == 404:
        assert response.json()["detail"]["code"] == "preview_not_ready"


def test_cancelling_finished_job_reports_a_code(client: TestClient, uploaded_video: dict):
    from conftest import wait_for_terminal

    job = client.post("/api/jobs", json={"video_id": uploaded_video["id"]}).json()
    wait_for_terminal(client, job["id"])

    response = client.post(f"/api/jobs/{job['id']}/cancel")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "job_already_finished"
