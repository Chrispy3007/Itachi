import { Innertube, Platform } from 'youtubei.js';
import { createWriteStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';
import { Readable } from 'node:stream';

Platform.shim.eval = async ({ output }) => new Function(output)();

function videoIdFromUrl(value) {
  const url = new URL(value);
  if (url.hostname.endsWith('youtu.be')) return url.pathname.split('/').filter(Boolean)[0];
  return url.searchParams.get('v') || url.pathname.match(/^\/(?:shorts|embed|live)\/([^/?]+)/)?.[1];
}

async function getInfo(url) {
  const id = videoIdFromUrl(url);
  if (!id) throw new Error('Could not identify a single YouTube video ID.');
  const yt = await Innertube.create({ lang: 'en', location: 'US' });
  const info = await yt.getBasicInfo(id);
  const status = info.playability_status?.status;
  if (status && status !== 'OK') {
    throw new Error(info.playability_status?.reason || `YouTube playability status: ${status}`);
  }
  return { yt, info, id };
}

const [action, url, arg] = process.argv.slice(2);
try {
  const { yt, info, id } = await getInfo(url);
  if (action === 'inspect') {
    const formats = (info.streaming_data?.formats || []).filter((f) => {
      const mime = f.mime_type || f.mimeType || '';
      return Number.isInteger(Number(f.itag)) && mime.startsWith('video/') && /codecs="[^"]*,\s*[^"]+"/i.test(mime);
    }).map((f) => ({
      format_id: `youtubejs:${f.itag}`,
      engine: 'youtubejs',
      ext: (f.mime_type || f.mimeType || '').match(/video\/([^;]+)/)?.[1] || 'mp4',
      resolution: f.quality_label || f.qualityLabel || (f.height ? `${f.height}p` : 'Video'),
      height: f.height || null,
      filesize: f.content_length || f.contentLength || null,
      fps: f.fps || null,
      needs_merge: false
    }));
    console.log(JSON.stringify({
      provider: 'youtube',
      status: formats.length ? 'available' : 'no_direct_formats',
      id,
      title: info.basic_info?.title || 'YouTube video',
      channel: info.basic_info?.author || null,
      thumbnail: info.basic_info?.thumbnail?.[0]?.url || null,
      duration: info.basic_info?.duration || null,
      webpage_url: url,
      engine: 'youtubejs',
      formats,
      message: formats.length ? 'Single-file formats exposed by YouTube.js.' : 'YouTube.js did not expose supported single-file formats.'
    }));
  } else if (action === 'download') {
    const itag = Number(arg);
    if (!Number.isInteger(itag) || itag <= 0) throw new Error('Invalid YouTube.js format ID.');
    const stream = await info.download({ itag });
    await pipeline(Readable.fromWeb(stream), createWriteStream(process.env.ITACHI_OUTPUT_PATH));
    console.log(JSON.stringify({ ok: true }));
  } else {
    throw new Error('Unknown YouTube.js adapter action.');
  }
} catch (error) {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
}
