"""Machine-readable API errors.

Clients localize by `code`; `message` stays English for logs, curl, and
anything without a translation catalogue.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, **params: Any) -> None:
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message, "params": params},
        )


def unsupported_file_type(suffix: str) -> ApiError:
    return ApiError(400, "unsupported_file_type", f"unsupported file type '{suffix}'", suffix=suffix)


def unreadable_video(reason: str) -> ApiError:
    return ApiError(400, "unreadable_video", f"unreadable video: {reason}", reason=reason)


def video_not_found() -> ApiError:
    return ApiError(404, "video_not_found", "video not found")


def frame_unreadable(reason: str) -> ApiError:
    return ApiError(400, "frame_unreadable", reason)


def job_not_found() -> ApiError:
    return ApiError(404, "job_not_found", "job not found")


def preview_not_ready() -> ApiError:
    return ApiError(404, "preview_not_ready", "no preview frame yet")


def job_already_finished(status: str) -> ApiError:
    return ApiError(409, "job_already_finished", f"job already {status}", status=status)
