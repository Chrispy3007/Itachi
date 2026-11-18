import time
from pathlib import Path
from unittest.mock import patch

from services import download_jobs


VIDEO_URL = "https://youtu.be/abcdefghijk"


def wait_for(identity, terminal=("ready", "error", "cancelled")):
    for _ in range(200):
        job = download_jobs.get_job(identity)
        if job and job["status"] in terminal:
            return job
        time.sleep(0.025)
    raise AssertionError("download job did not reach a terminal state")


def test_job_runs_and_exposes_temporary_file(tmp_path):
    def fake_download(url, resolved, directory, job=None):
        target = Path(directory) / "result.mp4"
        target.write_bytes(b"media")
        return target

    with patch("services.download_jobs.resolve_download_with_fallback", return_value={
        "engine": "yt-dlp", "title": "Example"
    }), patch("services.download_jobs.download_with_engine", side_effect=fake_download):
        created = download_jobs.create_job(VIDEO_URL, "18")
        finished = wait_for(created["id"])
    assert finished["status"] == "ready"
    path, filename, size = download_jobs.get_file(created["id"])
    assert path.read_bytes() == b"media"
    assert filename == "Example.mp4"
    assert size == 5


def test_job_rejects_invalid_youtube_url():
    import pytest
    with pytest.raises(ValueError, match="Only YouTube"):
        download_jobs.create_job("https://example.com/video", "18")


def test_job_rejects_missing_format():
    import pytest
    with pytest.raises(ValueError, match="valid format"):
        download_jobs.create_job(VIDEO_URL, "")


def test_cancel_terminates_active_extractor(tmp_path):
    import threading

    started = threading.Event()

    def slow_download(url, resolved, directory, job=None):
        started.set()
        while not job["cancel"].is_set():
            time.sleep(0.01)
        raise InterruptedError("Download cancelled.")

    with patch("services.download_jobs.resolve_download_with_fallback", return_value={
        "engine": "yt-dlp", "title": "Example"
    }), patch("services.download_jobs.download_with_engine", side_effect=slow_download):
        created = download_jobs.create_job(VIDEO_URL, "18")
        assert started.wait(2)
        cancelled = download_jobs.cancel_job(created["id"])
        assert cancelled["status"] == "working"
        finished = wait_for(created["id"])
    assert finished["status"] == "cancelled"
    assert download_jobs.get_file(created["id"]) is None


def test_ready_job_can_be_cancelled_and_file_removed():
    def fake_download(url, resolved, directory, job=None):
        target = Path(directory) / "result.mp4"
        target.write_bytes(b"media")
        return target

    with patch("services.download_jobs.resolve_download_with_fallback", return_value={
        "engine": "yt-dlp", "title": "Example"
    }), patch("services.download_jobs.download_with_engine", side_effect=fake_download):
        created = download_jobs.create_job(VIDEO_URL, "18")
        assert wait_for(created["id"])["status"] == "ready"
        cancelled = download_jobs.cancel_job(created["id"])
    assert cancelled["status"] == "cancelled"
    assert download_jobs.get_file(created["id"]) is None
