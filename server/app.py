"""
FastAPI server for Marhaban Company's transcription module.

Endpoints:
  GET  /health              → ping
  POST /transcribe          → trigger a transcription job (voice_note_id)
                              requires header: X-API-Secret

Env:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  API_SECRET
  WHISPER_MODEL  (default: medium)
"""
import os
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from .worker import run_transcription

load_dotenv()

API_SECRET = os.getenv("API_SECRET", "")

app = FastAPI(title="Marhaban Transcription Service", version="0.1.0")


class TranscribePayload(BaseModel):
    voice_note_id: str


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "marhaban-transcription-service",
        "model": os.getenv("WHISPER_MODEL", "medium"),
    }


@app.post("/transcribe")
async def transcribe(
    payload: TranscribePayload,
    background: BackgroundTasks,
    x_api_secret: str | None = Header(default=None, alias="X-API-Secret"),
):
    if not API_SECRET or x_api_secret != API_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")

    background.add_task(run_transcription, payload.voice_note_id)
    return {"accepted": True, "voice_note_id": payload.voice_note_id}
