from urllib.parse import urlparse

PROVIDERS = {
    "youtube": {"label": "YouTube", "hosts": {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}},
    "instagram": {"label": "Instagram", "hosts": {"instagram.com", "www.instagram.com"}},
    "spotify": {"label": "Spotify", "hosts": {"spotify.com", "open.spotify.com"}},
    "tiktok": {"label": "TikTok", "hosts": {"tiktok.com", "www.tiktok.com", "vm.tiktok.com"}},
    "facebook": {"label": "Facebook", "hosts": {"facebook.com", "www.facebook.com", "fb.watch", "m.facebook.com"}},
}

def inspect_url(raw_url: str):
    parsed = urlparse(raw_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Enter a valid http:// or https:// URL.")
    host = parsed.hostname.lower().rstrip(".")
    for key, item in PROVIDERS.items():
        if host in item["hosts"] or any(host.endswith("." + h) for h in item["hosts"]):
            return {
                "provider": key,
                "platform": item["label"],
                "url": raw_url.strip(),
                "status": "recognized",
                "message": f"{item['label']} link recognized. Next steps depend on official API support and your permissions."
            }
    return {"provider": "other", "platform": "Other website", "url": raw_url.strip(),
            "status": "unsupported", "message": "This source is not supported yet."}
