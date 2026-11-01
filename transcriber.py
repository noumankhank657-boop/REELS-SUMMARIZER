"""Transcribe downloaded audio with faster-whisper on the CPU."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Callable

from faster_whisper import WhisperModel


@lru_cache(maxsize=5)
def _load_model(model_size: str) -> WhisperModel:
    """Load and reuse a CPU model for the requested size."""
    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe_audio(
    audio_path: Path,
    model_size: str = "tiny",
    progress_callback: Callable[[int], None] | None = None,
) -> str:
    """Return the recognized words from an audio file as a single string."""
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

    if progress_callback:
        progress_callback(0)
    model = _load_model(model_size)
    segments, _info = model.transcribe(str(audio_path), beam_size=5)
    transcript_parts: list[str] = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            transcript_parts.append(text)
            if progress_callback:
                progress_callback(int(segment.end))
    return " ".join(transcript_parts)
