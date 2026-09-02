"""Counting jobs: create, inspect, stream, cancel."""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from ..bus import drain
from ..dependencies import StateDep, get_state
from ..errors import job_already_finished, job_not_found, preview_not_ready, video_not_found
from ..jobs import build_config
from ..schemas import CountsOut, CrossingOut, JobOut, JobRequest

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


@router.post("", response_model=JobOut, status_code=201)
async def create_job(request: JobRequest, state: StateDep) -> JobOut:
    video = state.database.get_video(request.video_id)
    if video is None:
        raise video_not_found()

    config = build_config(
        source=video["path"],
        model=state.settings.model,
        line=request.line,
        in_direction=request.in_direction,
        confidence=request.confidence,
        imgsz=request.imgsz,
        frame_stride=request.frame_stride,
        max_frames=request.max_frames,
    )
    job_id = state.runner.submit(config, video_id=video["id"], total_frames=_expected_frames(video, request))
    return _to_schema(state.database.get_job(job_id))


@router.get("", response_model=list[JobOut])
async def list_jobs(state: StateDep) -> list[JobOut]:
    return [_to_schema(row) for row in state.database.list_jobs()]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, state: StateDep) -> JobOut:
    return _to_schema(_require_job(state, job_id))


@router.get("/{job_id}/crossings", response_model=list[CrossingOut])
async def job_crossings(job_id: str, state: StateDep) -> list[CrossingOut]:
    _require_job(state, job_id)
    return [
        CrossingOut(
            track_id=row["track_id"],
            direction=row["direction"],
            frame_index=row["frame_index"],
            timestamp=row["timestamp"],
        )
        for row in state.database.list_crossings(job_id)
    ]


@router.get("/{job_id}/preview.jpg")
async def job_preview(job_id: str, state: StateDep) -> Response:
    _require_job(state, job_id)
    image = state.runner.preview_of(job_id)
    if image is None:
        raise preview_not_ready()
    return Response(image, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/{job_id}/cancel", response_model=JobOut)
async def cancel_job(job_id: str, state: StateDep) -> JobOut:
    row = _require_job(state, job_id)
    if row["status"] in TERMINAL_STATUSES:
        raise job_already_finished(row["status"])
    state.runner.cancel(job_id)
    return _to_schema(state.database.get_job(job_id))


@router.websocket("/{job_id}/stream")
async def job_stream(websocket: WebSocket, job_id: str) -> None:
    """Live counts for one job.

    A snapshot is sent first so a browser that connects late — or reconnects
    — starts from the truth rather than from whatever happens next.
    """
    state = get_state(websocket)
    row = state.database.get_job(job_id)
    if row is None:
        await websocket.close(code=4404, reason="job not found")
        return

    await websocket.accept()
    with state.bus.subscribe(job_id) as queue:
        await websocket.send_json({"type": "snapshot", "job": _to_schema(row).model_dump()})
        try:
            async for message in drain(queue):
                await websocket.send_json(message)
        except WebSocketDisconnect:
            return


def _require_job(state, job_id: str) -> sqlite3.Row:
    row = state.database.get_job(job_id)
    if row is None:
        raise job_not_found()
    return row


def _expected_frames(video: sqlite3.Row, request: JobRequest) -> int | None:
    """How many frames this job will actually process, for the progress bar."""
    total = video["frame_count"]
    if total is None:
        return None
    sampled = -(-total // request.frame_stride)  # ceiling division
    return min(sampled, request.max_frames) if request.max_frames else sampled


def _to_schema(row: sqlite3.Row) -> JobOut:
    return JobOut(
        id=row["id"],
        video_id=row["video_id"],
        status=row["status"],
        counts=CountsOut(
            entries=row["entries"],
            exits=row["exits"],
            net=row["entries"] - row["exits"],
        ),
        processed_frames=row["processed_frames"],
        total_frames=row["total_frames"],
        error=row["error"],
        created_at=row["created_at"],
        finished_at=row["finished_at"],
        config=json.loads(row["config"]),
    )
