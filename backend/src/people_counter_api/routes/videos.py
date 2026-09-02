"""Video upload and still-frame access."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from people_counter.video import VideoSourceError, VideoStream, grab_frame

from ..dependencies import StateDep
from ..preview import encode_jpeg
from ..schemas import VideoOut
from ..storage import VideoRecord, utc_now

router = APIRouter(prefix="/api/videos", tags=["videos"])

ALLOWED_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}

UploadedVideo = Annotated[UploadFile, File(description="The recording to count people in.")]
FrameIndex = Annotated[int, Query(ge=0, description="Frame to grab, for placing the counting line.")]


@router.post("", response_model=VideoOut, status_code=201)
async def upload_video(state: StateDep, file: UploadedVideo) -> VideoOut:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"unsupported file type '{suffix or file.filename}'")

    video_id = uuid.uuid4().hex
    destination = state.settings.uploads_dir / f"{video_id}{suffix}"
    state.settings.ensure_directories()
    # Streamed to disk: uploads are hundreds of megabytes and must not be
    # buffered in memory.
    with destination.open("wb") as sink:
        shutil.copyfileobj(file.file, sink)

    try:
        geometry = _probe(destination)
    except VideoSourceError as error:
        destination.unlink(missing_ok=True)
        raise HTTPException(400, f"unreadable video: {error}") from error

    record = VideoRecord(
        id=video_id,
        filename=file.filename or destination.name,
        path=destination,
        width=geometry.width,
        height=geometry.height,
        fps=geometry.fps,
        frame_count=geometry.frame_count,
        created_at=utc_now(),
    )
    state.database.add_video(record)
    return _to_schema(record)


@router.get("", response_model=list[VideoOut])
async def list_videos(state: StateDep) -> list[VideoOut]:
    return [VideoOut(**dict(row)) for row in state.database.list_videos()]


@router.get("/{video_id}/frame.jpg")
async def video_frame(video_id: str, state: StateDep, index: FrameIndex = 0) -> Response:
    row = state.database.get_video(video_id)
    if row is None:
        raise HTTPException(404, "video not found")
    try:
        frame = grab_frame(row["path"], index)
    except VideoSourceError as error:
        raise HTTPException(400, str(error)) from error
    return Response(
        encode_jpeg(frame, state.settings.preview_width),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _to_schema(record: VideoRecord) -> VideoOut:
    return VideoOut(
        id=record.id,
        filename=record.filename,
        width=record.width,
        height=record.height,
        fps=record.fps,
        frame_count=record.frame_count,
        created_at=record.created_at,
    )


def _probe(path: Path):
    with VideoStream(str(path)) as stream:
        return stream.geometry
