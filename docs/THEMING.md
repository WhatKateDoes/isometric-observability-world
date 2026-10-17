# Theming and extending

* **New theme = new `world.json`.** See `examples/station.world.json`. Copy it over `world.json`, `python3 pipeline/generate.py`, done.
* **Add a service:** add it to `world.json` `services` (pick a free `at` cell inside `grid`), add a probe with the same id to `collector/probes.json`, regenerate if it uses a new `kind`.
* **Add a building kind:** add to `kinds` (`color`, `height`, `prompt`).
* **Other data source:** replace `translate.js`; keep the state shape it returns (`services[id] = {up, load, latency}`, `traffic`, `gpuLoad`, `stale`).
* **Ideas not built (kept out on purpose):** scripted events (storms, visitors), speech and music, day/night. Add them as a new module that only reads `sim` state; keep `translate.js` the sole reader of status.json.
