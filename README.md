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
