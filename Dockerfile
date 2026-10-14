# ==============================================================================
# FOTOSTREAM - Multi-Photo Video Synthesizer & Streaming Web Application
# Dockerfile: Production Container Definition
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing bytecode (.pyc) and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (FFmpeg, FFprobe, and curl for diagnostic checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python package dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source tree
COPY . .

# Default Environment Variables (Configurable via docker run -e or docker-compose)
ENV HOST=0.0.0.0 \
    PORT=5000 \
    DEFAULT_PREFIX=/fotostream \
    DB_PATH=/app/storage/fotostream.db \
    STORAGE_DIR=/app/storage \
    UPLOAD_DIR=/app/storage/uploads \
    BGM_DIR=/app/storage/bgm \
    TRANSCODE_DIR=/app/storage/transcoded \
    HLS_DIR=/app/storage/hls \
    DOWNLOAD_DIR=/app/downloads \
    FFMPEG_PATH=/usr/bin/ffmpeg \
    FFPROBE_PATH=/usr/bin/ffprobe

# Expose web service port
EXPOSE 5000

# Persistent volume definition for SQLite database and synthesized media assets
VOLUME ["/app/storage"]

# Container Healthcheck (matches requested specification with dynamic DEFAULT_PREFIX)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=5s \
    CMD python -c "import os, requests; prefix = os.getenv('DEFAULT_PREFIX', ''); requests.get(f'http://localhost:5000{prefix}/api/status')"

# ------------------------------------------------------------------------------
# Starting CMD Options:
# ------------------------------------------------------------------------------
# 1) Gunicorn 운영서버로 기동 (요청한 사양에 맞춘 최적화 워커 및 디버깅 로그 옵션)
#    * gunicorn.conf.py 를 통해 uvicorn.workers.UvicornWorker 자동 연동
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "main:app"]

# 2) Run the FastAPI server using Uvicorn on port 5000 (개발 및 경량 구동 대안)
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
