# syntax=docker/dockerfile:1

# --- Dashboard ---------------------------------------------------------------
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- API + counting library ---------------------------------------------------
FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv

# OpenCV's runtime libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first, so source edits don't reinstall torch.
COPY pyproject.toml uv.lock ./
COPY core/pyproject.toml core/pyproject.toml
COPY backend/pyproject.toml backend/pyproject.toml
#
# PyPI's Linux torch wheels bundle ~3.5 GB of CUDA libraries. The default
# TORCH_VARIANT=cpu skips them and installs the matching CPU builds instead;
# build with TORCH_VARIANT=cuda for an NVIDIA GPU host.
ARG TORCH_VARIANT=cpu
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$TORCH_VARIANT" = "cpu" ]; then \
        skip=$(grep -oE '^name = "(torch|torchvision|triton|nvidia-[^"]+)"' uv.lock \
               | cut -d'"' -f2 | sed 's/^/--no-install-package /'); \
        uv sync --frozen --no-dev --no-install-workspace $skip \
        && uv pip install --no-deps --index-url https://download.pytorch.org/whl/cpu \
               "torch==$(grep -A1 '^name = "torch"$' uv.lock | sed -n 's/^version = "\(.*\)"/\1/p')+cpu" \
               "torchvision==$(grep -A1 '^name = "torchvision"$' uv.lock | sed -n 's/^version = "\(.*\)"/\1/p')+cpu"; \
    else \
        uv sync --frozen --no-dev --no-install-workspace; \
    fi

# The workspace members themselves, installed editable without re-syncing:
# a second `uv sync` would swap the CPU torch back for the locked CUDA one.
COPY core/ core/
COPY backend/ backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-deps -e core -e backend

# The API serves the built dashboard from frontend/dist when present.
COPY --from=frontend /build/dist frontend/dist

RUN useradd --create-home --uid 1000 counter \
    && mkdir -p data models out \
    && chown -R counter:counter data models out
USER counter

# The container is the network boundary; compose publishes to localhost only.
ENV PEOPLE_COUNTER_HOST=0.0.0.0 \
    PEOPLE_COUNTER_PORT=8000
EXPOSE 8000

CMD ["footfall-api"]
