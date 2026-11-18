import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from services.detector import inspect_url, PROVIDERS

app = FastAPI(title="Itachi Shadow Media Vault API", version="0.1.0")

# GitHub Pages serves the current static frontend. Keep local development and
# Pages enabled by default, while allowing deployments to override the list.
default_origins = "http://localhost:3000,https://chrispy3007.github.io"
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", os.getenv("FRONTEND_ORIGIN", default_origins)).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InspectRequest(BaseModel):
    url: HttpUrl

@app.get("/health")
def health():
    return {"status": "ok", "service": "itachi-media-api"}

@app.get("/api/providers")
def providers():
    details = {
        "youtube": "Official metadata and owner-authorized content workflows.",
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

@app.post("/api/download")
def create_download():
    raise HTTPException(status_code=501, detail=(
        "No generic extractor is enabled. Add an official provider workflow for content "
        "you own or are authorized to save. DRM and platform restrictions are not bypassed."
    ))
