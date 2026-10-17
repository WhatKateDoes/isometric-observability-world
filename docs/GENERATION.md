# Generating art

Three tiers, use whichever you have. All write the same files, so you can mix them (re-run with `--only`).

| Tier | Needs | Command |
|---|---|---|
| 0. none | nothing | the renderer draws coloured boxes and dots itself |
| 1. procedural | Python + Pillow | `python3 pipeline/generate.py --backend procedural` |
| 2. ComfyUI | a reachable ComfyUI server + an image checkpoint | `COMFYUI_URL=http://host:8188 COMFYUI_CKPT=model.safetensors python3 pipeline/generate.py` |

`--backend auto` (default) picks ComfyUI when `$COMFYUI_URL` (default `http://127.0.0.1:8188`) answers, else procedural.
If one ComfyUI job fails, that asset falls back to procedural, and `assets/manifest.json` `source` records which backend made which.

## How the ComfyUI path works
1. For each entry in `world.json` `kinds`, the prompt is `<style>, <kind.prompt>, isometric 2:1 view from above, ... plain flat bright green background`.
2. `pipeline/workflows/txt2img_sd.json` (ComfyUI *API format*) has placeholders `%PROMPT% %NEGATIVE% %SEED% %W% %H% %CKPT%`, filled and POSTed to `/prompt`. The result is fetched from `/history` + `/view`.
3. The green is flood-filled away from the border, the sprite cropped and placed into the sprite contract. The "off" (service down) variant is the "on" sprite desaturated and darkened, so the two always match.
4. The crew: one character is generated, the walk cycle is made by bobbing it (AI walk cycles do not stay consistent frame to frame).

**Other models** (Flux, Qwen-Image, SDXL turbo...): in ComfyUI use *Save (API Format)*, replace the prompt text, seed, size and checkpoint values with the placeholders above, pass `--workflow my.json`.
Placeholders must be the whole value of a field. **Remote GPU boxes** need nothing special: it is just a URL.

## Iterating
Look at the output (`python3 tools/check_art.py web/assets/post_*_on.png web/assets/crew.png --contact sheet.png`, then open `sheet.png`).
Regenerate one kind: `--only tower --seed 12`. Keep what you like; hand edits survive as long as you do not re-run that kind.
For a consistent look across kinds, put the shared art direction in `world.json` `style`, and consider a style LoRA in your workflow.
