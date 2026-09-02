from conftest import FRAME_COUNT, wait_for_terminal
from fastapi.testclient import TestClient


def start_job(client: TestClient, video_id: str, **overrides) -> dict:
    payload = {"video_id": video_id, "line": [0, 120, 320, 120], **overrides}
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_job_runs_and_counts_the_crossing(client: TestClient, uploaded_video: dict):
    job = start_job(client, uploaded_video["id"])

    finished = wait_for_terminal(client, job["id"])

    assert finished["status"] == "completed"
    assert finished["counts"] == {"entries": 1, "exits": 0, "net": 1}
    assert finished["processed_frames"] == FRAME_COUNT
    assert finished["error"] is None


def test_crossings_are_persisted_as_events(client: TestClient, uploaded_video: dict):
    """Totals are derived; the events are the durable record."""
    job = start_job(client, uploaded_video["id"])
    wait_for_terminal(client, job["id"])

    crossings = client.get(f"/api/jobs/{job['id']}/crossings").json()

    assert len(crossings) == 1
    assert crossings[0]["direction"] == "in"
    assert crossings[0]["track_id"] == 1
    assert crossings[0]["timestamp"] > 0


def test_in_direction_flips_the_tally(client: TestClient, uploaded_video: dict):
    job = start_job(client, uploaded_video["id"], in_direction="positive-to-negative")

    finished = wait_for_terminal(client, job["id"])

    assert finished["counts"] == {"entries": 0, "exits": 1, "net": -1}


def test_frame_stride_reduces_processed_frames(client: TestClient, uploaded_video: dict):
    job = start_job(client, uploaded_video["id"], frame_stride=2)

    finished = wait_for_terminal(client, job["id"])

    assert finished["total_frames"] == FRAME_COUNT // 2
    assert finished["processed_frames"] == FRAME_COUNT // 2


def test_job_config_is_recorded_for_reproducibility(client: TestClient, uploaded_video: dict):
    job = start_job(client, uploaded_video["id"], confidence=0.5, imgsz=640)

    finished = wait_for_terminal(client, job["id"])

    assert finished["config"]["confidence"] == 0.5
    assert finished["config"]["imgsz"] == 640
    assert finished["config"]["line"] == [0, 120, 320, 120]


def test_job_for_unknown_video_is_404(client: TestClient):
    assert client.post("/api/jobs", json={"video_id": "nope"}).status_code == 404


def test_degenerate_line_is_rejected(client: TestClient, uploaded_video: dict):
    response = client.post(
        "/api/jobs",
        json={"video_id": uploaded_video["id"], "line": [10, 10, 10, 10]},
    )

    assert response.status_code == 422


def test_cancelling_a_finished_job_conflicts(client: TestClient, uploaded_video: dict):
    job = start_job(client, uploaded_video["id"])
    wait_for_terminal(client, job["id"])

    response = client.post(f"/api/jobs/{job['id']}/cancel")

    assert response.status_code == 409


def test_preview_is_available_and_is_a_jpeg(client: TestClient, uploaded_video: dict):
    job = start_job(client, uploaded_video["id"])
    wait_for_terminal(client, job["id"])

    response = client.get(f"/api/jobs/{job['id']}/preview.jpg")

    assert response.status_code == 200
    assert response.content.startswith(b"\xff\xd8")


def test_unknown_job_endpoints_are_404(client: TestClient):
    assert client.get("/api/jobs/nope").status_code == 404
    assert client.get("/api/jobs/nope/crossings").status_code == 404
    assert client.get("/api/jobs/nope/preview.jpg").status_code == 404
