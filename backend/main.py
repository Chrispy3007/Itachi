import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, HttpUrl
from starlette.concurrency import run_in_threadpool

from services.detector import inspect_url, PROVIDERS
from services.youtube import inspect_youtube, resolve_download, safe_filename, validate_youtube_url

app = FastAPI(title="Itachi Shadow Media Vault API", version="0.2.0")

default_origins = "http://localhost:3000,https://chrispy3007.github.io"
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", os.getenv("FRONTEND_ORIGIN", default_origins)).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class InspectRequest(BaseModel):
    url: HttpUrl


class YouTubeDownloadRequest(BaseModel):
    url: HttpUrl
    format_id: str


@app.get("/health")
def health():
    import yt_dlp
    deno_path = shutil.which("deno")
    ffmpeg_path = shutil.which("ffmpeg")
    return {
        "status": "ok",
        "service": "itachi-media-api",
        "components": {
            "yt_dlp": {"available": True, "version": yt_dlp.version.__version__},
            "deno": {"available": bool(deno_path), "path": deno_path},
            "ffmpeg": {"available": bool(ffmpeg_path), "path": ffmpeg_path},
        },
    }


@app.get("/api/providers")
def providers():
    details = {
        "youtube": "Public video inspection and single-file formats where available.",
        "instagram": "Eligible account-owned media through supported Meta APIs.",
        "spotify": "Track, album and playlist metadata; no streamed-audio extraction.",
        "tiktok": "Official integrations and media explicitly available for download.",
        "facebook": "Eligible account-owned media through supported Meta APIs.",
    }
    return [{"id": key, "name": value["label"], "capability": details[key]} for key, value in PROVIDERS.items()]


@app.post("/api/inspect")
def inspect(request: InspectRequest):
    try:
        result = inspect_url(str(request.url))
        if result["status"] == "unsupported":
            raise HTTPException(status_code=422, detail=result["message"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/youtube/inspect")
async def youtube_inspect(request: InspectRequest):
    try:
        return await run_in_threadpool(inspect_youtube, str(request.url))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        # Return a safe, actionable error category while retaining full details in Render logs.
        import logging
        logging.getLogger("itachi.youtube").exception("YouTube inspection failed")
        message = str(exc).lower()
        if "deno" in message:
            detail = "The Deno JavaScript runtime is not available to the running Render service. Redeploy the latest commit and check the build logs for the Deno installation step."
        elif "javascript" in message or "js challenge" in message or "ejs" in message:
            detail = "YouTube's JavaScript challenge could not be solved. Check the Render logs for yt-dlp's EJS/runtime diagnostics."
        elif "sign in" in message or "bot" in message or "confirm you're not a bot" in message:
            detail = "YouTube declined this request or requested sign-in. Itachi does not use account cookies or bypass access controls."
        elif "private" in message or "unavailable" in message or "not available" in message:
            detail = "This video is unavailable for public extraction, or the source did not expose supported formats."
        else:
            detail = "yt-dlp could not inspect this video. Check the Render service logs for the extractor error and try a different public video."
        raise HTTPException(status_code=502, detail=detail) from exc


@app.post("/api/youtube/download")
async def youtube_download(request: YouTubeDownloadRequest):
    temp_dir = None
    try:
        url = validate_youtube_url(str(request.url))
        resolved = await run_in_threadpool(resolve_download, url, request.format_id)
        temp_dir = tempfile.mkdtemp(prefix="itachi-")
        output_template = str(Path(temp_dir) / "download.%(ext)s")
        command = [
            sys.executable, "-m", "yt_dlp",
            "--ignore-config", "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
            "--no-part", "--no-cache-dir", "--remote-components", "ejs:github",
            "--merge-output-format", "mkv",
            "-f", resolved["format_selector"],
            "-o", output_template,
            url,
        ]
        result = await run_in_threadpool(
            subprocess.run,
            command,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "yt-dlp failed to create the selected format.")[-1200:]
            raise RuntimeError(detail)
        files = [path for path in Path(temp_dir).iterdir() if path.is_file()]
        if not files:
            raise RuntimeError("yt-dlp completed without producing a media file.")
        output_file = files[0]
        filename = safe_filename(resolved["title"], output_file.suffix.lstrip("."))
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        def stream_file():
            with output_file.open("rb") as media:
                while True:
                    chunk = media.read(256 * 1024)
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(
            stream_file(),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                "Content-Length": str(output_file.stat().st_size),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
            background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
        )
    except ValueError as exc:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc))
    except subprocess.TimeoutExpired as exc:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=504, detail="The media download exceeded the 30-minute processing limit.") from exc
    except Exception as exc:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        import logging
        logging.getLogger("itachi.youtube").exception("YouTube download failed")
        raise HTTPException(status_code=502, detail=f"Could not create the selected download: {str(exc)[-500:]}") from exc


@app.post("/api/download")
def create_download():
    raise HTTPException(status_code=501, detail=(
        "No generic extractor is enabled. Use the dedicated YouTube endpoint for supported public video formats."
    ))
