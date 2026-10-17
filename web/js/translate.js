// The ONLY module that reads status.json. Everything else sees a plain "state" object, so a different data source
// (Prometheus, Netdata, a hand-written JSON file...) only needs a new translate().
export function translate(status, world) {
  const age = status ? Date.now() / 1000 - status.time : Infinity;
  const stale = !(status && status.version === 1) || age > 30;       // stale or unknown schema => everything idle, never a crash
  const services = {};
  for (const s of world.services) {
    const r = !stale && status.services?.[s.id];
    services[s.id] = r ? { up: !!r.up, load: Math.max(0, Math.min(1, r.load ?? 0.3)), latency: r.latency_ms ?? 0 } : { up: false, load: 0, latency: 0, unknown: true };
  }
  const gpuLoad = stale ? 0 : Math.max(0, ...Object.values(status.hosts || {}).flatMap(h => (h.gpus || []).map(g => g.util)));
  return { stale, age, services, traffic: stale ? 0 : status.traffic?.requests_per_s ?? 0, gpuLoad };
}
