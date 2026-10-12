"""Wire format between the API and the dashboard."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from footfall.counting import InDirection

MIN_IMGSZ = 32


class VideoOut(BaseModel):
    id: str
    filename: str
    width: int
    height: int
    fps: float
    frame_count: int | None
    created_at: str


class JobRequest(BaseModel):
    """Everything an operator configures for one counting run."""

    video_id: str
    line: tuple[float, float, float, float] | None = None
    in_direction: InDirection = InDirection.NEGATIVE_TO_POSITIVE
    confidence: float = Field(default=0.35, gt=0, lt=1)
    imgsz: int | None = Field(default=1280, ge=MIN_IMGSZ)
    frame_stride: int = Field(default=1, ge=1)
    max_frames: int | None = Field(default=None, ge=1)

    @field_validator("line")
    @classmethod
    def reject_zero_length_line(cls, value):
        if value is not None and value[:2] == value[2:]:
            raise ValueError("counting line must have two distinct endpoints")
        return value


class CountsOut(BaseModel):
    entries: int
    exits: int
    net: int


class JobOut(BaseModel):
    id: str
    video_id: str
    status: str
    counts: CountsOut
    processed_frames: int
    total_frames: int | None
    error: str | None
    created_at: str
    finished_at: str | None
    config: dict

    @property
    def progress(self) -> float | None:
        if not self.total_frames:
            return None
        return min(1.0, self.processed_frames / self.total_frames)


class CrossingOut(BaseModel):
    track_id: int
    direction: str
    frame_index: int
    timestamp: float
