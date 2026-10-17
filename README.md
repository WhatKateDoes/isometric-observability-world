# Isometric Observability World

A tiny isometric town that shows what your servers are doing. Each **service** is a building that lights up with its load
and goes grey with a red beacon when it is down. **Workers** walk to busy buildings, and **crates** fly in for every request.
It is a read-only web page over a small JSON file, so it works with any host, any stack, any art.

* **Server-agnostic.** Nothing here knows about a particular machine, OS, GPU vendor or hosting setup. The data source is one JSON file; the web page is static files.
* **Art optional.** Three tiers: built-in primitives (no assets), a procedural Pillow generator (no AI), or a ComfyUI pipeline on any server you can reach.
* **Forkable.** Re-theme by editing `world.json`; swap the data source by editing one file.

## Quick start (60 seconds, no config, no GPU)

```bash
git clone <your fork> && cd isometric-observability-world
pip install pillow                      # only for the optional art step
python3 collector/collector.py --demo &  # fake telemetry, writes web/api/status.json
python3 pipeline/generate.py             # optional: makes sprites (procedural if no ComfyUI)
python3 tools/serve.py 8080              # open http://localhost:8080/
```

Hover a building for its name, load and blurb.

## Watch your own services

1. Edit `world.json`: list your services (`id`, `name`, `kind`, grid position `at`).
2. `cp collector/probes.example.json collector/probes.json` and give each service id a probe: `http` (URL answers < 500), `tcp` (port open), `docker` (container running), or `cmd` (exit code 0).
3. Run `python3 collector/collector.py` (loops every 5 s; `--once` for cron). It also reports CPU, memory and NVIDIA GPU use if available.
4. Serve `web/` with any static server (copy `world.json` into `web/` first; `generate.py` does this for you). Keep `web/api/status.json` fresh and the world follows.

If the collector runs on a different machine than the web server, copy `status.json` across however you like (rsync, a shared mount, HTTP). The page only reads `api/status.json`.

## Generating art

```bash
python3 pipeline/generate.py                                   # auto: ComfyUI if reachable, else procedural
COMFYUI_URL=http://gpu-box:8188 COMFYUI_CKPT=mymodel.safetensors python3 pipeline/generate.py
python3 pipeline/generate.py --backend procedural              # force no-AI
python3 pipeline/generate.py --only tower,crew --seed 12       # redo some
```

Details, custom workflows (Flux/Qwen/anything) and the sprite contract: [docs/GENERATION.md](docs/GENERATION.md).

## Layout

| Path | What |
|---|---|
| `world.json` | the theme, services and layout (all data) |
| `collector/` | stdlib-only probe loop that writes `status.json` |
| `web/` | static page: `translate.js` (only reader of status.json), `sim.js`, `render.js`, `main.js` |
| `pipeline/` | asset generator + ComfyUI workflow template |
| `tools/` | dev server, art gate (`check_art.py`), site check, `selftest.sh` |
| `examples/` | alternative themes |
| `docs/` | [ARCHITECTURE](docs/ARCHITECTURE.md), [GENERATION](docs/GENERATION.md), [THEMING](docs/THEMING.md), [ORIGIN](docs/ORIGIN.md) |

## Checks

`tools/selftest.sh` runs the collector (demo), procedural generation, the art gate and JS syntax checks offline.
The art gate only proves sprites are not blank: **open the generated images and look at them**.

## Hosting publicly

The page makes GET requests only and `status.json` carries just service ids, up/down, latency, load and host utilisation (no hostnames or IPs).
Check your own `world.json` blurbs before exposing it, and serve it read-only.

## Not included

Scripted events, speech, music and day/night from the original project. See [docs/THEMING.md](docs/THEMING.md) for where they would plug in.

MIT licensed.
