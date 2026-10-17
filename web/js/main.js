import { translate } from './translate.js'; import { Sim } from './sim.js'; import { Renderer, loadAssets } from './render.js';
const world = await (await fetch('world.json')).json();
const sim = new Sim(world), cv = document.getElementById('c'), hud = document.getElementById('hud'), tip = document.getElementById('tip');
const r = new Renderer(cv, world, sim, await loadAssets());
addEventListener('resize', () => r.fit()); r.fit();
let status = null;
async function poll() {
  try { status = await (await fetch(world.status_url + '?_=' + Date.now(), { cache: 'no-store' })).json(); } catch { status = null; }
  const st = translate(status, world); sim.setState(st);
  const up = Object.values(st.services).filter(s => s.up).length;
  hud.innerHTML = `<b>${world.title}</b><br>${st.stale ? 'no fresh data' : `${up}/${world.services.length} services up`}`;
}
poll(); setInterval(poll, 3000);
cv.addEventListener('mousemove', e => { const p = r.pick(e.clientX, e.clientY); tip.style.display = p ? 'block' : 'none';
  if (p) { tip.style.left = e.clientX + 14 + 'px'; tip.style.top = e.clientY + 10 + 'px'; tip.textContent = `${p.name}: ${p.state.up ? 'up, load ' + Math.round(p.state.load * 100) + '%' : 'down'}. ${p.blurb || ''}`; } });
let last = performance.now();
(function loop(now) { r.hit = []; sim.update(Math.min(0.1, (now - last) / 1000)); last = now; r.frame(now / 1000); requestAnimationFrame(loop); })(last);
