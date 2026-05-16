const TOUR = [
  {sel:'.tab[data-tab="sources"]', text:'1️⃣ Start here — add sites to scrape'},
  {sel:'.tab[data-tab="themes"]', text:'2️⃣ Pick themes from scraped sites'},
  {sel:'.tab[data-tab="articles"]', text:'3️⃣ Browse the scraped articles'},
  {sel:'.tab[data-tab="edit"]', text:'4️⃣ Edit AI summaries before render (saves time!)'},
  {sel:'.tab[data-tab="generate"]', text:'5️⃣ Configure & run the pipeline'},
  {sel:'.tab[data-tab="pipeline"]', text:'6️⃣ Build custom visual pipelines'},
  {sel:'.notif-bell', text:'🔔 Notifications appear here'},
  {sel:'.theme-switcher', text:'🎨 Switch themes any time'},
];

let tourI = 0;
function startTour() {
  tourI = 0;
  showTourStep();
}
function showTourStep() {
  document.querySelectorAll('.tour-tip').forEach(t=>t.remove());
  if (tourI >= TOUR.length) { toast('tour complete'); return; }
  const step = TOUR[tourI];
  const el = document.querySelector(step.sel);
  if (!el) { tourI++; return showTourStep(); }
  el.scrollIntoView({behavior:'smooth', block:'center'});
  const r = el.getBoundingClientRect();
  const tip = document.createElement('div');
  tip.className = 'tour-tip';
  tip.style.cssText = `position:fixed; top:${r.bottom+10}px; left:${r.left}px; background:var(--accent); color:#fff;
    padding:10px 14px; font-size:12px; z-index:9999; box-shadow:0 4px 20px rgba(0,0,0,.5); max-width:300px;`;
  tip.innerHTML = `${step.text}<br><button onclick="tourI++;showTourStep()" style="background:transparent;color:#fff;border:1px solid #fff;padding:3px 8px;margin-top:6px;cursor:pointer">next →</button> <button onclick="document.querySelectorAll('.tour-tip').forEach(t=>t.remove())" style="background:transparent;color:#fff;border:1px solid #fff;padding:3px 8px;margin-top:6px;cursor:pointer">skip</button>`;
  document.body.appendChild(tip);
  el.style.outline = '2px solid var(--accent)';
  setTimeout(()=>{ if(el) el.style.outline=''; }, 5000);
}