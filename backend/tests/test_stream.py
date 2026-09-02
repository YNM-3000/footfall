"""WebSocket live updates — what the dashboard actually renders from."""

import pytest
from conftest import wait_for_terminal
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

TERMINAL = {"completed", "failed", "cancelled"}


def collect_until_terminal(websocket, limit: int = 200) -> list[dict]:
    messages = []
    for _ in range(limit):
        message = websocket.receive_json()
        messages.append(message)
        if message["type"] == "status" and message["status"] in TERMINAL:
            return messages
    raise AssertionError("never received a terminal status")


def test_stream_sends_snapshot_then_live_updates(client: TestClient, uploaded_video: dict):
    job = client.post(
        "/api/jobs",
        json={"video_id": uploaded_video["id"], "line": [0, 120, 320, 120]},
    ).json()

    with client.websocket_connect(f"/api/jobs/{job['id']}/stream") as websocket:
        messages = collect_until_terminal(websocket)

    kinds = [message["type"] for message in messages]
    assert kinds[0] == "snapshot", "a late subscriber must start from current truth"
    assert "progress" in kinds
    assert messages[-1]["status"] == "completed"

    crossings = [m for m in messages if m["type"] == "crossing"]
    assert len(crossings) == 1
    assert crossings[0]["direction"] == "in"

    final_progress = [m for m in messages if m["type"] == "progress"][-1]
    assert final_progress["counts"] == {"entries": 1, "exits": 0, "net": 1}


def test_stream_for_unknown_job_is_refused(client: TestClient):
    """Closed before accept, so the client never sees a live socket."""
    with pytest.raises(WebSocketDisconnect) as refusal, client.websocket_connect("/api/jobs/nope/stream"):
        pass

    assert refusal.value.code == 4404


def test_snapshot_reflects_a_job_that_already_finished(client: TestClient, uploaded_video: dict):
    job = client.post(
        "/api/jobs",
        json={"video_id": uploaded_video["id"], "line": [0, 120, 320, 120]},
    ).json()
    wait_for_terminal(client, job["id"])

    with client.websocket_connect(f"/api/jobs/{job['id']}/stream") as websocket:
        snapshot = websocket.receive_json()

    assert snapshot["type"] == "snapshot"
    assert snapshot["job"]["status"] == "completed"
    assert snapshot["job"]["counts"]["entries"] == 1
