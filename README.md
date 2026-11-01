# Reel Transcripts

A small private web app that takes public Instagram reel links and returns only the spoken audio transcript. It does not summarize, rewrite, or send transcripts to an AI API. Audio is downloaded with yt-dlp and transcribed locally by faster-whisper.

## Run locally on Windows

In PowerShell, from this project folder:

```powershell
if (-not (Test-Path .\.venv)) { py -3 -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create or keep a `.env` file with an app password:

```text
APP_PASSWORD=choose_a_long_private_password
```

Start the app:

```powershell
uvicorn app:app --reload
```

Open <http://127.0.0.1:8000>, enter the password, paste public Instagram reel links (one per line), choose a transcription model, and click **Transcribe reels**. The first use downloads the selected Whisper model. The `tiny` model is fastest on CPU; `small` is usually more accurate but slower. Transcripts are saved under `data/` and can be downloaded together as a PDF.

## Deploy on Vercel

1. Import this repository into Vercel.
2. In Vercel Storage, create a **private Blob** store and connect it to this project.
3. In Project Settings, add `APP_PASSWORD` as an environment variable for Production. Redeploy after connecting storage and setting the password.
4. Visit the deployment and enter the same password.

Vercel Blob stores transcripts between function requests. No DeepSeek account or API key is used. The app processes only public Instagram reels that Instagram serves without a login; restricted or unavailable reels show an error and do not stop the remaining links.
