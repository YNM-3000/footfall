# Contributing

Thanks for helping. Bug reports, accuracy findings from real cameras, and pull
requests are all welcome.

## Setup

You need Python ≥ 3.10, [`uv`](https://github.com/astral-sh/uv), and Node.js 20+.

```bash
uv sync --group dev              # core + backend + test tooling
cd frontend && npm ci            # dashboard
```

## Before you open a pull request

These are the same checks CI runs:

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run pyright

cd frontend
npm run lint
npm run build
```

The Python suite stubs the tracker and generates synthetic clips, so it needs
no model weights or footage and runs in about a second. If you change
detection, tracking, or counting, also run the CLI on a real clip and say in
the PR how the counts compared with a manual count.

## Guidelines

- **Respect the layering.** `core/` knows nothing about HTTP, `backend/` uses
  `core/` like any other client would, and `frontend/` talks only to the API.
  See [Project layout](README.md#project-layout).
- **Add tests** for new behaviour in `core/tests` or `backend/tests`.
- **Dashboard strings go in both catalogues**, `frontend/src/i18n/locales/zh.ts`
  and `en.ts`. The build fails if a key is missing.
- **Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat: …`, `fix: …`, `refactor: …`, `docs: …`, `test: …`, `chore: …`.
- **Don't commit footage, model weights, or databases.** `data/`, `out/`, and
  `models/` are git-ignored on purpose. If an issue needs a clip, describe the
  scene or share a frame with faces blurred.

## License

By contributing, you agree that your contributions are licensed under the
[GNU AGPL-3.0](LICENSE), the same license as the project.
