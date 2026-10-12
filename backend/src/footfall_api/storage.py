"""SQLite persistence.

Crossing events are stored individually rather than as running totals: any
total can be recomputed from events, but events cannot be recovered from a
total. That is what makes history, re-tallies after a line change, and
occupancy true-ups possible later.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from footfall.counting import CrossingEvent

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id           TEXT PRIMARY KEY,
    filename     TEXT NOT NULL,
    path         TEXT NOT NULL,
    width        INTEGER NOT NULL,
    height       INTEGER NOT NULL,
    fps          REAL NOT NULL,
    frame_count  INTEGER,
    created_at   TEXT NOT NULL
);

-- A job is one run against one source. A recorded clip finishes; a live
-- camera is simply a job that never does.
CREATE TABLE IF NOT EXISTS jobs (
    id               TEXT PRIMARY KEY,
    video_id         TEXT NOT NULL REFERENCES videos(id),
    status           TEXT NOT NULL,
    config           TEXT NOT NULL,
    entries          INTEGER NOT NULL DEFAULT 0,
    exits            INTEGER NOT NULL DEFAULT 0,
    processed_frames INTEGER NOT NULL DEFAULT 0,
    total_frames     INTEGER,
    error            TEXT,
    created_at       TEXT NOT NULL,
    finished_at      TEXT
);

CREATE TABLE IF NOT EXISTS crossings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL REFERENCES jobs(id),
    track_id    INTEGER NOT NULL,
    direction   TEXT NOT NULL,
    frame_index INTEGER NOT NULL,
    timestamp   REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS crossings_by_job ON crossings(job_id, id);
CREATE INDEX IF NOT EXISTS jobs_by_created ON jobs(created_at DESC);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class VideoRecord:
    id: str
    filename: str
    path: Path
    width: int
    height: int
    fps: float
    frame_count: int | None
    created_at: str


class Database:
    """Thin repository over SQLite.

    A connection is opened per operation: jobs run on worker threads, and
    SQLite connections are not safely shared across them.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path, timeout=30)
        connection.row_factory = sqlite3.Row
        # WAL lets the API read while a worker thread writes events.
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    # -- videos ---------------------------------------------------------
    def add_video(self, record: VideoRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO videos (id, filename, path, width, height, fps, frame_count, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.filename,
                    str(record.path),
                    record.width,
                    record.height,
                    record.fps,
                    record.frame_count,
                    record.created_at,
                ),
            )

    def get_video(self, video_id: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()

    def list_videos(self) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()

    # -- jobs -----------------------------------------------------------
    def add_job(self, job_id: str, video_id: str, config: dict, total_frames: int | None) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO jobs (id, video_id, status, config, total_frames, created_at)"
                " VALUES (?, ?, 'queued', ?, ?, ?)",
                (job_id, video_id, json.dumps(config), total_frames, utc_now()),
            )

    def get_job(self, job_id: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    def list_jobs(self, limit: int = 50) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()

    def set_job_status(self, job_id: str, status: str, *, error: str | None = None) -> None:
        finished_at = utc_now() if status in {"completed", "failed", "cancelled"} else None
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = ?, error = ?, finished_at = ? WHERE id = ?",
                (status, error, finished_at, job_id),
            )

    def set_job_counts(self, job_id: str, *, entries: int, exits: int, processed_frames: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET entries = ?, exits = ?, processed_frames = ? WHERE id = ?",
                (entries, exits, processed_frames, job_id),
            )

    # -- crossings ------------------------------------------------------
    def add_crossing(self, job_id: str, event: CrossingEvent) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO crossings (job_id, track_id, direction, frame_index, timestamp)"
                " VALUES (?, ?, ?, ?, ?)",
                (job_id, event.track_id, str(event.direction), event.frame_index, event.timestamp),
            )

    def list_crossings(self, job_id: str) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM crossings WHERE job_id = ? ORDER BY id", (job_id,)
            ).fetchall()
