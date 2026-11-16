'use client';
import { useState } from 'react';
import { ArrowDownToLine, AudioLines, CheckCircle2, CircleHelp, Clock3, ExternalLink, Instagram, Link2, Music2, ShieldCheck, Sparkles, Video, Youtube, Facebook, Loader2, Eye } from 'lucide-react';
import { inspectUrl, type InspectResult } from '../lib/api';

const platforms = [
  { id:'youtube', name:'YouTube', detail:'Authorized video workflows', icon:Youtube, color:'#f05a67' },
  { id:'instagram', name:'Instagram', detail:'Media from eligible accounts', icon:Instagram, color:'#dc718e' },
  { id:'spotify', name:'Spotify', detail:'Track and playlist metadata', icon:Music2, color:'#69c88a' },
  { id:'tiktok', name:'TikTok', detail:'Supported media workflows', icon:AudioLines, color:'#d4c5ca' },
  { id:'facebook', name:'Facebook', detail:'Eligible account-owned media', icon:Facebook, color:'#7e9de0' },
];

export default function Home() {
  const [url,setUrl] = useState('');
  const [result,setResult] = useState<InspectResult|null>(null);
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  async function inspect() {
    setError(''); setResult(null);
    if (!url.trim()) { setError('Paste a link to begin.'); return; }
    setBusy(true);
    try { setResult(await inspectUrl(url.trim())); }
    catch(e) { setError(e instanceof Error ? e.message : 'Something went wrong.'); }
    finally { setBusy(false); }
  }
  return <main className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Eye size={20}/></div><div>ITACHI<small>SHADOW MEDIA VAULT</small></div></div>
      <div className="side-label">HIDEOUT</div>
      <a className="nav active"><Video size={16}/> Link inspector</a>
      <a className="nav"><Clock3 size={16}/> Activity log <span className="soon">SOON</span></a>
      <a className="nav"><AudioLines size={16}/> Media tools <span className="soon">SOON</span></a>
      <div className="side-bottom"><ShieldCheck size={17}/><div><b>Quietly protected</b><p>Personal workspace. Your links stay yours.</p></div></div>
    </aside>
    <section className="main">
      <header className="topbar"><div className="crumb">The hideout <span>/</span> Link inspector</div><div className="top-pill"><span className="dot"/> PRIVATE WORKSPACE</div></header>
      <div className="content">
        <div className="eyebrow"><Sparkles size={13}/> <span>THE SHADOW MEDIA VAULT</span></div>
        <h1>Move in <span>silence.</span><br/>Keep your media close.</h1>
        <p className="subhead">A personal place to inspect links and organize media you own or have permission to save.</p>
        <section className="hero">
          <div className="hero-head"><div><h2>Inspect a media link</h2><p>Paste a supported URL. We’ll identify its source and available next steps.</p></div><div className="eye-mark"><Eye size={21}/></div></div>
          <div className="url-row"><Link2 size={17}/><input value={url} onChange={e=>setUrl(e.target.value)} onKeyDown={e=>e.key==='Enter'&&inspect()} placeholder="Paste a YouTube, Instagram, Spotify, TikTok or Facebook URL"/><button onClick={inspect} disabled={busy}>{busy?<Loader2 className="spin" size={16}/>:<><Sparkles size={15}/> Inspect link</>}</button></div>
          {error && <div className="error">{error}</div>}
          {result && <div className="result"><CheckCircle2 size={18}/><div className="result-copy"><b>{result.platform} link recognized</b><p>{result.message}</p><small>{result.url}</small></div><button className="secondary" onClick={()=>{setResult(null);setUrl('')}}>Clear</button></div>}
          <div className="supported"><strong>SUPPORTED SOURCES</strong>{platforms.map(p=><span className="source" key={p.id}>{p.name}</span>)}</div>
        </section>
        <div className="section-heading"><div><h2>Five platforms. One hideout.</h2><p>Platform-specific integrations will be enabled through official access.</p></div><span className="count">05 SOURCES</span></div>
        <div className="platform-grid">{platforms.map(p=>{const Icon=p.icon;return <article className="platform-card" key={p.id}><div className="platform-top"><div className="platform-icon" style={{color:p.color}}><Icon size={21}/></div><span className="status">READY FOR INTEGRATION</span></div><h3>{p.name}</h3><p>{p.detail}</p><div className="card-foot"><span>Integration details</span><ExternalLink size={13}/></div></article>})}</div>
        <div className="notice"><CircleHelp size={18}/><div><b>Respect the source. Protect the vault.</b><p>This starter does not bypass DRM, private-account restrictions, login walls or platform download controls. Spotify supports metadata and playlist information through its official API, not extracting streamed tracks. Download features will be enabled only for content you own or are authorized to save.</p></div></div>
        <footer>ITACHI <span>•</span> SHADOW MEDIA VAULT <span className="foot-right">VERSION 0.1.0</span></footer>
      </div>
    </section>
  </main>;
}
