"""Speech-to-text transcription via OpenAI Whisper API."""

import logging
import re

import httpx

from maviriq.config import settings

logger = logging.getLogger(__name__)

# Hallucination-suppression prompt — gives Whisper domain context so it
# doesn't invent YouTube-style filler when audio is ambiguous or silent.
_WHISPER_PROMPT = (
    "This is a voice recording of someone describing a startup or business idea. "
    "Transcribe exactly what is said. Do not add filler phrases."
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
