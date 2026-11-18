# Itachi — Shadow Media Vault

An Itachi Uchiha / Akatsuki-inspired personal media workspace.

## Stack
- Frontend: Next.js 14, React, TypeScript, Tailwind CSS
- Backend: FastAPI (Python)
- Hosting: Vercel for the frontend; Render/Railway for the API

## Local development
### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000.

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Set `NEXT_PUBLIC_API_BASE=http://localhost:8000` in `frontend/.env.local`.

## Current capabilities
- Itachi-themed responsive dashboard
- URL platform detection for YouTube, Instagram, Spotify, TikTok and Facebook
- API endpoint for inspecting links
- Explicit safe-by-design provider messaging

## Important provider limitations
This app does not bypass DRM, login walls, private-account restrictions, or platform download controls. Spotify integration is for metadata/playlist information through its official API; it does not extract Spotify-streamed audio. Enable download workflows only for content you own or have permission to save, using official APIs or provider-authorized download paths.

## Deployment
- Import this repository into Vercel and set the Root Directory to `frontend`.
- Deploy `backend` as a separate Python web service on Render/Railway.
- Set `NEXT_PUBLIC_API_BASE` to the deployed API URL.
- Configure provider credentials as backend environment variables only; never commit secrets.

## YouTube backend (yt-dlp)

The FastAPI backend now includes two YouTube-specific endpoints:

- `POST /api/youtube/inspect` with JSON `{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}` returns the video's metadata and only the single-file HTTP formats that already contain both audio and video.
- `POST /api/youtube/download` with JSON `{"url":"https://www.youtube.com/watch?v=VIDEO_ID","format_id":"FORMAT_ID"}` streams the selected original format through the API response. The backend does not keep a permanent media copy.

Run the API locally:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The YouTube endpoints deliberately do not use browser cookies or private-account access. DRM-marked formats, live streams, and separate video-only/audio-only formats are not offered. This first version therefore shows only formats that can be delivered as a single file without a server-side merge; the available resolutions depend on what YouTube exposes for each video. yt-dlp and YouTube delivery behavior can change, so a successful inspection is not guaranteed for every public link.

The current GitHub Pages frontend is static and does not host this API. To make YouTube formats and downloads appear on the live site, deploy the `backend` as a separate service and configure the frontend to call that API. Do not expose an unprotected public download API to heavy traffic; add appropriate rate limits and operational monitoring before production use.

Only download videos you own or are otherwise authorized to save, and follow the applicable platform terms and copyright rules.


## GitHub-only yt-dlp download (manual)

The live GitHub Pages site is static, so it cannot run yt-dlp as an on-demand API. While we are avoiding a separately hosted backend, this repository includes a manually triggered GitHub Actions workflow as a temporary download path:

1. Open the repository's **Actions** tab.
2. Select **Download with yt-dlp**.
3. Choose **Run workflow**, paste an HTTPS YouTube video URL, and start the run.
4. When the run finishes, open it and download the **itachi-download** artifact.

The workflow runs on a temporary GitHub-hosted runner, accepts YouTube URLs only, requests one video (not a playlist), limits the download to 500 MB, and keeps the artifact for one day. It does not use browser cookies, sign in to accounts, access private videos, or bypass DRM. It selects the best available single-file format containing both audio and video; it does not merge separate streams or convert media. Some videos may not offer a suitable format, and GitHub Actions usage limits apply.

This is a manual GitHub Actions workflow, not a direct download button on the Pages website. Use it only for videos you own or have permission to save, and comply with applicable platform terms and copyright rules.


## Deploy the API on Render

The repository includes a Render Blueprint for the FastAPI + yt-dlp service:

1. Sign in to Render and choose **New → Blueprint**.
2. Connect the `Chrispy3007/Itachi` GitHub repository.
3. Select the `main` branch and deploy the Blueprint from the repository's `render.yaml`.
4. Wait for the service to finish deploying, then open its **`/health`** URL. A healthy service returns JSON with `"status": "ok"`.
5. Copy the service's public `onrender.com` URL. The GitHub Pages frontend must be configured with this exact API base URL as `window.ITACHI_API_BASE`; do not include a trailing slash.

The Blueprint uses Render's free web-service plan, configures the GitHub Pages origin for CORS, and uses `/health` for deployment health checks. Render free web services spin down after a period without inbound traffic, so the first request after inactivity can be delayed. Free-plan availability and limits are controlled by Render and may change.

No persistent disk or database is configured. The API streams downloads and does not intentionally retain media files. This is a small free-tier deployment intended for personal/testing use, not an unrestricted public download service. Use it only for media you own or are authorized to save and follow provider terms.


## Balanced product direction and current capabilities

Itachi's product goal is a simple flow: paste a link, inspect the real downloadable options, choose a quality, and save the file to the user's device. The website is hosted on GitHub Pages and the API is deployed separately on Render.

### Current implementation status

- YouTube: yt-dlp inspection is implemented. The API lists downloadable video streams, including adaptive video-only formats; adaptive downloads pair the selected video with the best available audio and merge with FFmpeg into MKV. Availability depends on the video's exposed formats and whether YouTube accepts the request from the service's network.
- Direct media URLs: the browser can inspect and download direct files when the source permits browser access (including CORS).
- Instagram, TikTok and Facebook: the provider detector recognizes links, but recognition is not the same as a working downloader. Do not advertise these providers as download-ready until an authorized extraction/API adapter is implemented and tested.
- Spotify: metadata recognition only; Itachi does not extract Spotify-streamed audio.

### YouTube extraction engines

The backend now has a small extraction-engine orchestrator. yt-dlp remains the primary engine; a YouTube.js adapter is installed as a secondary engine for extractor compatibility failures. The adapter returns only single-file audio/video formats and can download a selected format through the same temporary-file delivery path.

Fallback is deliberately not attempted after an explicit YouTube sign-in, bot-verification, private-video, DRM, or access-denial response. Switching extractor libraries does not grant permission to evade a provider's access controls, and it does not guarantee that a different library will be accepted from the same hosting network.

NewPipe and Cobalt are research candidates, not active extraction engines in this deployment yet. NewPipe requires a separately packaged JVM service and GPL-3.0 compliance review. Cobalt requires a separately deployed instance/API and AGPL-3.0 compliance review. The health endpoint reports these as unavailable/not configured rather than claiming they are active.

The Render Docker image now installs Node.js/npm for YouTube.js. The health endpoint reports engine availability. A successful health response verifies installed components only; it does not prove that YouTube will accept a request or that a real media download will complete.

### Runtime diagnostics

`GET /health` reports the installed yt-dlp version and whether Deno and FFmpeg executables are available in the running container. A healthy API response alone does not prove that a particular platform will permit extraction or that a full download will complete.

### Product guarantees

Only display formats returned by the source and supported by the backend. Never invent resolutions, file sizes, or availability. Do not bypass DRM, private/login-only restrictions, or provider access controls. Temporary files used for stream merging must be removed after delivery; no permanent media library is maintained on the server.
