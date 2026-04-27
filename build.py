#!/usr/bin/env python3
"""
OpenMark Icons — Build Script
Reads all SVGs from src/, generates docs/index.html, updates CATALOG.md count.
Run: python build.py
"""

import os
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
DOCS = ROOT / "docs"
CATALOG = ROOT / "CATALOG.md"
OUTPUT = DOCS / "index.html"

DOCS.mkdir(exist_ok=True)

# ── Read all icons from src/ ──────────────────────────────────────────────────
icons = []
for fname in sorted(SRC.glob("*.svg")):
    svg = fname.read_text(encoding="utf-8").strip()
    name = fname.stem
    parts = name.split("-", 1)
    category = parts[0]
    label = parts[1].replace("-", " ") if len(parts) > 1 else name
    icons.append({"name": name, "category": category, "label": label, "svg": svg})

if not icons:
    print("No SVG files found in src/. Nothing to build.")
    exit(1)

categories = sorted(set(i["category"] for i in icons))
icons_json = json.dumps(icons, ensure_ascii=False)
cat_buttons = "\n    ".join(
    f'<button class="cat-btn" data-cat="{c}">{c}</button>' for c in categories
)

print(f"Found {len(icons)} icons across {len(categories)} categories.")

# ── Build HTML ────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenMark Icons — Open Source Icon Library</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0a0a0f;--surface:#12121a;--surface2:#1a1a26;--border:#2a2a3d;--accent:#4fffb0;--accent2:#7b61ff;--text:#e8e8f0;--muted:#6b6b8a;--font-display:'Syne',sans-serif;--font-mono:'DM Mono',monospace}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--text);font-family:var(--font-mono);min-height:100vh;overflow-x:hidden}}
body::before{{content:'';position:fixed;inset:0;background-image:linear-gradient(var(--border) 1px,transparent 1px),linear-gradient(90deg,var(--border) 1px,transparent 1px);background-size:48px 48px;opacity:.25;pointer-events:none;z-index:0}}
header{{position:sticky;top:0;z-index:10;padding:0 24px;border-bottom:1px solid var(--border);background:rgba(10,10,15,.92);backdrop-filter:blur(12px);display:flex;align-items:center;justify-content:space-between;height:56px}}
.logo{{font-family:var(--font-display);font-weight:800;font-size:18px;letter-spacing:-.5px;color:var(--text);display:flex;align-items:center;gap:10px}}
.logo-dot{{width:8px;height:8px;background:var(--accent);border-radius:50%;box-shadow:0 0 12px var(--accent);animation:pulse 2s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.5;transform:scale(.75)}}}}
.header-links{{display:flex;gap:20px;align-items:center}}
.header-links a{{color:var(--muted);text-decoration:none;font-size:13px;transition:color .2s}}
.header-links a:hover{{color:var(--accent)}}
.gh-btn{{display:flex;align-items:center;gap:6px;background:var(--surface2);border:1px solid var(--border);color:var(--text)!important;padding:6px 14px;border-radius:6px;font-size:12px;font-family:var(--font-mono);transition:border-color .2s}}
.gh-btn:hover{{border-color:var(--accent)!important}}
.hero{{position:relative;z-index:1;padding:72px 24px 56px;max-width:900px;margin:0 auto}}
.hero-tag{{display:inline-block;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--accent);border:1px solid var(--accent);padding:4px 10px;border-radius:3px;margin-bottom:24px}}
.hero h1{{font-family:var(--font-display);font-size:clamp(36px,6vw,64px);font-weight:800;line-height:1.05;letter-spacing:-2px;margin-bottom:20px}}
.hero h1 span{{color:var(--accent)}}
.hero p{{font-size:15px;color:var(--muted);line-height:1.7;max-width:560px;margin-bottom:36px}}
.hero-stats{{display:flex;gap:36px;flex-wrap:wrap}}
.stat{{display:flex;flex-direction:column;gap:2px}}
.stat-num{{font-family:var(--font-display);font-size:28px;font-weight:800;letter-spacing:-1px}}
.stat-label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px}}
.install-strip{{position:relative;z-index:1;max-width:900px;margin:0 auto 48px;padding:0 24px}}
.install-tabs{{display:flex;gap:2px;border-bottom:1px solid var(--border)}}
.install-tab{{font-family:var(--font-mono);font-size:12px;padding:8px 16px;background:none;border:none;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:color .2s}}
.install-tab.active{{color:var(--accent);border-bottom-color:var(--accent)}}
.install-box{{background:var(--surface);border:1px solid var(--border);border-top:none;border-radius:0 0 8px 8px;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
.install-cmd{{font-family:var(--font-mono);font-size:14px;color:var(--accent);flex:1}}
.install-cmd .dim{{color:var(--muted)}}
.copy-btn{{background:none;border:1px solid var(--border);color:var(--muted);font-family:var(--font-mono);font-size:11px;padding:4px 12px;border-radius:4px;cursor:pointer;transition:all .2s;white-space:nowrap}}
.copy-btn:hover,.copy-btn.copied{{border-color:var(--accent);color:var(--accent)}}
.browser{{position:relative;z-index:1;max-width:1200px;margin:0 auto;padding:0 24px 80px}}
.browser-header{{display:flex;align-items:center;gap:16px;margin-bottom:20px;flex-wrap:wrap}}
.section-label{{font-family:var(--font-display);font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted)}}
.search-wrap{{flex:1;min-width:200px;max-width:360px;position:relative}}
.search-wrap svg{{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}}
#search{{width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:9px 12px 9px 36px;font-family:var(--font-mono);font-size:13px;color:var(--text);outline:none;transition:border-color .2s}}
#search:focus{{border-color:var(--accent2)}}
#search::placeholder{{color:var(--muted)}}
.cats{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:24px}}
.cat-btn{{background:var(--surface);border:1px solid var(--border);color:var(--muted);font-family:var(--font-mono);font-size:11px;padding:5px 12px;border-radius:4px;cursor:pointer;transition:all .15s;text-transform:uppercase;letter-spacing:.5px}}
.cat-btn:hover{{border-color:var(--accent2);color:var(--text)}}
.cat-btn.active{{background:var(--accent2);border-color:var(--accent2);color:white}}
#icon-count{{font-size:12px;color:var(--muted);margin-bottom:20px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:12px}}
.icon-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px 12px 14px;display:flex;flex-direction:column;align-items:center;gap:10px;cursor:pointer;transition:border-color .15s,background .15s,transform .15s;position:relative;user-select:none}}
.icon-card:hover{{border-color:var(--accent2);background:var(--surface2);transform:translateY(-2px)}}
.icon-preview{{width:36px;height:36px;display:flex;align-items:center;justify-content:center;color:var(--text)}}
.icon-preview svg{{width:28px;height:28px}}
.icon-name{{font-family:var(--font-mono);font-size:10px;color:var(--muted);text-align:center;line-height:1.4;word-break:break-all}}
.new-badge{{position:absolute;top:7px;left:7px;background:var(--accent);color:var(--bg);font-size:8px;font-weight:700;padding:2px 5px;border-radius:3px;text-transform:uppercase;letter-spacing:.5px;display:none}}
.icon-card[data-new="true"] .new-badge{{display:block}}
.no-results{{grid-column:1/-1;text-align:center;padding:60px 0;color:var(--muted);font-size:13px}}
#detail{{position:fixed;bottom:0;left:0;right:0;background:var(--surface);border-top:1px solid var(--border);padding:20px 24px;z-index:100;transform:translateY(100%);transition:transform .3s cubic-bezier(.16,1,.3,1);display:flex;align-items:center;gap:24px;flex-wrap:wrap}}
#detail.open{{transform:translateY(0)}}
.detail-icon{{width:56px;height:56px;background:var(--surface2);border:1px solid var(--border);border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--text);flex-shrink:0}}
.detail-icon svg{{width:32px;height:32px}}
.detail-info{{flex:1;min-width:160px}}
.detail-name{{font-family:var(--font-display);font-size:18px;font-weight:700;margin-bottom:4px}}
.detail-cat{{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}}
.detail-actions{{display:flex;gap:8px;flex-wrap:wrap}}
.detail-btn{{font-family:var(--font-mono);font-size:12px;padding:8px 16px;border-radius:6px;cursor:pointer;border:1px solid var(--border);background:var(--surface2);color:var(--text);transition:all .15s}}
.detail-btn:hover{{border-color:var(--accent);color:var(--accent)}}
.detail-btn.primary{{background:var(--accent);border-color:var(--accent);color:var(--bg);font-weight:500}}
.detail-btn.primary:hover{{background:#3de89a}}
#detail-close{{background:none;border:none;color:var(--muted);cursor:pointer;font-size:22px;line-height:1;padding:4px;margin-left:auto}}
.usage{{position:relative;z-index:1;max-width:900px;margin:0 auto;padding:64px 24px 80px;border-top:1px solid var(--border)}}
.usage h2{{font-family:var(--font-display);font-size:32px;font-weight:800;letter-spacing:-1px;margin-bottom:8px}}
.usage-subtitle{{color:var(--muted);font-size:14px;margin-bottom:40px}}
.usage-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}}
.usage-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:24px}}
.usage-card h3{{font-family:var(--font-display);font-size:14px;font-weight:700;margin-bottom:12px;color:var(--accent)}}
.code-block{{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:14px 16px;font-family:var(--font-mono);font-size:12px;color:#a8b1c0;line-height:1.7;overflow-x:auto;white-space:pre}}
.code-block .kw{{color:var(--accent2)}}.code-block .str{{color:var(--accent)}}.code-block .tag{{color:#ff7b7b}}.code-block .attr{{color:#ffc87b}}.code-block .cm{{color:var(--muted);font-style:italic}}
footer{{position:relative;z-index:1;border-top:1px solid var(--border);padding:24px;text-align:center;font-size:12px;color:var(--muted)}}
footer a{{color:var(--muted);text-decoration:none}}
footer a:hover{{color:var(--accent)}}
@media(max-width:600px){{.hero h1{{letter-spacing:-1px}}.hero-stats{{gap:20px}}.grid{{grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:8px}}.header-links a:not(.gh-btn){{display:none}}}}
</style>
</head>
<body>
<header>
  <div class="logo"><div class="logo-dot"></div>OpenMark Icons</div>
  <div class="header-links">
    <a href="#how-to-use">Usage</a>
    <a href="https://github.com/brightfred/icon-library-project" class="gh-btn" target="_blank">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.49.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.08.63-1.33-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.56 9.56 0 0 1 12 6.8c.85 0 1.71.11 2.51.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10.01 10.01 0 0 0 22 12c0-5.52-4.48-10-10-10z"/></svg>
      GitHub
    </a>
  </div>
</header>

<section class="hero">
  <div class="hero-tag">Open Source &middot; Free Forever &middot; AI-Ready</div>
  <h1>Icons for<br><span>science, engineering<br>&amp; the web.</span></h1>
  <p>A free, open source SVG icon library built for developers and AI systems. Stroke-only, 24px grid, currentColor. Works in React, Vue, plain HTML &mdash; anything.</p>
  <div class="hero-stats">
    <div class="stat"><span class="stat-num">{len(icons)}</span><span class="stat-label">Icons</span></div>
    <div class="stat"><span class="stat-num">{len(categories)}</span><span class="stat-label">Categories</span></div>
    <div class="stat"><span class="stat-num">MIT</span><span class="stat-label">License</span></div>
    <div class="stat"><span class="stat-num">24px</span><span class="stat-label">Grid</span></div>
  </div>
</section>

<section class="install-strip">
  <div class="install-tabs">
    <button class="install-tab active" data-pkg="npm">npm</button>
    <button class="install-tab" data-pkg="svg">SVG direct</button>
    <button class="install-tab" data-pkg="cdn">CDN</button>
  </div>
  <div class="install-box">
    <div class="install-cmd" id="install-cmd"><span class="dim">$ </span>npm install openmark-icons</div>
    <button class="copy-btn" id="install-copy">copy</button>
  </div>
</section>

<section class="browser">
  <div class="browser-header">
    <span class="section-label">Browse</span>
    <div class="search-wrap">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="10.5" cy="10.5" r="6.5"/><line x1="15.5" y1="15.5" x2="21" y2="21"/></svg>
      <input type="text" id="search" placeholder="search icons..." autocomplete="off" spellcheck="false">
    </div>
  </div>
  <div class="cats">
    <button class="cat-btn active" data-cat="all">All</button>
    {cat_buttons}
  </div>
  <div id="icon-count"></div>
  <div class="grid" id="grid"></div>
</section>

<section class="usage" id="how-to-use">
  <h2>How to use</h2>
  <p class="usage-subtitle">Click any icon to copy its SVG. Or use one of these methods.</p>
  <div class="usage-grid">
    <div class="usage-card">
      <h3>Plain HTML</h3>
      <div class="code-block"><span class="tag">&lt;div</span> <span class="attr">class</span>=<span class="str">"icon"</span><span class="tag">&gt;</span>
  <span class="tag">&lt;svg</span> <span class="attr">viewBox</span>=<span class="str">"0 0 24 24"</span>
       <span class="attr">stroke</span>=<span class="str">"currentColor"</span><span class="tag">&gt;</span>
    ...
  <span class="tag">&lt;/svg&gt;</span>
<span class="tag">&lt;/div&gt;</span></div>
    </div>
    <div class="usage-card">
      <h3>React / JSX</h3>
      <div class="code-block"><span class="kw">export const</span> Icon = () <span class="kw">=&gt;</span> (
  <span class="tag">&lt;svg</span> <span class="attr">viewBox</span>=<span class="str">"0 0 24 24"</span>
       <span class="attr">stroke</span>=<span class="str">"currentColor"</span>
       <span class="attr">strokeWidth</span>=<span class="str">{{2}}</span><span class="tag">&gt;</span>
    ...
  <span class="tag">&lt;/svg&gt;</span>
)</div>
    </div>
    <div class="usage-card">
      <h3>CSS sizing</h3>
      <div class="code-block"><span class="attr">.icon</span> {{
  <span class="kw">width</span>: <span class="str">24px</span>;
  <span class="kw">height</span>: <span class="str">24px</span>;
  <span class="kw">color</span>: <span class="str">#4fffb0</span>;
}}
<span class="cm">/* stroke = currentColor */</span></div>
    </div>
    <div class="usage-card">
      <h3>For AI systems</h3>
      <div class="code-block"><span class="cm"># machine-readable catalog</span>
GET /icons.json

<span class="cm"># fields: name, category,</span>
<span class="cm"># label, tags, svg</span>
<span class="cm"># MIT licensed</span></div>
    </div>
  </div>
</section>

<footer>
  <p>OpenMark Icons &mdash; MIT License &mdash; <a href="https://github.com/brightfred/icon-library-project" target="_blank">GitHub</a> &mdash; Built with Claude Code</p>
</footer>

<div id="detail">
  <div class="detail-icon" id="detail-icon"></div>
  <div class="detail-info">
    <div class="detail-name" id="detail-name"></div>
    <div class="detail-cat" id="detail-cat"></div>
  </div>
  <div class="detail-actions">
    <button class="detail-btn primary" id="detail-copy-svg">Copy SVG</button>
    <button class="detail-btn" id="detail-copy-name">Copy name</button>
    <button class="detail-btn" id="detail-download">Download .svg</button>
  </div>
  <button id="detail-close">&times;</button>
</div>

<script>
const ICONS = {icons_json};
const grid = document.getElementById('grid');
const search = document.getElementById('search');
const countEl = document.getElementById('icon-count');
let activecat = 'all';
let selected = null;

function render() {{
  const q = search.value.toLowerCase().trim();
  const filtered = ICONS.filter(icon => {{
    const matchCat = activecat === 'all' || icon.category === activecat;
    const matchQ = !q || icon.name.includes(q) || icon.label.includes(q) || icon.category.includes(q);
    return matchCat && matchQ;
  }});
  countEl.textContent = filtered.length + ' icon' + (filtered.length !== 1 ? 's' : '');
  if (!filtered.length) {{ grid.innerHTML = '<div class="no-results">No icons found.</div>'; return; }}
  const sorted = [...filtered].reverse();
  grid.innerHTML = sorted.map((icon, i) => `
    <div class="icon-card" data-name="${{icon.name}}" data-new="${{i < 3 ? 'true' : 'false'}}">
      <div class="new-badge">new</div>
      <div class="icon-preview">${{icon.svg}}</div>
      <div class="icon-name">${{icon.name}}</div>
    </div>
  `).join('');
  grid.querySelectorAll('.icon-card').forEach(card => {{
    card.addEventListener('click', () => openDetail(card.dataset.name));
  }});
}}

function openDetail(name) {{
  const icon = ICONS.find(i => i.name === name);
  if (!icon) return;
  selected = icon;
  document.getElementById('detail-icon').innerHTML = icon.svg;
  document.getElementById('detail-name').textContent = icon.name;
  document.getElementById('detail-cat').textContent = icon.category + ' · 24x24 · stroke · currentColor';
  document.getElementById('detail').classList.add('open');
}}

document.getElementById('detail-close').addEventListener('click', () => {{
  document.getElementById('detail').classList.remove('open');
  selected = null;
}});

document.getElementById('detail-copy-svg').addEventListener('click', () => {{
  if (!selected) return;
  navigator.clipboard.writeText(selected.svg);
  const btn = document.getElementById('detail-copy-svg');
  btn.textContent = 'Copied!';
  setTimeout(() => btn.textContent = 'Copy SVG', 1500);
}});

document.getElementById('detail-copy-name').addEventListener('click', () => {{
  if (!selected) return;
  navigator.clipboard.writeText(selected.name);
  const btn = document.getElementById('detail-copy-name');
  btn.textContent = 'Copied!';
  setTimeout(() => btn.textContent = 'Copy name', 1500);
}});

document.getElementById('detail-download').addEventListener('click', () => {{
  if (!selected) return;
  const blob = new Blob([selected.svg], {{type: 'image/svg+xml'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = selected.name + '.svg';
  a.click();
}});

document.querySelectorAll('.cat-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activecat = btn.dataset.cat;
    render();
  }});
}});

search.addEventListener('input', render);

const cmds = {{
  npm: '<span class="dim">$ </span>npm install openmark-icons',
  svg: '<span class="dim">&#8594; </span>click any icon &rarr; Copy SVG &rarr; paste',
  cdn: '<span class="dim">&#8594; </span>coming soon &mdash; star the repo to get notified'
}};

document.querySelectorAll('.install-tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.install-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('install-cmd').innerHTML = cmds[tab.dataset.pkg];
  }});
}});

document.getElementById('install-copy').addEventListener('click', () => {{
  const text = document.getElementById('install-cmd').textContent;
  navigator.clipboard.writeText(text);
  const btn = document.getElementById('install-copy');
  btn.textContent = 'copied!';
  btn.classList.add('copied');
  setTimeout(() => {{ btn.textContent = 'copy'; btn.classList.remove('copied'); }}, 1500);
}});

document.addEventListener('click', e => {{
  const detail = document.getElementById('detail');
  if (detail.classList.contains('open') && !detail.contains(e.target) && !e.target.closest('.icon-card')) {{
    detail.classList.remove('open');
    selected = null;
  }}
}});

render();
</script>
</body>
</html>"""

OUTPUT.write_text(html, encoding="utf-8")
print(f"Built docs/index.html with {len(icons)} icons.")

# ── Build review.html ─────────────────────────────────────────────────────────
cards = ""
for icon in icons:
    n = icon["name"]
    cards += f"""
    <div class="card" id="{n}">
      <div class="icon-wrap">{icon["svg"]}</div>
      <div class="label">{n}</div>
      <div class="actions">
        <button onclick="flag('{n}','good')" class="btn good">Good</button>
        <button onclick="flag('{n}','too-generic')" class="btn bad">Generic</button>
        <button onclick="flag('{n}','too-complex')" class="btn bad">Complex</button>
        <button onclick="flag('{n}','unclear')" class="btn bad">Unclear</button>
        <button onclick="flag('{n}','wrong-style')" class="btn bad">Style</button>
      </div>
      <div class="status" id="status-{n}">needs-review</div>
    </div>"""

review_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Icon Review — {len(icons)} icons</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; background: #f3f4f6; padding: 24px; }}
  h1 {{ font-size: 22px; font-weight: 700; color: #111827; margin-bottom: 4px; }}
  .subtitle {{ font-size: 13px; color: #6b7280; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 16px; }}
  .card {{ background: white; border-radius: 10px; padding: 20px 12px 14px; text-align: center; border: 2px solid #e5e7eb; transition: border-color 0.2s; }}
  .card.flagged-good {{ border-color: #22c55e; background: #f0fdf4; }}
  .card.flagged-bad {{ border-color: #ef4444; background: #fef2f2; }}
  .icon-wrap {{ display: flex; align-items: center; justify-content: center; height: 48px; margin-bottom: 10px; }}
  .icon-wrap svg {{ width: 32px; height: 32px; color: #1a56db; }}
  .label {{ font-size: 11px; color: #374151; margin-bottom: 10px; word-break: break-all; line-height: 1.4; }}
  .actions {{ display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; margin-bottom: 8px; }}
  .btn {{ font-size: 10px; padding: 3px 7px; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; }}
  .btn.good {{ background: #dcfce7; color: #166534; }}
  .btn.bad {{ background: #fee2e2; color: #991b1b; }}
  .btn:hover {{ opacity: 0.8; }}
  .status {{ font-size: 10px; color: #9ca3af; font-style: italic; }}
  .summary {{ margin-top: 28px; background: white; border-radius: 10px; padding: 16px 20px; border: 1px solid #e5e7eb; }}
  .summary h2 {{ font-size: 14px; font-weight: 700; margin-bottom: 10px; color: #111827; }}
  #log {{ font-size: 12px; color: #374151; line-height: 2; }}
  .copy-btn {{ margin-top: 10px; font-size: 12px; padding: 6px 14px; background: #1a56db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }}
  .copy-btn:hover {{ background: #1e40af; }}
  .filter-bar {{ display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}
  .filter-btn {{ font-size: 11px; padding: 4px 12px; border: 1px solid #d1d5db; border-radius: 4px; background: white; cursor: pointer; }}
  .filter-btn.active {{ background: #1a56db; color: white; border-color: #1a56db; }}
</style>
</head>
<body>
<h1>Icon Review</h1>
<p class="subtitle">{len(icons)} icons — flag then copy the log for Claude Code</p>
<div class="filter-bar">
  <button class="filter-btn active" onclick="filterCat('all')">All</button>
  {"".join(f'<button class="filter-btn" onclick="filterCat(\'{c}\')">{c}</button>' for c in categories)}
</div>
<div class="grid" id="grid">{cards}</div>
<div class="summary">
  <h2>Review Log</h2>
  <div id="log">No flags yet.</div>
  <button class="copy-btn" onclick="copyLog()">Copy log for Claude Code</button>
</div>
<script>
  const flags = {{}};
  function flag(name, status) {{
    flags[name] = status;
    const card = document.getElementById(name);
    card.className = 'card ' + (status === 'good' ? 'flagged-good' : 'flagged-bad');
    document.getElementById('status-' + name).textContent = status;
    renderLog();
  }}
  function renderLog() {{
    const entries = Object.entries(flags);
    if (!entries.length) {{ document.getElementById('log').textContent = 'No flags yet.'; return; }}
    document.getElementById('log').innerHTML = entries
      .map(([name, status]) => `<span style="color:${{status==='good'?'#166534':'#991b1b'}}">${{name}}: ${{status}}</span>`)
      .join('<br>');
  }}
  function copyLog() {{
    const entries = Object.entries(flags);
    if (!entries.length) {{ alert('No flags yet.'); return; }}
    const text = entries.map(([name, status]) => `${{name}}: ${{status}}`).join('\\n');
    navigator.clipboard.writeText(text).then(() => alert('Copied!'));
  }}
  function filterCat(cat) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.card').forEach(card => {{
      card.style.display = cat === 'all' || card.id.startsWith(cat) ? '' : 'none';
    }});
  }}
</script>
</body>
</html>"""

review_path = ROOT / "review.html"
review_path.write_text(review_html, encoding="utf-8")
print(f"Built review.html with {len(icons)} icons.")

# ── Update CATALOG.md total count ─────────────────────────────────────────────
if CATALOG.exists():
    content = CATALOG.read_text(encoding="utf-8")
    updated = re.sub(r"\*\*Total icons:\*\* \d+", f"**Total icons:** {len(icons)}", content)
    from datetime import date
    updated = re.sub(r"\*\*Last updated:\*\* .+", f"**Last updated:** {date.today()}", updated)
    CATALOG.write_text(updated, encoding="utf-8")
    print(f"Updated CATALOG.md — total: {len(icons)}, date: {date.today()}")

print("Done.")