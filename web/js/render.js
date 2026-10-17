// Isometric 2:1 renderer. Uses generated sprites from assets/manifest.json when present, else draws primitives, so the
// world looks fine with zero generated art. Sprite contract: diamond centre of the post's tile sits at (w/2, h-anchor); tile_px = sprite px per tile width.
const TW = 64, TH = 32;
const iso = (i, j) => [(i - j) * TW / 2, (i + j) * TH / 2];
const shade = (hex, f) => { const n = parseInt(hex.slice(1), 16); return `rgb(${[16, 8, 0].map(s => Math.min(255, ((n >> s) & 255) * f | 0)).join(',')})`; };
const load = src => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.onerror = () => r(null); i.src = src; });

export async function loadAssets() {
  try { var m = await (await fetch('assets/manifest.json', { cache: 'no-cache' })).json(); } catch { return {}; }
  const a = { crew: m.crew && await load('assets/' + m.crew), posts: {}, crewFrames: m.crew_frames || 2, tile: m.tile_px || 64, anchor: m.anchor ?? 16, crewScale: m.crew_scale || 0.6 };
  for (const [k, v] of Object.entries(m.posts || {})) a.posts[k] = { off: await load('assets/' + v.off), on: await load('assets/' + v.on) };
  return a;
}

export class Renderer {
  constructor(canvas, world, sim, assets) { this.cv = canvas; this.g = canvas.getContext('2d'); this.w = world; this.sim = sim; this.A = assets; this.hit = []; }
  fit() {
    const dpr = devicePixelRatio || 1, { clientWidth: W, clientHeight: H } = this.cv; this.cv.width = W * dpr; this.cv.height = H * dpr;
    const gw = this.w.grid.w, gd = this.w.grid.d, bw = (gw + gd) * TW / 2 + 160, bh = (gw + gd) * TH / 2 + 220;
    this.k = Math.min(W / bw, H / bh) * dpr; this.ox = this.cv.width / 2; this.oy = (this.cv.height - bh * this.k) / 2 + 150 * this.k;
  }
  P(i, j) { const [x, y] = iso(i, j); return [this.ox + x * this.k, this.oy + y * this.k]; }
  diamond(i, j, w, d, fill) {
    const g = this.g, pts = [[i, j], [i + w, j], [i + w, j + d], [i, j + d]].map(([a, b]) => this.P(a, b));
    g.beginPath(); pts.forEach(([x, y], n) => n ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); g.fillStyle = fill; g.fill();
  }
  box(p, h, col, glow) {
    const g = this.g, [i, j] = p.at, z = h * this.k, pt = (a, b) => this.P(i + a, j + b);
    const A = pt(0, 0), B = pt(1, 0), C = pt(1, 1), D = pt(0, 1);
    const face = (pts, f) => { g.beginPath(); pts.forEach(([x, y], n) => n ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); g.fillStyle = shade(col, f); g.fill(); };
    face([D, C, [C[0], C[1] - z], [D[0], D[1] - z]], 0.62); face([C, B, [B[0], B[1] - z], [C[0], C[1] - z]], 0.8); face([A, B, C, D].map(([x, y]) => [x, y - z]), 1.05);
    if (glow > 0.02) { g.fillStyle = `rgba(255,220,140,${0.35 + 0.6 * glow})`; const wx = (D[0] + C[0]) / 2, wy = (D[1] + C[1]) / 2 - z * 0.45; g.fillRect(wx - 5 * this.k, wy - 6 * this.k, 10 * this.k, 12 * this.k); }
  }
  frame(t) {
    const g = this.g, { palette: pal, grid } = this.w; g.fillStyle = pal.bg; g.fillRect(0, 0, this.cv.width, this.cv.height);
    for (let i = 0; i < grid.w; i++) for (let j = 0; j < grid.d; j++) this.diamond(i, j, 1, 1, (i + j) & 1 ? pal.ground : pal.ground_alt);
    const items = [];
    for (const p of this.sim.posts) items.push({ z: p.at[0] + p.at[1] + 1, f: () => this.drawPost(p, t) });
    for (const c of this.sim.crew) items.push({ z: c.x + c.y, f: () => this.drawCrew(c, t) });
    for (const k of this.sim.crates) items.push({ z: 99, f: () => this.drawCrate(k) });
    items.sort((a, b) => a.z - b.z).forEach(o => o.f());
  }
  drawPost(p, t) {
    const kind = this.w.kinds[p.kind], up = p.state.up, A = this.A.posts?.[p.kind], [cx, cy] = this.P(p.at[0] + 0.5, p.at[1] + 0.5);
    if (A && (up ? A.on : A.off)) { const im = up ? A.on : A.off, s = this.k * (TW / this.A.tile); this.g.drawImage(im, cx - im.width * s / 2, cy - (im.height - this.A.anchor) * s, im.width * s, im.height * s); }
    else this.box(p, kind.height, up ? kind.color : '#555a60', up ? p.glow : 0);
    this.hit.push({ p, x: cx, y: cy - kind.height * this.k / 2, r: 30 * this.k });
    if (!up) { this.g.fillStyle = this.w.palette.down; this.g.globalAlpha = 0.5 + 0.5 * Math.sin(t * 5); this.g.beginPath(); this.g.arc(cx, cy - (kind.height + 14) * this.k, 5 * this.k, 0, 7); this.g.fill(); this.g.globalAlpha = 1; }
  }
  drawCrew(c, t) {
    const [x, y] = this.P(c.x, c.y), g = this.g, bob = c.work > 0 ? 0 : Math.abs(Math.sin(t * 8 + c.hue)) * 2 * this.k;
    if (this.A.crew) { const n = this.A.crewFrames, fw = this.A.crew.width / n, f = c.work > 0 ? 0 : 1 + ((t * 6) | 0) % (n - 1 || 1), s = this.k * this.A.crewScale; g.drawImage(this.A.crew, f * fw, 0, fw, this.A.crew.height, x - fw * s / 2, y - this.A.crew.height * s - bob, fw * s, this.A.crew.height * s); return; }
    g.fillStyle = `hsl(${c.hue},60%,55%)`; g.fillRect(x - 3 * this.k, y - 16 * this.k - bob, 6 * this.k, 12 * this.k);
    g.fillStyle = '#f2d3b0'; g.beginPath(); g.arc(x, y - 19 * this.k - bob, 3.5 * this.k, 0, 7); g.fill();
  }
  drawCrate(k) {
    const [ex, ey] = this.w.entry, [x0, y0] = this.P(ex, ey), [x1, y1] = this.P(k.to.at[0] + 0.5, k.to.at[1] + 0.5);
    this.g.fillStyle = this.w.palette.accent; this.g.fillRect(x0 + (x1 - x0) * k.p - 3 * this.k, y0 + (y1 - y0) * k.p - 3 * this.k - Math.sin(k.p * Math.PI) * 14 * this.k, 6 * this.k, 6 * this.k);
  }
  pick(mx, my) { const dpr = devicePixelRatio || 1; return this.hit.find(h => Math.hypot(h.x - mx * dpr, h.y - my * dpr) < h.r)?.p; }
}
