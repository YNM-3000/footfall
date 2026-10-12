# Security Policy

## Supported versions

Only the latest commit on `main` gets security fixes.

## Reporting a vulnerability

Please **don't open a public issue**. Report it privately through
[GitHub security advisories](https://github.com/YNM-3000/footfall/security/advisories/new)
and include:

- what an attacker can do,
- steps or a request that reproduces it,
- the commit you tested.

You should get a reply within 7 days. Once a fix is merged, the advisory is
published with credit to you unless you'd rather stay anonymous.

## Deployment model: read this before exposing the service

The API has **no authentication and no authorization**. Anyone who can reach
it can upload videos, start CPU-heavy jobs, read every stored crossing event,
and view frames from the footage.

It's built to run on a trusted machine or a trusted network:

- The API binds to `127.0.0.1` by default. Docker Compose publishes it on
  `127.0.0.1:8000` only.
- Don't set `FOOTFALL_HOST=0.0.0.0` or publish the port publicly
  unless a reverse proxy in front of it handles authentication and TLS.
- Camera URLs passed to `--source` often contain credentials
  (`rtsp://user:pass@...`). Keep them out of shell history and shared
  scripts, for example by using environment variables.
- Uploaded footage and the SQLite database live under `data/`. Treat that
  directory as sensitive: it can contain images of identifiable people.

Missing authentication on its own isn't a vulnerability in this project, because
the design assumes a trusted network. Ways to escape that boundary are
vulnerabilities, for example path traversal through uploads or code execution
through a crafted video. Please report those.
