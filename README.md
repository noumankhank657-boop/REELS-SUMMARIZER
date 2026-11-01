# Sales Reel Notes

A minimal private web app that turns public Instagram reels into short sales advice and content patterns. The app uses a plain HTML interface and a FastAPI Python backend; it does not use Streamlit or sign in to Instagram.

## Run locally on Windows

In PowerShell, from this project folder:

```powershell
if (-not (Test-Path .\.venv)) { py -3 -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Add these settings to your existing `.env` file. Keep any key already there; do not overwrite it, paste real keys into chat, or commit `.env`:

```text
DEEPSEEK_API_KEY=your_deepseek_key
APP_PASSWORD=choose_a_long_private_password
```

Start the local app:

```powershell
uvicorn app:app --reload
```

Open <http://127.0.0.1:8000>. Enter one or more public reel links, one per line, and click **Process reels**. Each link runs separately so one failed reel does not stop the rest. The selected `tiny` model is fastest on CPU. Click **Download notes PDF** after processing to export the current batch. Saved notes live in `data/` during local use.

## Deploy on Vercel

The project is configured as a Python FastAPI app for Vercel Functions. Vercel's Python runtime is currently in beta. Each reel is processed in its own request; the Hobby plan allows a function to run for up to five minutes. First use may download the Whisper model, so long reels or a cold start can exceed that limit.

1. Put this project in a Git repository and import that repository as a new project in Vercel. Keep the project root set to this folder.
2. In the Vercel project, open **Storage**, create a **private Blob** store, and connect it to the project. The app uses private Blob storage for saved notes because Vercel function files do not persist between requests.
3. In **Project Settings → Environment Variables**, set `DEEPSEEK_API_KEY` to your DeepSeek API key and `APP_PASSWORD` to a long private password. Apply both to Production (and Preview if you will use preview deployments), then redeploy.
4. Open the deployed URL and enter your app password. Keep it private; the same password protects the processing, saved notes, and PDF endpoints.

The Blob store should be private. Vercel supplies its storage credentials when the store is connected. Do not put API keys or passwords in frontend code. Keep the repository's `.env` file out of Git; `.gitignore` already excludes it.

## What each reel saves

Each saved note contains only **Use when**, **Content part** (content ideas, how the hook works, and hook pattern), and **Sales part** (sales advice). The PDF and the notes page use the same compact format. Existing local notes are stored one JSON file per reel in `data/`.

## Reel access and privacy

Only public reels that Instagram serves without signing in can be processed. Instagram may still block automated requests or restrict a reel, in which case that link reports an error and the batch continues. The app asks yt-dlp for audio-only media and does not request video conversion. Transcripts are sent to DeepSeek to create the short notes; the API key stays on the server.
# REELS-SUMMARIZER
