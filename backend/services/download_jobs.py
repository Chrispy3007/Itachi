"""Bounded, temporary YouTube download jobs with status and cancellation."""
from __future__ import annotations

import secrets
import shutil
import tempfile
import threading
import time
from pathlib import Path

from services.youtube import safe_filename, validate_youtube_url
from services.youtube_engines import download_with_engine, resolve_download_with_fallback

MAX_ACTIVE = 2
MAX_JOBS = 64
MAX_BYTES = 500 * 1024 * 1024
TTL_SECONDS = 3600
_jobs: dict[str, dict] = {}
_lock = threading.RLock()
_slots = threading.BoundedSemaphore(MAX_ACTIVE)


def _public(job: dict) -> dict:
    return {key: job.get(key) for key in (
        "id", "status", "stage", "progress", "filename", "size",
        "engine", "created_at", "updated_at", "error"
    )}


def _run(job: dict, url: str, format_id: str) -> None:
    try:
        job.update(status="working", stage="checking selected format", updated_at=time.time())
        resolved = resolve_download_with_fallback(url, format_id)
        if job["cancel"].is_set():
            raise InterruptedError("Download cancelled.")
        job.update(stage="downloading", engine=resolved.get("engine"), updated_at=time.time())
        output = download_with_engine(url, resolved, str(job["directory"]), job=job)
        if job["cancel"].is_set():
            raise InterruptedError("Download cancelled.")
        size = output.stat().st_size
        if not size:
            raise RuntimeError("The extractor returned an empty file.")
        if size > MAX_BYTES:
            raise RuntimeError("This deployment accepts downloads up to 500 MB. Choose a smaller format if available.")
        job.update(
            status="ready",
            stage="ready to save",
            progress=100,
            filename=safe_filename(resolved["title"], output.suffix.lstrip(".")),
            path=output,
            size=size,
            updated_at=time.time(),
        )
    except InterruptedError as exc:
        job.update(status="cancelled", stage="cancelled", error=str(exc), updated_at=time.time())
        shutil.rmtree(job["directory"], ignore_errors=True)
    except Exception as exc:
        job.update(status="error", stage="failed", error=str(exc)[-500:], updated_at=time.time())
        shutil.rmtree(job["directory"], ignore_errors=True)
    finally:
        job.pop("process", None)
        _slots.release()


def create_job(raw_url: str, format_id: str) -> dict:
    url = validate_youtube_url(raw_url)
    if not isinstance(format_id, str) or not format_id or len(format_id) > 80:
        raise ValueError("Choose a valid format from the latest inspection results.")
    with _lock:
        _prune_locked()
        if len(_jobs) >= MAX_JOBS:
            raise ValueError("Download queue is full. Completed jobs expire after one hour.")
        if not _slots.acquire(blocking=False):
            raise ValueError("Itachi is busy. Please try again shortly.")
        identity = secrets.token_urlsafe(24)
        directory = Path(tempfile.mkdtemp(prefix="itachi-job-"))
        job = {
            "id": identity, "status": "queued", "stage": "waiting to start",
            "progress": None, "directory": directory, "cancel": threading.Event(),
            "created_at": time.time(), "updated_at": time.time(),
        }
        _jobs[identity] = job
        thread = threading.Thread(target=_run, args=(job, url, format_id), daemon=True)
        thread.start()
        return _public(job)


def get_job(identity: str) -> dict | None:
    with _lock:
        _prune_locked()
        job = _jobs.get(identity)
        return _public(job) if job else None


def get_file(identity: str) -> tuple[Path, str, int] | None:
    with _lock:
        _prune_locked()
        job = _jobs.get(identity)
        if not job or job.get("status") != "ready":
            return None
        path = job.get("path")
        if not path or not path.is_file():
            return None
        return path, job["filename"], job["size"]


def cancel_job(identity: str) -> dict | None:
    with _lock:
        job = _jobs.get(identity)
        if not job:
            return None
        if job.get("status") in ("ready", "error", "cancelled"):
            if job.get("status") == "ready":
                shutil.rmtree(job["directory"], ignore_errors=True)
                job.update(status="cancelled", stage="cancelled", path=None)
        else:
            job["cancel"].set()
            process = job.get("process")
            if process and process.poll() is None:
                process.terminate()
        job["updated_at"] = time.time()
        return _public(job)


def _prune_locked() -> None:
    now = time.time()
    for identity, job in list(_jobs.items()):
        if now - job["updated_at"] > TTL_SECONDS and job["status"] not in ("queued", "working"):
            shutil.rmtree(job["directory"], ignore_errors=True)
            del _jobs[identity]
