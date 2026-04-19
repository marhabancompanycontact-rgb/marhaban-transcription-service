# Marhaban Transcription Service — Python + FastAPI + faster-whisper
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=3003
# CTranslate2 performance tuning for CPU-only inference (2 CPUs on VPS KVM 2).
ENV OMP_NUM_THREADS=2
ENV MKL_NUM_THREADS=2

WORKDIR /app

# System deps for ffmpeg (faster-whisper uses it for resampling / non-wav formats)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the Whisper model at build time so the first request doesn't
# stall on a multi-hundred-MB download. The path is baked into /root/.cache.
ARG WHISPER_MODEL=medium
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8')"

COPY . .

EXPOSE 3003

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "3003"]
