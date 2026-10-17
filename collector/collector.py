#!/usr/bin/env python3
"""Collector: probes your services and writes web/api/status.json (schema v1, see docs/ARCHITECTURE.md).
Stdlib only. Runs anywhere Python 3.8+ runs. GPU stats via nvidia-smi if present; skipped otherwise.

  collector.py --demo                 fake data, no config needed (try the web UI)
  collector.py --once                 probe once and exit
  collector.py                        loop every --interval seconds
Probes live in collector/probes.json: {"service_id": {"type": "http|tcp|docker|cmd", ...}}"""
import argparse, json, math, os, random, shutil, socket, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

def probe(p):
    t0 = time.time(); t = p.get("type")
    try:
        if t == "http":
            with urllib.request.urlopen(p["url"], timeout=p.get("timeout", 3)) as r: up = r.status < 500
        elif t == "tcp":
            socket.create_connection((p["host"], int(p["port"])), timeout=p.get("timeout", 3)).close(); up = True
        elif t == "docker":
            out = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", p["name"]], capture_output=True, text=True, timeout=5)
            up = out.stdout.strip() == "true"
        elif t == "cmd":
            up = subprocess.run(p["cmd"], shell=True, capture_output=True, timeout=p.get("timeout", 5)).returncode == 0
        else: up = False
    except Exception: up = False
    return {"up": up, "latency_ms": round((time.time() - t0) * 1000, 1)}

def host_stats():
    h = {}
    try: h["cpu"] = min(1.0, os.getloadavg()[0] / (os.cpu_count() or 1))
    except OSError: h["cpu"] = 0.0
    try:
        mi = dict(l.split(":") for l in open("/proc/meminfo").read().splitlines())
        tot, av = (int(mi[k].split()[0]) for k in ("MemTotal", "MemAvailable")); h["mem"] = 1 - av / tot
    except Exception: h["mem"] = None            # non-Linux: unknown, UI ignores it
    h["gpus"] = []
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5).stdout
            for l in out.strip().splitlines():
                u, mu, mt = (float(x) for x in l.split(","))
                h["gpus"].append({"util": u / 100, "mem_used_mb": mu, "mem_total_mb": mt})
        except Exception: pass
    return h

def build(world, probes, demo):
    now = time.time(); svc = {}
    for s in world["services"]:
        if demo:
            ph = now / 20 + sum(map(ord, s["id"])) % 7
            svc[s["id"]] = {"up": not (s["id"] == "jobs" and int(now / 30) % 5 == 0), "latency_ms": round(20 + 15 * math.sin(ph), 1), "load": round(0.5 + 0.45 * math.sin(ph * 1.7), 2)}
        else:
            r = probe(probes[s["id"]]) if s["id"] in probes else {"up": False, "latency_ms": 0}
            r["load"] = 0.5 if r["up"] else 0.0       # real per-service load needs your own metric; add it in probes.json
            svc[s["id"]] = r
    hid = next(iter(world.get("hosts", {"main": 0})))
    host = {"cpu": round(0.4 + 0.3 * math.sin(now / 15), 2), "mem": 0.5, "gpus": []} if demo else host_stats()
    return {"version": 1, "time": now, "hosts": {hid: host}, "services": svc,
            "traffic": {"requests_per_s": round(random.uniform(0, 8), 1) if demo else 0}}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default=os.path.join(HERE, "..", "world.json"))
    ap.add_argument("--probes", default=os.path.join(HERE, "probes.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "web", "api", "status.json"))
    ap.add_argument("--interval", type=float, default=5)
    ap.add_argument("--demo", action="store_true"); ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    world = json.load(open(a.world))
    probes = {} if a.demo else json.load(open(a.probes))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    while True:
        tmp = a.out + ".tmp"
        json.dump(build(world, probes, a.demo), open(tmp, "w")); os.replace(tmp, a.out)   # atomic: readers never see half a file
        if a.once: break
        time.sleep(a.interval)

if __name__ == "__main__": main()
