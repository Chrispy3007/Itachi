import re
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
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "cachedir": False,
        "ignoreerrors": False,
        "extractor_retries": 1,
        "socket_timeout": 15,
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
    for item in info.get("formats", []):
        # Only offer single-file HTTP formats that already contain both
        # audio and video. This avoids server-side merging and fake options.
        if item.get("has_drm"):
            continue
        if item.get("vcodec") in (None, "none") or item.get("acodec") in (None, "none"):
            continue
        if item.get("protocol") not in {"http", "https"}:
            continue
        format_id = str(item.get("format_id", ""))
        if not format_id:
            continue
        formats.append({
            "format_id": format_id,
            "ext": item.get("ext") or "unknown",
            "resolution": item.get("resolution") or (
                f'{item.get("height")}p' if item.get("height") else "Audio/video"
            ),
            "height": item.get("height"),
            "filesize": item.get("filesize") or item.get("filesize_approx"),
            "fps": item.get("fps"),
            "format_note": item.get("format_note"),
        })
    formats.sort(key=lambda item: (item["height"] or 0, item["filesize"] or 0), reverse=True)
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
            "Only single-file formats containing both audio and video are listed. "
            "Separate video/audio streams and DRM-marked formats are not offered."
            if formats else
            "yt-dlp did not expose a supported single-file audio/video format for this video."
        ),
    }


def resolve_download(url: str, format_id: str) -> dict:
    result = inspect_youtube(url)
    selected = next((item for item in result["formats"] if item["format_id"] == format_id), None)
    if not selected:
        raise ValueError("That format is not available for this video. Inspect the link again.")
    return {
        "url": result["webpage_url"],
        "format": selected,
        "title": result["title"],
    }


def safe_filename(value: str, extension: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", value).strip(" ._")
    name = (name or "youtube-video")[:150]
    ext = re.sub(r"[^a-zA-Z0-9]", "", extension or "mp4")[:8] or "mp4"
    return f"{name}.{ext}"
