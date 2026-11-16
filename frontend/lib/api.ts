const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
export type InspectResult = { provider: string; platform: string; url: string; status: string; message: string };

export async function inspectUrl(url: string): Promise<InspectResult> {
  const response = await fetch(`${API}/api/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Unable to inspect this link.');
  return data;
}
