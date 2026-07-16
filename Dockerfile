FROM node:22-bookworm-slim@sha256:6c74791e557ce11fc957704f6d4fe134a7bc8d6f5ca4403205b2966bd488f6b3 AS web-build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM cgr.dev/chainguard/wolfi-base:latest@sha256:02dab76bd852a70556b5b2002195c8a5fdab77d323c433bf6642aab080489795 AS python-build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN apk add --no-cache \
      python-3.12=3.12.13-r10 \
      py3.12-pip=26.1.2-r1
WORKDIR /build
COPY requirements.lock ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python3.12 -m pip install --require-hashes --target=/runtime/app/site-packages \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      -r requirements.lock
COPY pyproject.toml README.md ./
COPY src/ src/
RUN python3.12 -m pip install --target=/runtime/app/site-packages \
      --no-deps --no-build-isolation . \
    && mkdir -p /runtime/models /runtime/audit

FROM cgr.dev/chainguard/wolfi-base:latest@sha256:02dab76bd852a70556b5b2002195c8a5fdab77d323c433bf6642aab080489795 AS runtime
RUN apk add --no-cache \
      python-3.12=3.12.13-r10 \
    && apk del wolfi-base apk-tools \
    && rm -f /bin/sh /bin/busybox
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
    CMD ["/usr/bin/python3.12", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=3)"]
CMD ["/usr/bin/python3.12", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
