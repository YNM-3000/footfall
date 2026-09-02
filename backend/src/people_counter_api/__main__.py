"""`people-counter-api` — run the service."""

from __future__ import annotations

import os

import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def main() -> None:
    uvicorn.run(
        "people_counter_api.app:create_app",
        factory=True,
        host=os.environ.get("PEOPLE_COUNTER_HOST", DEFAULT_HOST),
        port=int(os.environ.get("PEOPLE_COUNTER_PORT", DEFAULT_PORT)),
        reload=bool(os.environ.get("PEOPLE_COUNTER_RELOAD")),
    )


if __name__ == "__main__":
    main()
