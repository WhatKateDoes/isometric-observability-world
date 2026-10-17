// Posts (services), crew (workers) and crates (traffic). Knows nothing about status.json or canvas.
const R = (a, b) => a + Math.random() * (b - a);
export class Sim {
  constructor(world) {
    this.w = world; this.posts = world.services.map(s => ({ ...s, state: { up: false, load: 0 }, glow: 0 }));
    this.crew = []; this.crates = []; this.t = 0; this.crateAcc = 0;
  }
  setState(st) {
    this.st = st; for (const p of this.posts) p.state = st.services[p.id];
    const busy = this.posts.filter(p => p.state.up).reduce((a, p) => a + p.state.load, 0);
    const want = Math.min(this.w.crew.max, Math.round(busy * 2));
    while (this.crew.length < want) this.crew.push({ x: this.w.entry[0], y: this.w.entry[1], to: null, work: 0, hue: R(0, 360) });
    this.crew.length = Math.min(this.crew.length, Math.max(want, this.crew.length - 1));      // leave one per tick
  }
  update(dt) {
    this.t += dt;
    for (const p of this.posts) p.glow += ((p.state.up ? 0.3 + 0.7 * p.state.load : 0) - p.glow) * Math.min(1, dt * 3);
    const up = this.posts.filter(p => p.state.up);
    for (const c of this.crew) {
      if (c.work > 0) { c.work -= dt; continue; }
      if (!c.to) { c.to = up.length ? up[(Math.random() * up.length) | 0] : null; if (!c.to) continue; }
      const [tx, ty] = [c.to.at[0] + 0.5, c.to.at[1] + 1.5], dx = tx - c.x, dy = ty - c.y, d = Math.hypot(dx, dy);
      if (d < 0.08) { c.work = R(2, 6); c.to = null; } else { c.x += dx / d * dt * 1.4; c.y += dy / d * dt * 1.4; c.face = dx; }
    }
    this.crateAcc += dt * (this.st?.traffic ?? 0);                         // one crate per request
    while (this.crateAcc >= 1 && up.length) { this.crateAcc--; this.crates.push({ p: 0, to: up[(Math.random() * up.length) | 0] }); }
    for (const k of this.crates) k.p += dt * 0.5;
    this.crates = this.crates.filter(k => k.p < 1);
  }
}
