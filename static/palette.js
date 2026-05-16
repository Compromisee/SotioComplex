const ACTIONS = [
  {label:'Run pipeline', icon:'bolt', fn:() => generate()},
  {label:'Estimate cost', icon:'payments', fn:() => { document.querySelector('[data-tab="generate"]').click(); estimateCost(); }},
  {label:'Scrape themes', icon:'search', fn:() => { document.querySelector('[data-tab="sources"]').click(); }},
  {label:'Clear cache', icon:'delete', fn:() => clearCache()},
  {label:'Open pipeline builder', icon:'account_tree', fn:() => document.querySelector('[data-tab="pipeline"]').click()},
  {label:'Open settings', icon:'settings', fn:() => document.querySelector('[data-tab="settings"]').click()},
  {label:'Start onboarding tour', icon:'tour', fn:() => startTour()},
  {label:'Switch to dark theme', icon:'dark_mode', fn:() => loadTheme('dark')},
  {label:'Switch to light theme', icon:'light_mode', fn:() => loadTheme('light')},
  {label:'Switch to neon theme', icon:'bolt', fn:() => loadTheme('neon')},
  {label:'Switch to terminal theme', icon:'terminal', fn:() => loadTheme('terminal')},
  {label:'Switch to dracula theme', icon:'nights_stay', fn:() => loadTheme('dracula')},
  {label:'Switch to nord theme', icon:'ac_unit', fn:() => loadTheme('nord')},
];

let palSel = 0;

function openPalette() {
  document.getElementById('palette').classList.remove('hidden');
  const inp = document.getElementById('paletteInput'); inp.value=''; inp.focus();
  renderPalette('');
}

function renderPalette(q) {
  palSel = 0;
  const results = ACTIONS.filter(a => a.label.toLowerCase().includes(q.toLowerCase()));
  document.getElementById('paletteResults').innerHTML = results.map((a,i) =>
    `<div class="pal-item ${i===0?'sel':''}" onclick="runPal(${ACTIONS.indexOf(a)})"><span class="material-icons-round">${a.icon}</span>${a.label}</div>`).join('');
}

function runPal(i) {
  document.getElementById('palette').classList.add('hidden');
  ACTIONS[i].fn();
}

document.addEventListener('input', e => {
  if (e.target.id === 'paletteInput') renderPalette(e.target.value);
});
document.addEventListener('keydown', e => {
  if (document.getElementById('palette').classList.contains('hidden')) return;
  const items = document.querySelectorAll('.pal-item');
  if (e.key === 'ArrowDown') { palSel = (palSel+1) % items.length; items.forEach((it,i)=>it.classList.toggle('sel',i===palSel)); e.preventDefault(); }
  if (e.key === 'ArrowUp') { palSel = (palSel-1+items.length) % items.length; items.forEach((it,i)=>it.classList.toggle('sel',i===palSel)); e.preventDefault(); }
  if (e.key === 'Enter' && items[palSel]) items[palSel].click();
});