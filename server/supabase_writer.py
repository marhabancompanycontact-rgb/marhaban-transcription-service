"""Supabase client using service_role to bypass RLS."""
import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing")
        _client = create_client(url, key)
    return _client


def fetch_voice_note(voice_note_id: str) -> Optional[dict]:
    sb = get_client()
    res = sb.table("voice_notes").select("*").eq("id", voice_note_id).maybe_single().execute()
    return res.data if res else None


def update_voice_note(
    voice_note_id: str,
    *,
    status: Optional[str] = None,
    transcript: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    language: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    sb = get_client()
    patch: dict = {}
    if status is not None:
        patch["status"] = status
    if transcript is not None:
        patch["transcript"] = transcript
    if duration_seconds is not None:
        patch["duration_seconds"] = duration_seconds
    if language is not None:
        patch["language"] = language
    if error_message is not None:
        patch["error_message"] = error_message
    if not patch:
        return
    sb.table("voice_notes").update(patch).eq("id", voice_note_id).execute()


def signed_download_url(audio_path: str, expires_in: int = 600) -> str:
    """Build a short-lived signed URL to download the audio from the
    voice-notes bucket."""
    sb = get_client()
    res = sb.storage.from_("voice-notes").create_signed_url(audio_path, expires_in)
    url = res.get("signedURL") or res.get("signed_url") or res.get("signedUrl")
    if not url:
        raise RuntimeError(f"Could not sign URL for {audio_path}: {res}")
    return url
