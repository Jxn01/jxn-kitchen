# JXN Kitchen — one image: the Svelte app built in a node stage, served by FastAPI in a slim Python stage.
# Built ON the server by ./deploy.sh (context = the repo root, synced to /srv/compose/kitchen/src).
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund --loglevel=error
COPY web/ ./
ARG KITCHEN_BUILD=dev
RUN KITCHEN_BUILD="$KITCHEN_BUILD" npx vitest run && KITCHEN_BUILD="$KITCHEN_BUILD" npm run build --silent

FROM python:3.13-slim
ARG KITCHEN_BUILD=dev
ENV KITCHEN_BUILD=$KITCHEN_BUILD
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    KITCHEN_STATIC_DIR=/app/static KITCHEN_DATA_DIR=/data TZ=Europe/Budapest
WORKDIR /app
# Digitising (sub-project 7): Tesseract with the Hungarian + English models (+ OSD: pages scanned sideways) and poppler
# for splitting scanned PDFs into pages
# apt-get -y upgrade: Debian's security fixes on top of the base image, every build (a weekly rebuild with --pull can
# take them in between deploys). The base lags Debian between its own releases -- it carried a libbrotli1
# vulnerable to Node2Shell (CVE-2026-111497) on 2026-10-26.
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y upgrade \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hun tesseract-ocr-eng \
      tesseract-ocr-osd poppler-utils && rm -rf /var/lib/apt/lists/*
COPY server/pyproject.toml ./server/pyproject.toml
COPY server/kitchen ./server/kitchen
COPY catalogue ./catalogue
COPY knowhow ./knowhow
COPY engine ./engine
RUN pip install --no-cache-dir ./server && rm -rf ./server
ENV KITCHEN_CATALOGUE_DIR=/app/catalogue
COPY --from=web /web/dist ./static
RUN useradd --system --uid 10001 --no-create-home kitchen && mkdir -p /data && chown kitchen /data
USER kitchen
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
# --timeout-graceful-shutdown: open SSE streams never end by themselves; without it every stop waited Docker's 10 s
# and ended in SIGKILL, skipping the app's shutdown (measured 2026-10-10: restart 10.6 s)
CMD ["uvicorn", "kitchen.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*", "--timeout-graceful-shutdown", "2"]
