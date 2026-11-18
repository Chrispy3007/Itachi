const API = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/+$/, "");

export type InspectResult = {
  provider: string;
  platform: string;
  url: string;
  status: string;
  message: string;
};

const PROVIDERS: Record<string, { label: string; hosts: string[] }> = {
  youtube: { label: "YouTube", hosts: ["youtube.com", "youtu.be"] },
  instagram: { label: "Instagram", hosts: ["instagram.com"] },
  spotify: { label: "Spotify", hosts: ["spotify.com"] },
  tiktok: { label: "TikTok", hosts: ["tiktok.com"] },
  facebook: { label: "Facebook", hosts: ["facebook.com", "fb.watch"] },
};

function inspectLocally(rawUrl: string): InspectResult {
  let parsed: URL;
  try { parsed = new URL(rawUrl); }
  catch { throw new Error("Enter a complete link, including https://."); }
  if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname) {
    throw new Error("Enter a valid http:// or https:// URL.");
  }
  const host = parsed.hostname.toLowerCase().replace(/\.$/, "");
  for (const [provider, item] of Object.entries(PROVIDERS)) {
    if (item.hosts.some((domain) => host === domain || host.endsWith("." + domain))) {
      return { provider, platform: item.label, url: parsed.href, status: "recognized",
        message: item.label + " link recognized. Available actions depend on official API support and your permissions." };
    }
  }
  return { provider: "other", platform: "Other website", url: parsed.href, status: "unsupported",
    message: "This source is not supported yet." };
}

export async function inspectUrl(rawUrl: string): Promise<InspectResult> {
  const localResult = inspectLocally(rawUrl);
  // Keep the frontend usable without a separately hosted API. If configured,
  // prefer the API response but fall back to local recognition if it is offline.
  if (!API) return localResult;
  try {
    const response = await fetch(API + "/api/inspect", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: localResult.url }), signal: AbortSignal.timeout(8000),
    });
    if (response.ok) return await response.json() as InspectResult;
  } catch { /* Optional API unavailable: use the local result. */ }
  return localResult;
}
