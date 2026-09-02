"""Service configuration, resolved from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# settings.py -> people_counter_api -> src -> backend -> repo root
DEFAULT_ROOT = Path(__file__).resolve().parents[3]
ENV_PREFIX = "PEOPLE_COUNTER_"
# One job saturates several cores already; the default keeps a laptop usable.
DEFAULT_MAX_CONCURRENT_JOBS = 2
DEFAULT_PREVIEW_WIDTH = 720


@dataclass(frozen=True)
class Settings:
    uploads_dir: Path
    database_path: Path
    model: str
    max_concurrent_jobs: int = DEFAULT_MAX_CONCURRENT_JOBS
    preview_width: int = DEFAULT_PREVIEW_WIDTH
    allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    @classmethod
    def from_env(cls, root: Path | None = None) -> Settings:
        base = root or Path(os.environ.get(f"{ENV_PREFIX}ROOT", DEFAULT_ROOT))
        return cls(
            uploads_dir=Path(os.environ.get(f"{ENV_PREFIX}UPLOADS", base / "data" / "uploads")),
            database_path=Path(os.environ.get(f"{ENV_PREFIX}DB", base / "data" / "people_counter.db")),
            model=os.environ.get(f"{ENV_PREFIX}MODEL", str(base / "models" / "yolov8n.pt")),
            max_concurrent_jobs=int(os.environ.get(f"{ENV_PREFIX}MAX_JOBS", DEFAULT_MAX_CONCURRENT_JOBS)),
        )

    def ensure_directories(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
