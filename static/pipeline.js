const PIPE = { nodes: [], edges: [], dragging: null, connecting: null };
let nodeId = 0;

const NODE_TYPES = {
  source: {icon:'language', color:'#4a9eff'},
  scraper: {icon:'search', color:'#7bc4ff'},
  ai: {icon:'smart_toy', color:'#3dd68c'},
  tts: {icon:'record_voice_over', color:'#bd93f9'},
  video: {icon:'movie', color:'#ff79c6'},
  image: {icon:'image', color:'#ffb347'},
  publish: {icon:'rocket_launch', color:'#ff5f5f'}
};

function addNode(type) {
  const id = 'n' + (nodeId++);
  const node = { id, type, x: 60 + (PIPE.nodes.length%4)*180, y: 50 + Math.floor(PIPE.nodes.length/4)*120 };
  PIPE.nodes.push(node); renderPipeline();
}

function renderPipeline() {
  const canvas = document.getElementById('pipelineCanvas');
  if (!canvas) return;
  // svg first
  let svg = document.getElementById('pipelineSvg');
  if (!svg) {
    canvas.insertAdjacentHTML('beforeend','<svg id="pipelineSvg"></svg>');
    svg = document.getElementById('pipelineSvg');
  }
  // clear nodes
  canvas.querySelectorAll('.node').forEach(n=>n.remove());
  PIPE.nodes.forEach(n => {
    const t = NODE_TYPES[n.type];
    const div = document.createElement('div');
    div.className = 'node'; div.id = n.id;
    div.style.left = n.x+'px'; div.style.top = n.y+'px';
    div.innerHTML = `
      <div class="node-header"><span class="material-icons-round" style="color:${t.color}">${t.icon}</span>${n.type}</div>
      <div class="node-body">${n.id}</div>
      <div class="node-port in" data-node="${n.id}"></div>
      <div class="node-port out" data-node="${n.id}"></div>
    `;
    canvas.appendChild(div);
    makeDraggable(div, n);
  });
  // edges
  svg.innerHTML = '';
  PIPE.edges.forEach(([a,b]) => {
    const na = PIPE.nodes.find(x=>x.id===a); const nb = PIPE.nodes.find(x=>x.id===b);
    if (!na||!nb) return;
    const x1 = na.x + 140, y1 = na.y + 28;
    const x2 = nb.x, y2 = nb.y + 28;
    const path = `M${x1},${y1} C${x1+50},${y1} ${x2-50},${y2} ${x2},${y2}`;
    svg.insertAdjacentHTML('beforeend', `<path class="pipe-line" d="${path}"/>`);
  });
}

function makeDraggable(el, n) {
  let offX, offY, drag=false;
  el.addEventListener('mousedown', e => {
    if (e.target.classList.contains('node-port')) {
      if (e.target.classList.contains('out')) PIPE.connecting = n.id;
      return;
    }
    drag = true; offX = e.clientX - n.x; offY = e.clientY - n.y;
  });
  document.addEventListener('mousemove', e => {
    if (!drag) return;
    n.x = e.clientX - offX; n.y = e.clientY - offY;
    el.style.left = n.x+'px'; el.style.top = n.y+'px';
    renderPipeline();
  });
  document.addEventListener('mouseup', e => {
    drag = false;
    if (PIPE.connecting && e.target.classList.contains('node-port') && e.target.classList.contains('in')) {
      const target = e.target.dataset.node;
      if (target !== PIPE.connecting) {
        PIPE.edges.push([PIPE.connecting, target]);
        renderPipeline();
      }
    }
    PIPE.connecting = null;
  });
}

async function savePipeline() {
  const name = prompt('pipeline name?', 'my_pipeline');
  if (!name) return;
  await fetch('/api/pipeline/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name, nodes:PIPE.nodes, edges:PIPE.edges})});
  toast('saved: '+name);
}

async function runPipeline() {
  const r = await fetch('/api/pipeline/run',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({nodes:PIPE.nodes, edges:PIPE.edges})}).then(r=>r.json());
  toast('pipeline mapped → switch to generate tab');
}