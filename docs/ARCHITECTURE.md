# Architecture

```
probes (collector) -> status.json v1 -> translate.js (only reader) -> Sim (posts, crew, crates) -> Renderer (canvas)
                                  world.json (theme + services + layout) feeds all of them
pipeline/generate.py -> web/assets/{post_*_on|off.png, crew.png, manifest.json}   (optional; renderer falls back to primitives)
```

## status.json v1
```json
{ "version": 1, "time": 1790000000.0,
  "hosts": { "<id>": { "cpu": 0.0-1.0, "mem": 0.0-1.0|null, "gpus": [ { "util": 0-1, "mem_used_mb": 0, "mem_total_mb": 0 } ] } },
  "services": { "<service id>": { "up": true, "latency_ms": 12.3, "load": 0.0-1.0 } },
  "traffic": { "requests_per_s": 0.0 } }
```
`time` older than 30 s, or an unknown `version`, makes the world go idle (never an error). Anything can produce this file:
the bundled collector, a cron job, a Prometheus/Netdata adapter. Only `web/js/translate.js` reads it; to change the data source, change that one file.

## world.json
`kinds` (look: colour, height, AI prompt), `services` (id, name, kind, grid position `at`), `grid`, `palette`, `style`
(prefix of every AI prompt), `crew`, `entry` (where crates and workers appear). The service ids are the join key between
`world.json`, `collector/probes.json` and `status.json`.

## Behaviour (sim.js)
* A post glows with its service's `load`; a down service is grey with a pulsing red marker.
* Crew count follows total load of up services; each walks to a random up post, works, repeats.
* One crate flies from `entry` to a random up post per request (`traffic.requests_per_s`).

## Sprite contract (assets/manifest.json)
`tile_px` = sprite pixels per tile width (64 px = one tile diamond 64x32 on screen at zoom 1). In a post sprite the
diamond centre of the post's tile is `anchor` px above the bottom edge, horizontally centred. `crew.png` is `crew_frames`
equal cells side by side: cell 0 idle, the rest a walk cycle; feet at the bottom edge.
Any tool can make these files. Hand-drawn sprites that follow the contract just work.

## Public-hosting safety
The page only does GET. status.json should contain no hostnames, IPs, secrets or prompts; the bundled collector emits only
service ids, up/down, latency, load, host utilisation.
