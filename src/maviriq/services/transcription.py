"""Speech-to-text transcription via OpenAI Whisper API."""

import logging
import re

import httpx

from maviriq.config import settings

logger = logging.getLogger(__name__)

# Whisper prompt — used as a vocabulary/style hint (NOT an instruction).
# Whisper conditions on this text to bias toward domain-relevant words
# and away from YouTube-style hallucinations.
_WHISPER_PROMPT = (
    "startup, business idea, product, market, customers, revenue, "
    "SaaS, app, platform, MVP, validation"
)

# Known Whisper hallucination phrases (English + Lithuanian).
_HALLUCINATION_PHRASES: list[str] = [
    # English
    "thank you for watching",
    "thanks for watching",
    "subscribe to my channel",
    "like and subscribe",
    "please subscribe",
    "hit the bell",
    "see you in the next video",
    "don't forget to subscribe",
    "leave a like",
    "thank you for listening",
    "please like and subscribe",
    # Lithuanian
    "ačiū, kad žiūrite",
    "ačiū kad žiūrite",
    "prenumeruokite kanalą",
    "spauskite prenumeruoti",
    "iki pasimatymo",
    "subtitrai pagal declips",
    "subtitrai sukurti declips",
    "džiaugiuosi, džiaugiuosi",
    "džiaugiuosi džiaugiuosi",
    # Guard against prompt echo (if prompt text leaks into output)
    "transcribe exactly what is said",
    "do not add filler phrases",
]


def _filter_hallucinations(text: str) -> str:
    """Remove known Whisper hallucination phrases from transcribed text."""
    cleaned = text
    for phrase in _HALLUCINATION_PHRASES:
        cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.strip(" .,!?;:")
    return cleaned


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "recording.webm",
    language: str | None = None,
) -> str:
    """Send audio to OpenAI Whisper API and return transcribed text."""
    content_type = "audio/mp4" if filename.endswith(".mp4") else "audio/webm"

    data: dict[str, str] = {"model": "whisper-1", "prompt": _WHISPER_PROMPT}
    if language:
        data["language"] = language

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            files={"file": (filename, audio_bytes, content_type)},
            data=data,
        )
        response.raise_for_status()
        text = response.json()["text"]
        return _filter_hallucinations(text)
