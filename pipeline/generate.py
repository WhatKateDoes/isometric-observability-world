#!/usr/bin/env python3
"""Asset pipeline. Reads world.json, writes web/assets/*.png + manifest.json.

  --backend comfyui     use a ComfyUI server (any machine: --comfy-url or $COMFYUI_URL), key out the flat background
  --backend procedural  draw everything with Pillow, no AI, no network
  --backend auto        (default) comfyui if the server answers, else procedural; a failed ComfyUI asset falls back per asset
The engine also runs with NO assets at all (it draws primitives), so this step is optional polish.
Needs Pillow (`pip install pillow`); ComfyUI use is stdlib urllib. Sprite contract: see web/js/render.js."""
import argparse, colorsys, json, os, random, shutil, sys, time, urllib.parse, urllib.request, uuid
from PIL import Image, ImageDraw, ImageEnhance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = 128                                   # sprite px per tile width (engine scales down; 2x for crispness)
NEG = "text, watermark, blurry, multiple objects, ground plane, cast shadow, frame, border"
rgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
def shade(c, f): return tuple(min(255, int(v * f)) for v in c)

# ---------- procedural backend ----------
def draw_post(kind, on, ss=3):
    """Iso box with windows/roof band. Diamond centre at (w/2, h-anchor); anchor = T/4+4."""
    z = int(kind["height"] * T / 64); w, h = T + 8, z + T // 2 + 8; ax = T // 4 + 4
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy = w * ss / 2, (h - ax) * ss; hw, hh, zz = T / 2 * ss, T / 4 * ss, z * ss
    col = rgb(kind["color"]) if on else (92, 98, 106)
    A, B, C, D = (cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)
    up = lambda p: (p[0], p[1] - zz)
    d.polygon([D, C, up(C), up(D)], fill=shade(col, .62)); d.polygon([C, B, up(B), up(C)], fill=shade(col, .8))
    d.polygon([up(A), up(B), up(C), up(D)], fill=shade(col, 1.05)); d.line([up(D), up(C), up(B)], fill=shade(col, 1.3), width=ss)
    for k in range(max(1, z // 28)):                                         # windows on the left face
        t0 = .25 + .5 * ((k * 37 % 5) / 5); wy = zz * (.3 + .4 * (k % 2))
        p = lambda t, yy: (D[0] + (C[0] - D[0]) * t, D[1] + (C[1] - D[1]) * t - yy)
        d.polygon([p(t0, wy), p(t0 + .14, wy), p(t0 + .14, wy + 12 * ss), p(t0, wy + 12 * ss)], fill=(255, 220, 140) if on else (50, 54, 60))
    return im.resize((w, h), Image.LANCZOS)

def draw_crew(n=4, ss=4):
    cw, ch = 40, 64; sheet = Image.new("RGBA", (cw * n, ch), (0, 0, 0, 0))
    for f in range(n):
        im = Image.new("RGBA", (cw * ss, ch * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = ss
        step = 0 if f == 0 else (-1, 1, -1, 1)[f % 4] * 4; bob = 0 if f == 0 else (f % 2) * 2
        d.rounded_rectangle([14 * s, (26 - bob) * s, 26 * s, (50 - bob) * s], 4 * s, fill=(240, 200, 60))          # coat
        d.rectangle([(15 + step / 2) * s, (48 - bob) * s, (19 + step / 2) * s, 62 * s], fill=(50, 60, 90)); d.rectangle([(21 - step / 2) * s, (48 - bob) * s, (25 - step / 2) * s, 62 * s], fill=(50, 60, 90))
        d.ellipse([14 * s, (10 - bob) * s, 26 * s, (24 - bob) * s], fill=(242, 211, 176)); d.pieslice([13 * s, (8 - bob) * s, 27 * s, (22 - bob) * s], 180, 360, fill=(70, 70, 90))
        sheet.paste(im.resize((cw, ch), Image.LANCZOS), (f * cw, 0))
    return sheet

# ---------- ComfyUI backend ----------
class Comfy:
    def __init__(s, url, workflow, ckpt, size, timeout):
        s.url = url.rstrip("/"); s.wf = json.load(open(workflow)); s.ckpt = ckpt; s.size = size; s.timeout = timeout
    def alive(s):
        try: urllib.request.urlopen(s.url + "/system_stats", timeout=3).read(); return True
        except Exception: return False
    def fill(s, node, sub):
        if isinstance(node, dict): return {k: s.fill(v, sub) for k, v in node.items()}
        if isinstance(node, list): return [s.fill(v, sub) for v in node]
        if isinstance(node, str) and node in sub: return sub[node]       # whole-value placeholder keeps its type (int seed etc.)
        return node
    def run(s, prompt, seed):
        sub = {"%PROMPT%": prompt, "%NEGATIVE%": NEG, "%SEED%": seed, "%W%": s.size, "%H%": s.size, "%CKPT%": s.ckpt}
        body = json.dumps({"prompt": s.fill(s.wf, sub), "client_id": uuid.uuid4().hex}).encode()
        pid = json.load(urllib.request.urlopen(urllib.request.Request(s.url + "/prompt", body, {"Content-Type": "application/json"}), timeout=30))["prompt_id"]
        end = time.time() + s.timeout
        while time.time() < end:
            hist = json.load(urllib.request.urlopen(f"{s.url}/history/{pid}", timeout=10)).get(pid)
            if hist and hist.get("outputs"):
                for o in hist["outputs"].values():
                    for im in o.get("images", []):
                        q = urllib.parse.urlencode({k: im[k] for k in ("filename", "subfolder", "type")})
                        return Image.open(urllib.request.urlopen(f"{s.url}/view?{q}", timeout=30)).convert("RGBA")
            time.sleep(1.5)
        raise TimeoutError("ComfyUI job timed out")

def key_green(im, tol=70):
    """Remove the flat bright-green background: flood from the border using the corner colour, then crop to content."""
    px = im.load(); w, h = im.size; bg = px[0, 0][:3]; seen = set(); stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    near = lambda c: sum(abs(a - b) for a, b in zip(c[:3], bg)) < tol * 3 / 1.5 or (c[1] > 150 and c[1] > c[0] + 50 and c[1] > c[2] + 50)
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h) or not near(px[x, y]): continue
        seen.add((x, y)); px[x, y] = (0, 0, 0, 0); stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return im.crop(im.getbbox()) if im.getbbox() else im

def place_post(sprite):
    """Fit a keyed sprite into the post canvas contract (bottom of the sprite near the diamond's lower half)."""
    sc = min(1.0, (T * 1.15) / sprite.width); sp = sprite.resize((int(sprite.width * sc), int(sprite.height * sc)), Image.LANCZOS)
    w, h = max(T + 8, sp.width + 8), sp.height + T // 8 + 4; out = Image.new("RGBA", (w, h), (0, 0, 0, 0)); out.paste(sp, ((w - sp.width) // 2, 0), sp); return out

def off_variant(im):
    g = ImageEnhance.Color(im).enhance(.15); r, gch, b, a = g.split(); return Image.merge("RGBA", (*[ImageEnhance.Brightness(Image.merge("RGB", (r, gch, b))).enhance(.7).split()[i] for i in range(3)], a))

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--world", default=os.path.join(ROOT, "world.json")); ap.add_argument("--out", default=os.path.join(ROOT, "web", "assets"))
    ap.add_argument("--backend", choices=["auto", "comfyui", "procedural"], default="auto")
    ap.add_argument("--comfy-url", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    ap.add_argument("--workflow", default=os.path.join(ROOT, "pipeline", "workflows", "txt2img_sd.json"))
    ap.add_argument("--ckpt", default=os.environ.get("COMFYUI_CKPT", "sd_xl_base_1.0.safetensors"))
    ap.add_argument("--size", type=int, default=1024); ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--only", help="comma list of kind ids and/or 'crew'"); ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    world = json.load(open(a.world)); os.makedirs(a.out, exist_ok=True)
    comfy = None
    if a.backend != "procedural":
        c = Comfy(a.comfy_url, a.workflow, a.ckpt, a.size, a.timeout)
        if c.alive(): comfy = c
        elif a.backend == "comfyui": sys.exit(f"ComfyUI not reachable at {a.comfy_url}")
    print("backend:", "comfyui @ " + a.comfy_url if comfy else "procedural")
    want = set(a.only.split(",")) if a.only else None
    man = {"tile_px": T, "anchor": T // 4 + 4, "posts": {}, "crew_frames": 4, "crew_scale": 0.9, "source": {}}
    old = os.path.join(a.out, "manifest.json")
    if want and os.path.exists(old): man = {**man, **{k: v for k, v in json.load(open(old)).items() if k in ("posts", "crew", "source")}}
    style = world.get("style", "isometric game art")
    def gen(prompt):
        if comfy:
            try: return "comfyui", comfy.run(prompt, a.seed)
            except Exception as e: print("  comfyui failed, falling back to procedural:", e)
        return "procedural", None
    for name, kind in world["kinds"].items():
        if want and name not in want: continue
        src, raw = gen(f"{style}, {kind['prompt']}, isometric 2:1 view from above, single building centred, whole object visible, plain flat bright green background")
        if raw: on = place_post(key_green(raw)); off = off_variant(on)
        else: on, off = draw_post(kind, True), draw_post(kind, False)
        on.save(os.path.join(a.out, f"post_{name}_on.png")); off.save(os.path.join(a.out, f"post_{name}_off.png"))
        man["posts"][name] = {"on": f"post_{name}_on.png", "off": f"post_{name}_off.png"}; man["source"][name] = src; print(f"  post {name}: {src}")
    if not want or "crew" in want:
        src, raw = gen(f"{style}, {world['crew']['prompt']}, full body standing, front view, single character, plain flat bright green background")
        if raw:                                                           # one generated character, frames made by bob/shear (AI walk cycles do not stay consistent)
            c = key_green(raw); c = c.resize((int(c.width * 64 / c.height), 64), Image.LANCZOS); cw = c.width + 8; sheet = Image.new("RGBA", (cw * 4, 72), (0, 0, 0, 0))
            for f in range(4): sheet.paste(c, (f * cw + 4, 8 - (f % 2) * 3 if f else 8), c)
        else: sheet = draw_crew()
        sheet.save(os.path.join(a.out, "crew.png")); man["crew"] = "crew.png"; man["source"]["crew"] = src; print("  crew:", src)
    json.dump(man, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    shutil.copy(a.world, os.path.join(ROOT, "web", "world.json")); print("wrote", a.out)

if __name__ == "__main__": main()
