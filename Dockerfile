FROM node:22-bookworm-slim@sha256:6c74791e557ce11fc957704f6d4fe134a7bc8d6f5ca4403205b2966bd488f6b3 AS web-build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.11-slim-bookworm@sha256:b18992999dbe963a45a8a4da40ac2b1975be1a776d939d098c647482bcad5cba AS python-build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY requirements.lock ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --require-hashes --target=/runtime/app/site-packages \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      -r requirements.lock
COPY pyproject.toml README.md ./
COPY src/ src/
RUN python -m pip install --target=/runtime/app/site-packages \
      --no-deps --no-build-isolation . \
    && mkdir -p /runtime/models /runtime/audit

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:7d1042ce588ab97019fe95c24ffca7bc5a82ccdac572511d5e09bda4435c89c5 AS runtime
ENV ATTNDIST_ENABLE_DOCS=0 \
    ATTNDIST_CHECKPOINT=/models/best_iou.pt \
    ATTNDIST_OPERATING_MODE=research \
    ATTNDIST_RELEASE_ID=development \
    MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONPATH=/app/site-packages \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --chown=65532:65532 --from=python-build /runtime/ /
COPY --chown=65532:65532 api.py ./
COPY --chown=65532:65532 --from=web-build /build/web/dist/ web/dist/
USER 65532:65532
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=3)"]
CMD ["-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
