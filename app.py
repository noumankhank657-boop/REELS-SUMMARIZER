"""FastAPI backend and static UI for local and Vercel deployment."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

if os.getenv("VERCEL"):
    os.environ.setdefault("HF_HOME", "/tmp/huggingface")

from downloader import download_audio
from pdf_builder import build_pdf
from transcriber import transcribe_audio


ROOT_DIR = Path(__file__).parent
WEB_DIR = ROOT_DIR / "web"
DATA_DIR = ROOT_DIR / "data"
MODEL_OPTIONS = {"tiny", "base", "small"}
SCHEMA_VERSION = 4
REQUIRED_FIELDS = {"transcript", "url", "_schema_version"}
logger = logging.getLogger(__name__)

app = FastAPI(title="Reel Transcripts", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class ProcessRequest(BaseModel):
    url: str
    model_size: str = "tiny"


class PdfRequest(BaseModel):
    results: list[dict[str, Any]]


def _result_name(url: str) -> str:
    return f"notes/{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"


def _authorize(request: Request) -> None:
    configured_password = os.getenv("APP_PASSWORD", "").strip()
    if os.getenv("VERCEL") and not configured_password:
        raise HTTPException(status_code=503, detail="Set APP_PASSWORD in Vercel project settings.")
    if configured_password:
        supplied = request.headers.get("x-app-password", "")
        if not secrets.compare_digest(supplied, configured_password):
            raise HTTPException(status_code=401, detail="Enter the app password to continue.")


async def _read_result(url: str) -> dict[str, Any] | None:
    name = _result_name(url)
    if os.getenv("VERCEL"):
        from vercel import blob

        try:
            stored = await blob.get_blob(name, access="private")
        except blob.BlobNotFoundError:
            return None
        return json.loads(stored.body.decode("utf-8"))

    path = DATA_DIR / name.removeprefix("notes/")
    if not path.is_file():
        return None
    return json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8"))


async def _save_result(url: str, result: dict[str, Any]) -> None:
    name = _result_name(url)
    payload = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
    if os.getenv("VERCEL"):
        from vercel import blob

        await blob.put_blob(
            name,
            payload,
            access="private",
            content_type="application/json",
            allow_overwrite=True,
        )
        return

    path = DATA_DIR / name.removeprefix("notes/")
    path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_bytes, payload)


def _valid_reel_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"instagram.com", "www.instagram.com"}
        and parsed.path.startswith("/reel/")
    )


def _event(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def _friendly_error(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if "can't be seen by certain audiences" in lowered:
        return "Instagram marks this reel as restricted, so it is not available to this app."
    if "empty media response" in lowered or "not available" in lowered:
        return "Instagram did not provide this reel anonymously. Check that it opens while signed out."
    return message or "This reel could not be processed."


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/config")
async def config() -> dict[str, bool]:
    return {"password_required": bool(os.getenv("APP_PASSWORD", "").strip())}


@app.get("/api/notes")
async def list_notes(request: Request) -> list[dict[str, Any]]:
    _authorize(request)
    if os.getenv("VERCEL"):
        try:
            from vercel import blob

            notes: list[dict[str, Any]] = []
            async for entry in blob.query_blobs(prefix="notes/", page_size=100):
                try:
                    stored = await blob.get_blob(entry.pathname, access="private")
                    result = json.loads(stored.body.decode("utf-8"))
                    if REQUIRED_FIELDS.issubset(result) and result.get("_schema_version") == SCHEMA_VERSION:
                        notes.append(result)
                    if len(notes) >= 300:
                        break
                except (blob.BlobNotFoundError, json.JSONDecodeError):
                    continue
            return notes
        except Exception as exc:
            logger.exception("Could not load saved notes from Vercel Blob")
            raise HTTPException(
                status_code=503,
                detail=(
                    "Saved-note storage is unavailable. In Vercel, create a private Blob store "
                    "and connect it to this project for Production, then redeploy. "
                    "See the Vercel function logs for the storage error."
                ),
            ) from exc

    notes = []
    if DATA_DIR.exists():
        for path in (DATA_DIR / "notes").glob("*.json"):
            try:
                result = json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8"))
                if REQUIRED_FIELDS.issubset(result) and result.get("_schema_version") == SCHEMA_VERSION:
                    notes.append(result)
            except (OSError, json.JSONDecodeError):
                continue
    return notes


@app.post("/api/process")
async def process_reel(body: ProcessRequest, request: Request) -> StreamingResponse:
    _authorize(request)
    url = body.url.strip()
    if not _valid_reel_url(url):
        raise HTTPException(status_code=400, detail="Enter a public Instagram reel URL.")
    if body.model_size not in MODEL_OPTIONS:
        raise HTTPException(status_code=400, detail="Choose tiny, base, or small transcription model.")

    async def generate() -> AsyncIterator[bytes]:
        audio_path: Path | None = None
        try:
            cached = await _read_result(url)
            if cached and cached.get("_schema_version") == SCHEMA_VERSION and REQUIRED_FIELDS.issubset(cached):
                yield _event({"type": "result", "result": cached, "cached": True})
                return

            transcript = cached.get("transcript") if cached else None
            if transcript:
                yield _event({"type": "status", "message": "Using saved transcript"})
            else:
                yield _event({"type": "status", "message": "Downloading reel audio"})
                temp_dir = tempfile.TemporaryDirectory(dir="/tmp" if os.getenv("VERCEL") else None)
                try:
                    audio_path = await asyncio.to_thread(download_audio, url, Path(temp_dir.name))
                    yield _event({"type": "status", "message": f"Transcribing audio with the {body.model_size} CPU model"})
                    transcript = await asyncio.to_thread(transcribe_audio, audio_path, body.model_size)
                finally:
                    temp_dir.cleanup()

            if not transcript or not transcript.strip():
                raise ValueError("No speech could be transcribed from this reel.")
            result = {"transcript": transcript.strip(), "url": url, "_schema_version": SCHEMA_VERSION}
            await _save_result(url, result)
            yield _event({"type": "result", "result": result, "cached": False})
        except Exception as exc:
            yield _event({"type": "error", "message": _friendly_error(exc)})
        finally:
            if audio_path is not None:
                audio_path.unlink(missing_ok=True)

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@app.post("/api/pdf")
async def create_pdf(body: PdfRequest, request: Request) -> Response:
    _authorize(request)
    if not body.results:
        raise HTTPException(status_code=400, detail="There are no notes to export.")
    with tempfile.TemporaryDirectory(dir="/tmp" if os.getenv("VERCEL") else None) as temp_dir:
        pdf_path = Path(temp_dir) / "sales-reel-notes.pdf"
        await asyncio.to_thread(build_pdf, body.results, pdf_path)
        pdf_bytes = await asyncio.to_thread(pdf_path.read_bytes)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="sales-reel-notes.pdf"'},
    )
