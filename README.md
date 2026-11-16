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
