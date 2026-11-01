"""Download public reel audio without signing in to Instagram."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL


class _QuietLogger:
    """Keep yt-dlp details in its raised error instead of dumping console noise."""

    def debug(self, _message: str) -> None:
        pass

    def warning(self, _message: str) -> None:
        pass

    def error(self, _message: str) -> None:
        pass


def download_audio(url: str, output_dir: Path) -> Path:
    """Save the best audio-only stream and return its file path.

    No post-processing is requested, so yt-dlp does not run ffmpeg to convert
    or extract an audio track. The original audio stream's container is kept.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    options: dict[str, Any] = {
        "format": "bestaudio",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "logger": _QuietLogger(),
    }

    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=True)
        if not info:
            raise RuntimeError("yt-dlp did not return reel information.")
        filename = downloader.prepare_filename(info)

    audio_path = Path(filename)
    if not audio_path.is_file():
        raise FileNotFoundError(f"Downloaded audio file was not found: {audio_path.name}")
    return audio_path
