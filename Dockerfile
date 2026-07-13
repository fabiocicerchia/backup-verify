# Multi-stage build keeps the final image small.
# NOTE: backup-verify shells out to your container runtime (docker/podman) to
# spin up scratch restore containers, so running it *inside* a container needs
# the host socket mounted. Installing on the host is usually simpler.

# --- build stage ---
FROM python:3.12-slim AS build
WORKDIR /src
COPY . .
RUN pip install --no-cache-dir build && python -m build --wheel

# --- runtime stage ---
FROM python:3.12-slim
WORKDIR /app
RUN useradd -u 10001 -m app
COPY --from=build /src/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
USER app
ENTRYPOINT ["backup-verify"]
