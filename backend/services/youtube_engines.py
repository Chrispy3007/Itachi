import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

from services.youtube import inspect_youtube, resolve_download, safe_filename, validate_youtube_url


def _is_access_denial(error: Exception) -> bool:
    message = str(error).lower()
    markers = (
        "sign in", "confirm you're not a bot", "not a bot", "captcha",
        "login required", "private video", "members-only", "age-restricted",
        "drm", "forbidden", "http error 403",
    )
    return any(marker in message for marker in markers)


def inspect_youtubejs(url: str) -> dict:
    node = shutil.which("node")
    script = Path(__file__).resolve().parent / "youtubejs.mjs"
    if not node or not script.is_file():
        raise RuntimeError("YouTube.js adapter is not installed in this deployment.")
    result = subprocess.run(
        [node, str(script), "inspect", validate_youtube_url(url)],
        capture_output=True, text=True, timeout=90, check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or "YouTube.js inspection failed.")[-1200:])
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("YouTube.js returned an invalid response.") from exc


def inspect_with_fallback(url: str) -> dict:
    url = validate_youtube_url(url)
    try:
        result = inspect_youtube(url)
        result["engine"] = "yt-dlp"
        result["engines_attempted"] = ["yt-dlp"]
        return result
    except Exception as primary_error:
        # A provider access denial is not an extractor compatibility failure.
        # Do not try alternate clients to work around an explicit denial.
        if _is_access_denial(primary_error):
            raise
        try:
            result = inspect_youtubejs(url)
            result["engines_attempted"] = ["yt-dlp", "youtubejs"]
            result["fallback_reason"] = "yt-dlp extractor error"
            return result
        except Exception as fallback_error:
            raise RuntimeError(
                "All enabled YouTube extractors failed. "
                f"yt-dlp: {primary_error}; YouTube.js: {fallback_error}"
            ) from fallback_error


def resolve_download_with_fallback(url: str, format_id: str) -> dict:
    url = validate_youtube_url(url)
    if format_id.startswith("youtubejs:"):
        result = inspect_youtubejs(url)
        selected = next((f for f in result["formats"] if f["format_id"] == format_id), None)
        if not selected:
            raise ValueError("That YouTube.js format is no longer available. Inspect the link again.")
        return {
            "engine": "youtubejs",
            "format": selected,
            "title": result["title"],
            "url": result["webpage_url"],
            "itag": format_id.split(":", 1)[1],
        }
    resolved = resolve_download(url, format_id)
    resolved["engine"] = "yt-dlp"
    return resolved


def download_with_engine(url: str, resolved: dict, temp_dir: str) -> Path:
    if resolved["engine"] == "youtubejs":
        node = shutil.which("node")
        script = Path(__file__).resolve().parent / "youtubejs.mjs"
        if not node or not script.is_file():
            raise RuntimeError("YouTube.js adapter is not installed in this deployment.")
        output = Path(temp_dir) / safe_filename(resolved["title"], resolved["format"].get("ext", "mp4"))
        env = os.environ.copy()
        env["ITACHI_OUTPUT_PATH"] = str(output)
        result = subprocess.run(
            [node, str(script), "download", url, resolved["itag"]],
            capture_output=True, text=True, timeout=1800, check=False, env=env,
        )
        if result.returncode or not output.is_file():
            raise RuntimeError((result.stderr or "YouTube.js download failed.")[-1200:])
        return output

    output_template = str(Path(temp_dir) / "download.%(ext)s")
    command = [
        shutil.which("python") or "python", "-m", "yt_dlp",
        "--ignore-config", "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
        "--no-part", "--no-cache-dir", "--remote-components", "ejs:github",
        "--merge-output-format", "mkv", "-f", resolved["format_selector"],
        "-o", output_template, url,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "yt-dlp download failed.")[-1200:])
    files = [path for path in Path(temp_dir).iterdir() if path.is_file()]
    if not files:
        raise RuntimeError("yt-dlp completed without producing a media file.")
    return files[0]


def engine_health() -> dict:
    return {
        "yt_dlp": {"available": importlib.util.find_spec("yt_dlp") is not None},
        "youtubejs": {"available": shutil.which("node") is not None and (Path(__file__).resolve().parent / "youtubejs.mjs").is_file()},
        "newpipe": {"available": False, "reason": "Isolated adapter not installed yet."},
        "cobalt": {"available": bool(os.getenv("COBALT_API_URL")), "mode": "remote API" if os.getenv("COBALT_API_URL") else "not configured"},
    }
