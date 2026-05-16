const socket = io();
const STATE = { themes:[], selectedThemes:[], articles:[], presets:{}, voices:[], themesConfig:{}, currentTheme:'dark', pendingEdits:{}, notifs:[] };

window.addEventListener('load', () => {
  setTimeout(() => document.getElementById('startup').classList.add('done'), 2200);
  initDotCanvas();
  loadTheme(localStorage.getItem('hd_theme') || 'dark');
  // System theme auto (#23)
  if (!localStorage.getItem('hd_theme') && window.matchMedia('(prefers-color-scheme: light)').matches) loadTheme('light');
});

socket.on('connect', async () => {
  const r = await fetch('/api/bootstrap').then(r=>r.json());
  STATE.presets = r.presets; STATE.voices = r.voices; STATE.themesConfig = r.themes;
  renderThemeSwitcher();

  const ms = document.getElementById('model');
  const models = r.models.local;
  ms.innerHTML = models.length ? models.map(m=>`<option>${m.name}</option>`).join('') : '<option value="">— none —</option>';

  document.getElementById('voice').innerHTML = r.voices.map(v=>`<option>${v}</option>`).join('');
  document.getElementById('voice2').innerHTML = r.voices.map(v=>`<option>${v}</option>`).join('');
  document.getElementById('style').innerHTML = Object.keys(r.presets.prompt_presets).map(k=>`<option value="${k}">${k}</option>`).join('');
  document.getElementById('template').innerHTML = '<option value="">— none —</option>' + Object.keys(r.presets.templates).map(k=>`<option value="${k}">${k}</option>`).join('');
  document.getElementById('sourcePresets').innerHTML = Object.entries(r.presets.source_presets).map(([k,v])=>`<span class="chip" onclick="loadPreset('${k}')">${k}<span class="count">${v.length}</span></span>`).join('');
});

function renderThemeSwitcher() {
  document.getElementById('themeSwitcher').innerHTML = Object.entries(STATE.themesConfig).map(([k,t]) =>
    `<div class="theme-btn ${k===STATE.currentTheme?'active':''}" data-theme-key="${k}" onclick="loadTheme('${k}')"><span class="material-icons-round">${t.icon}</span>${t.label}</div>`).join('');
}

function loadTheme(key) {
  STATE.currentTheme = key; localStorage.setItem('hd_theme', key);
  const t = STATE.themesConfig[key];
  if (t) Object.entries(t.vars).forEach(([k,v]) => document.documentElement.style.setProperty(k, v));
  document.documentElement.setAttribute('data-theme', key);
  document.querySelectorAll('.theme-btn').forEach(b => b.classList.toggle('active', b.dataset.themeKey === key));
}

function initDotCanvas() {
  const c = document.getElementById('dotCanvas'); const ctx = c.getContext('2d');
  let dots = [];
  function resize() { c.width = innerWidth; c.height = innerHeight;
    dots = Array.from({length:50}, () => ({x:Math.random()*c.width, y:Math.random()*c.height, vx:(Math.random()-.5)*.3, vy:(Math.random()-.5)*.3, r:Math.random()*1.5+.5})); }
  resize(); addEventListener('resize', resize);
  function loop() {
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#4a9eff';
    ctx.clearRect(0,0,c.width,c.height);
    dots.forEach(d => { d.x+=d.vx; d.y+=d.vy;
      if(d.x<0||d.x>c.width) d.vx*=-1; if(d.y<0||d.y>c.height) d.vy*=-1;
      ctx.beginPath(); ctx.arc(d.x,d.y,d.r,0,Math.PI*2); ctx.fillStyle = accent+'33'; ctx.fill(); });
    requestAnimationFrame(loop);
  }
  if (!window._dots) { window._dots = true; loop(); }
}

document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
  t.classList.add('active');
  document.querySelector(`.panel[data-panel="${t.dataset.tab}"]`).classList.add('active');
  if (t.dataset.tab==='history') loadHistory();
  if (t.dataset.tab==='settings') { loadHealth(); loadCacheStats(); }
}));

document.addEventListener('click', e => {
  const btn = e.target.closest('.btn');
  if (!btn) return;
  const r = document.createElement('span'); r.className = 'ripple';
  const rect = btn.getBoundingClientRect();
  r.style.width = r.style.height = Math.max(rect.width,rect.height) + 'px';
  r.style.left = (e.clientX-rect.left-rect.width/2) + 'px';
  r.style.top = (e.clientY-rect.top-rect.height/2) + 'px';
  btn.appendChild(r); setTimeout(()=>r.remove(), 600);
});

// Socket
socket.on('log', d => {
  const log = document.getElementById('log');
  log.innerHTML += `<div class="log-entry ${d.level}"><span class="log-ts">${d.time}</span>${d.msg}</div>`;
  log.scrollTop = log.scrollHeight;
});
socket.on('progress', d => {
  document.getElementById('progFill').style.width = d.percent + '%';
  document.getElementById('progPct').textContent = d.percent + '%';
  document.getElementById('progStep').textContent = `${d.step} · ${d.label}`;
  document.getElementById('progFill').classList.toggle('done', d.percent>=100);
});
socket.on('status', d => {
  const c = document.getElementById('statusCard');
  c.className = 'status-card show ' + d.level;
  document.getElementById('statusText').textContent = d.status;
});
socket.on('themes_ready', d => { STATE.themes = d.themes; renderThemes(); toast('themes ready'); document.querySelector('[data-tab="themes"]').click(); });
socket.on('articles_ready', d => {
  STATE.articles = d.articles; renderArticles();
  if (d.trends && d.trends.length) {
    document.getElementById('trends').innerHTML = '<strong>🔥 trending now:</strong> ' +
      d.trends.map(t => `<span class="trend-pill">${t.keyword} +${t.growth}%</span>`).join('');
  }
  toast(`${d.articles.length} articles`); document.querySelector('[data-tab="articles"]').click();
});
socket.on('result_ready', r => document.getElementById('results').insertAdjacentHTML('beforeend', renderResult(r)));
socket.on('job_complete', d => {
  toast('pipeline complete');
  if (d.clusters && d.clusters.length) {
    document.getElementById('clusters').innerHTML = '<h3 style="margin-bottom:8px">🧬 topic clusters</h3>' +
      d.clusters.map(c => `<div class="result-card"><h3>Cluster ${c.cluster} (${c.size} articles)</h3><div class="rc-summary">${c.articles.map(a=>a.title).join(' · ')}</div></div>`).join('');
  }
  document.querySelector('[data-tab="results"]').click();
});
socket.on('notification', n => {
  STATE.notifs.unshift(n);
  document.getElementById('notifBadge').style.display = '';
  document.getElementById('notifBadge').textContent = STATE.notifs.length;
  renderNotifs();
});
socket.on('preview', d => {
  const body = document.getElementById('previewBody');
  const html = d.kind === 'video' ? `<video src="/${d.path}" autoplay muted loop class="preview-thumb"></video>` : `<div class="preview-thumb"><img src="/${d.path}"></div>`;
  body.insertAdjacentHTML('afterbegin', html);
  if (body.children.length > 12) body.lastChild.remove();
});

function renderThemes(filter="") {
  document.getElementById('themes').innerHTML = STATE.themes
    .filter(t => t.name.includes(filter.toLowerCase()))
    .map(t => `<span class="chip ${STATE.selectedThemes.includes(t.name)?'active':''}" onclick="toggleTheme('${t.name.replace(/'/g,"\\'")}')">${t.name}<span class="count">${t.confidence}%</span></span>`).join('');
}

function renderArticles() {
  document.getElementById('articles').innerHTML = STATE.articles.map(a => {
    const s = a.sentiment || {label:'neutral'};
    return `<div class="article-item">
      <div class="at-title">${a.title}</div>
      <div class="at-meta">
        <span>${a.source}</span>
        <span class="trust-badge ${a.trust>80?'high':a.trust>50?'med':'low'}">trust ${a.trust}</span>
        <span class="sentiment-badge ${s.label}">${s.label}</span>
        ${a.date?`<span>${a.date}</span>`:''}
      </div>
      <div class="at-preview">${a.preview||''}</div>
    </div>`;
  }).join('');
}

function renderResult(r) {
  const a = [];
  if (r.assets.videos) r.assets.videos.forEach(v => a.push(`<a class="asset-link" href="/${v}" target="_blank"><span class="material-icons-round">play_circle</span>video</a>`));
  if (r.assets.images) r.assets.images.forEach(i => a.push(`<a class="asset-link" href="/${i}" target="_blank"><span class="material-icons-round">image</span>img</a>`));
  if (r.assets.audio) a.push(`<a class="asset-link" href="/${r.assets.audio}" target="_blank"><span class="material-icons-round">music_note</span>audio</a>`);
  if (r.assets.srt) a.push(`<a class="asset-link" href="/${r.assets.srt}" target="_blank"><span class="material-icons-round">subtitles</span>srt</a>`);
  if (r.assets.thumbnail) a.push(`<a class="asset-link" href="/${r.assets.thumbnail}" target="_blank"><span class="material-icons-round">image</span>thumb</a>`);
  const s = r.sentiment || {label:'neutral'};
  return `<div class="result-card">
    <h3>${r.title} <span class="sentiment-badge ${s.label}">${s.label}</span></h3>
    <div class="rc-meta">${r.source} · ${r.language} · trust:${r.trust}</div>
    <div class="rc-summary">${r.summary}</div>
    ${r.variant_b ? `<details style="margin:8px 0"><summary style="cursor:pointer;color:var(--accent);font-size:11px">▸ Variant B (A/B test)</summary><div class="rc-summary" style="margin-top:6px">${r.variant_b}</div></details>` : ''}
    <div class="rc-assets">${a.join('')} <span class="asset-link" style="cursor:pointer" onclick="copyText(\`${(r.summary||'').replace(/`/g,"'")}\`)"><span class="material-icons-round">content_copy</span>copy</span></div>
  </div>`;
}

function toggleTheme(name) {
  if (STATE.selectedThemes.includes(name)) STATE.selectedThemes = STATE.selectedThemes.filter(t=>t!==name);
  else STATE.selectedThemes.push(name);
  renderThemes(document.getElementById('themeSearch').value);
}
function filterThemes() { renderThemes(document.getElementById('themeSearch').value); }
function loadPreset(name) { document.getElementById('sites').value = STATE.presets.source_presets[name].join('\n'); toast('loaded '+name); }
function applyTemplate() {
  const t = document.getElementById('template').value; if (!t) return;
  const tpl = STATE.presets.templates[t];
  if (tpl.style) document.getElementById('style').value = tpl.style;
  if (tpl.voice) document.getElementById('voice').value = tpl.voice;
  if ('shorts' in tpl) document.getElementById('shorts').checked = tpl.shorts;
  toast('template: '+t);
}

async function scrapeThemes() {
  const sites = document.getElementById('sites').value.split('\n').filter(s=>s.trim());
  if (!sites.length) return toast('no sites');
  await fetch('/api/scrape-themes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sites})});
}
async function scrapeArticles() {
  await fetch('/api/scrape-articles',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({themes:STATE.selectedThemes, article:document.getElementById('article').value})});
}

async function estimateCost() {
  const opts = buildOpts();
  const r = await fetch('/api/estimate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(opts)}).then(r=>r.json());
  document.getElementById('costText').innerHTML = `~${r.human_time} · ~$${r.estimated_cost_usd} · ${r.videos} videos · ${r.images} images`;
}

async function previewSummaries() {
  const opts = buildOpts();
  const r = await fetch('/api/summarize-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(opts)}).then(r=>r.json());
  STATE.pendingEdits = {};
  document.getElementById('editList').innerHTML = r.summaries.map((s,i) => `
    <div class="edit-card">
      <h4>${s.title} <span class="sentiment-badge ${s.sentiment.label}">${s.sentiment.label}</span></h4>
      <textarea id="edit_${i}" oninput="STATE.pendingEdits['${i}']=this.value">${s.summary}</textarea>
      <button class="btn" onclick="regenerate(${i})"><span class="material-icons-round">refresh</span>regenerate</button>
    </div>`).join('');
  r.summaries.forEach((s,i) => STATE.pendingEdits[i] = s.summary);
}

async function regenerate(i) {
  const opts = buildOpts(); opts.max_articles = i+1;
  const r = await fetch('/api/summarize-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(opts)}).then(r=>r.json());
  if (r.summaries[i]) { document.getElementById(`edit_${i}`).value = r.summaries[i].summary; STATE.pendingEdits[i] = r.summaries[i].summary; }
}

function buildOpts() {
  return {
    provider:val('provider'), model:val('model'), style:val('style'),
    voice:val('voice'), voice2:val('voice2'),
    translate_to:val('translate')||null, template:val('template'),
    max_articles:+val('max')||2, image_count:+val('imgCount')||2,
    video_url:val('videoUrl'), video_prompt:val('videoPrompt'),
    api_key:val('apiKey'), elevenlabs_key:val('elevenKey'),
    shorts:chk('shorts'), split:chk('split'),
    gen_video:chk('genVideo'), gen_images:chk('genImages'),
    gen_tts:chk('genTts'), gen_thumb:chk('genThumb'),
    use_whisper:chk('useWhisper'), add_music:chk('addMusic'),
    dialogue_mode:chk('dialogueMode'), concurrent:chk('concurrent'),
    ab_test:chk('abTest'), auto_publish:chk('autoPublish')
  };
}

async function generate() {
  document.getElementById('results').innerHTML = '';
  document.getElementById('previewBody').innerHTML = '';
  const opts = buildOpts();
  opts.edited_summaries = STATE.pendingEdits;
  await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(opts)});
}

async function control(a) { await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:a})}); toast(a); }

async function doExport() {
  const fmt = val('exportFmt');
  const body = {format:fmt};
  if (fmt==='notion') { body.notion_key = val('notionKey'); body.database_id = val('notionDb'); }
  const r = await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(r=>r.json());
  if (r.path) { window.open(r.path,'_blank'); toast('exported'); }
  else if (r.ok) toast('pushed to notion');
}

async function factCheck() {
  const claim = document.getElementById('factClaim').value;
  const r = await fetch('/api/fact-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({claim})}).then(r=>r.json());
  document.getElementById('factResult').innerHTML = `<div class="result-card"><h3>Confidence: ${r.confidence}%</h3>
    <div class="rc-meta">${r.matches} sources matched</div>
    <div class="rc-summary">${r.sources.join(', ') || 'no matches'}</div></div>`;
}

async function schedule() {
  await fetch('/api/schedule',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:val('schedId'), interval:+val('schedInt')})});
  toast('scheduled');
  loadSchedules();
}
async function loadSchedules() {
  const r = await fetch('/api/scheduled').then(r=>r.json());
  document.getElementById('schedList').innerHTML = r.map(s=>`<div class="article-item"><strong>${s.id}</strong><br><small>next: ${s.next}</small></div>`).join('') || '<em>none</em>';
}

async function loadHistory() {
  const h = await fetch('/api/history').then(r=>r.json());
  document.getElementById('historyList').innerHTML = h.length
    ? h.map(j=>`<div class="article-item"><div class="at-title">${j.summary}</div><div class="at-meta">${j.timestamp}</div></div>`).join('')
    : '<div style="color:var(--muted);text-align:center;padding:40px">no history</div>';
}

async function loadHealth() {
  const r = await fetch('/api/source-health').then(r=>r.json());
  document.getElementById('healthReport').innerHTML = r.length
    ? '<h4 style="margin:14px 0 8px">source health</h4>' + r.map(s=>`<div class="article-item"><strong>${s.site}</strong> · score ${s.score}% (${s.success}✓ / ${s.fail}✗)</div>`).join('')
    : '';
}
async function loadCacheStats() {
  const r = await fetch('/api/bootstrap').then(r=>r.json());
  document.getElementById('cacheStats').textContent = `Cache: ${r.cache_stats.count} items · ${(r.cache_stats.size/1024/1024).toFixed(2)} MB`;
}
async function clearCache() { await fetch('/api/cache/clear',{method:'POST'}); toast('cache cleared'); loadCacheStats(); }

// Notifications
function toggleNotifs() { document.getElementById('notifPanel').classList.toggle('hidden'); document.getElementById('notifBadge').style.display='none'; }
function renderNotifs() {
  document.getElementById('notifPanel').innerHTML = STATE.notifs.length
    ? STATE.notifs.map(n=>`<div class="notif-item"><strong>${n.title}</strong>${n.body}<br><small style="color:var(--muted)">${new Date(n.time).toLocaleTimeString()}</small></div>`).join('')
    : '<div class="notif-item" style="color:var(--muted)">no notifications</div>';
}

function val(id) { return document.getElementById(id).value; }
function chk(id) { return document.getElementById(id).checked; }
function copyText(t) { navigator.clipboard.writeText(t); toast('copied'); }
function toast(msg) {
  document.getElementById('toastText').textContent = msg;
  const el = document.getElementById('toast');
  el.classList.add('show');
  clearTimeout(window._t); window._t = setTimeout(()=>el.classList.remove('show'), 2200);
}

// Drop zone
const dz = document.getElementById('dropSites');
if (dz) {
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('over'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('over'));
  dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('over');
    const f = e.dataTransfer.files[0]; if (f) { const r = new FileReader();
      r.onload = ev => { document.getElementById('sites').value = ev.target.result; toast('file loaded'); }; r.readAsText(f); }
  });
}

// Keyboard #17
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.key === 'Enter') generate();
  if (e.ctrlKey && (e.key === 'k' || e.key === 'p')) { e.preventDefault(); openPalette(); }
  if (e.key === 'Escape') { document.getElementById('palette').classList.add('hidden'); }
});

// Workspace tabs #19
function addWorkspace() {
  const n = document.querySelectorAll('.ws-tab').length;
  const t = document.createElement('div');
  t.className = 'ws-tab'; t.textContent = `workspace ${n}`;
  document.querySelector('.workspace-tabs').insertBefore(t, document.querySelector('.ws-tab:last-child'));
  toast('new workspace');
}