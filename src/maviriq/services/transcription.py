"""Speech-to-text transcription via OpenAI Whisper API."""

import logging

import httpx

from maviriq.config import settings

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_bytes: bytes, filename: str = "recording.webm") -> str:
    """Send audio to OpenAI Whisper API and return transcribed text."""
    content_type = "audio/mp4" if filename.endswith(".mp4") else "audio/webm"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            files={"file": (filename, audio_bytes, content_type)},
            data={"model": "whisper-1"},
        )
        response.raise_for_status()
        return response.json()["text"]
