# Marhaban Transcription Service

FastAPI + faster-whisper service that transcribes voice notes stored in
Supabase `voice-notes` bucket and writes the result back to the `voice_notes`
table.

## Architecture

- **Trigger** — Vercel app calls `POST /transcribe { voice_note_id }` with
  `X-API-Secret` header (fire-and-forget).
- **Worker** — FastAPI `BackgroundTasks` picks up the job. Downloads the audio
  from Supabase Storage using the service role, transcribes with
  faster-whisper, writes `transcript` and flips `status` from `transcribing`
  to `done` (or `error`).
- **Concurrency guard** — a global `asyncio.Lock` serialises jobs so that we
  never run two `medium` inferences at once on the shared 2-CPU/8GB VPS.
  The Supabase row stays in `pending` while the lock is held by another job.

## Endpoints

- `GET  /health`
- `POST /transcribe` — body: `{ "voice_note_id": "<uuid>" }`, header:
  `X-API-Secret: ...`

## Local dev

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # fill in values
uvicorn server.app:app --host 0.0.0.0 --port 3003 --reload
```

## Deploy to VPS Hostinger

```bash
# On the VPS (Ubuntu 24.04 + Docker)
cd /opt
git clone https://github.com/marhabancompanycontact-rgb/marhaban-transcription-service.git
cd marhaban-transcription-service
cp .env.example .env   # edit with real values
docker compose up -d --build
```

The Dockerfile pre-downloads the Whisper model during build, so the first
request doesn't stall.

## Env vars

| Name | Required | Purpose |
|------|----------|---------|
| `SUPABASE_URL` | yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | yes | service role key (bypasses RLS) |
| `API_SECRET` | yes | shared secret with Vercel app |
| `WHISPER_MODEL` | no | `medium` (default), `small`, `base`, `tiny`, `large-v3` |
