"""Background worker that transcribes one voice note at a time.

Model is loaded lazily on first request and kept in memory. A global asyncio
lock guarantees only one transcription runs concurrently — critical on the
shared 2-CPU VPS where medium INT8 would otherwise fight WAHA/video/scraping.
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional

import httpx
from faster_whisper import WhisperModel

from .supabase_writer import (
    fetch_voice_note,
    signed_download_url,
    update_voice_note,
)

_model: Optional[WhisperModel] = None
_model_lock = asyncio.Lock()
_job_lock = asyncio.Lock()


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        model_name = os.getenv("WHISPER_MODEL", "medium")
        print(f"[worker] Loading faster-whisper model: {model_name} (INT8 CPU)")
        _model = WhisperModel(model_name, device="cpu", compute_type="int8")
        print(f"[worker] Model ready")
    return _model


async def run_transcription(voice_note_id: str) -> None:
    async with _job_lock:
        await _run(voice_note_id)


async def _run(voice_note_id: str) -> None:
    row = fetch_voice_note(voice_note_id)
    if not row:
        print(f"[worker] voice_note {voice_note_id} not found")
        return

    audio_path = row.get("audio_path")
    if not audio_path:
        update_voice_note(
            voice_note_id,
            status="error",
            error_message="audio_path missing on voice_notes row",
        )
        return

    update_voice_note(voice_note_id, status="transcribing", error_message=None)

    tmp: Optional[str] = None
    try:
        url = signed_download_url(audio_path, expires_in=600)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            suffix = Path(audio_path).suffix or ".bin"
            fd, tmp = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, "wb") as f:
                f.write(resp.content)

        def _do_transcribe(path: str) -> tuple[str, float, str]:
            model = _get_model()
            segments, info = model.transcribe(
                path,
                language="fr",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text, info.duration, info.language

        text, duration, language = await asyncio.to_thread(_do_transcribe, tmp)

        update_voice_note(
            voice_note_id,
            status="done",
            transcript=text,
            duration_seconds=duration,
            language=language,
        )
        print(f"[worker] {voice_note_id} done ({duration:.1f}s, {len(text)} chars)")

    except Exception as e:
        print(f"[worker] {voice_note_id} failed: {e}")
        update_voice_note(voice_note_id, status="error", error_message=str(e)[:500])
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
