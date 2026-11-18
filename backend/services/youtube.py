import re
import shutil
from urllib.parse import urlparse

import yt_dlp


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


def validate_youtube_url(raw_url: str) -> str:
    value = raw_url.strip()
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not host or parsed.username or parsed.password:
        raise ValueError("Enter a valid public YouTube video URL.")
    if not (host in YOUTUBE_HOSTS or any(host.endswith("." + item) for item in YOUTUBE_HOSTS)):
        raise ValueError("Only YouTube video URLs are supported by this endpoint.")
    if not (
        host.endswith("youtu.be")
        or parsed.path == "/watch"
        or re.match(r"^/(?:shorts|embed|live)/[^/]+", parsed.path)
    ):
        raise ValueError("Paste a YouTube video or Shorts URL, not a channel or playlist page.")
    return value


def _extract_info(url: str) -> dict:
    if not shutil.which("deno"):
        raise RuntimeError("Deno JavaScript runtime is missing from PATH on the Render service.")
    options = {
        "quiet": True,
        "no_warnings": False,
        "noplaylist": True,
        "skip_download": True,
        "cachedir": False,
        "ignoreerrors": False,
        "extractor_retries": 2,
        "socket_timeout": 25,
        "js_runtimes": {"deno": {}},
        "remote_components": ["ejs:github"],
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info or info.get("_type") == "playlist":
        raise ValueError("This URL did not resolve to a single public video.")
    if info.get("is_live") and not info.get("was_live"):
        raise ValueError("Live streams are not supported by this downloader.")
    if info.get("availability") not in (None, "public", "unlisted"):
        raise ValueError("This video is not publicly available.")
    return info


def inspect_youtube(url: str) -> dict:
    url = validate_youtube_url(url)
    info = _extract_info(url)
    formats = []
    seen = set()
    for item in info.get("formats", []):
        if item.get("has_drm"):
            continue
        if item.get("protocol") not in {"http", "https"}:
            continue
        format_id = str(item.get("format_id", ""))
        if not format_id or format_id in seen:
            continue

        has_video = item.get("vcodec") not in (None, "none")
        has_audio = item.get("acodec") not in (None, "none")
        if not has_video:
            continue

        # Include both native muxed formats and video-only adaptive formats.
        # For video-only streams the download endpoint pairs this exact stream
        # with the best available audio stream and muxes them with FFmpeg.
        needs_merge = not has_audio
        height = item.get("height")
        output_ext = "mkv" if needs_merge else (item.get("ext") or "unknown")
        formats.append({
            "format_id": format_id,
            "ext": output_ext,
            "source_ext": item.get("ext") or "unknown",
            "resolution": item.get("resolution") or (f"{height}p" if height else "Video"),
            "height": height,
            "filesize": item.get("filesize") or item.get("filesize_approx"),
            "fps": item.get("fps"),
            "format_note": item.get("format_note"),
            "needs_merge": needs_merge,
        })
        seen.add(format_id)

    formats.sort(
        key=lambda item: (item["height"] or 0, item["fps"] or 0, item["filesize"] or 0),
        reverse=True,
    )
    return {
        "provider": "youtube",
        "status": "available" if formats else "no_direct_formats",
        "id": info.get("id"),
        "title": info.get("title") or "YouTube video",
        "channel": info.get("channel") or info.get("uploader"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "webpage_url": info.get("webpage_url") or url,
        "formats": formats,
        "message": (
            "Video resolutions include native audio/video files and adaptive video streams. "
            "Adaptive streams are paired with the best available audio and merged into an MKV file. "
            "DRM-marked and non-downloadable formats are excluded."
            if formats else
            "yt-dlp did not expose supported downloadable video formats for this video."
        ),
    }


def resolve_download(url: str, format_id: str) -> dict:
    result = inspect_youtube(url)
    selected = next((item for item in result["formats"] if item["format_id"] == format_id), None)
    if not selected:
        raise ValueError("That format is not available for this video. Inspect the link again.")
    selector = f"{format_id}+bestaudio/best" if selected["needs_merge"] else format_id
    return {
        "url": result["webpage_url"],
        "format": selected,
        "format_selector": selector,
        "title": result["title"],
    }


def safe_filename(value: str, extension: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", value).strip(" ._")
    name = (name or "youtube-video")[:150]
    ext = re.sub(r"[^a-zA-Z0-9]", "", extension or "mp4")[:8] or "mp4"
    return f"{name}.{ext}"
