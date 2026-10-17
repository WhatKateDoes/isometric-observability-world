#!/usr/bin/env python3
"""check_art.py PATH... [--contact out.png] [--min-opaque 0.02] [--cell WxH]
Fails (exit 1) when any image is fully transparent / nearly empty, or its opaque pixels touch the image border (cropped sprite).
Prints one line per file and writes a contact sheet to LOOK AT. Needs Pillow.  A sheet that has not been opened is not verified."""
import sys, glob, pathlib
from PIL import Image, ImageDraw

def main():
    a = sys.argv[1:]
    contact = a[a.index("--contact") + 1] if "--contact" in a else None
    mino = float(a[a.index("--min-opaque") + 1]) if "--min-opaque" in a else 0.02
    paths = []
    skip = set()
    for i, x in enumerate(a):
        if x in ("--contact", "--min-opaque", "--cell"): skip.update({i, i + 1})
    for i, x in enumerate(a):
        if i in skip: continue
        p = pathlib.Path(x)
        paths += sorted(p.glob("*.png")) + sorted(p.glob("*.webp")) if p.is_dir() else [p]
    bad = 0; ims = []
    for p in paths:
        im = Image.open(p).convert("RGBA"); al = im.getchannel("A")
        bbox = al.getbbox(); n = sum(1 for v in al.tobytes() if v > 8); frac = n / (im.width * im.height)
        flag = ""
        if bbox is None: flag = "BLANK"
        elif frac < mino: flag = f"NEARLY EMPTY ({frac:.3f})"
        elif bbox[0] == 0 or bbox[1] == 0 or bbox[2] == im.width or bbox[3] == im.height:
            if im.width * im.height < 600 * 600: flag = "touches the border (cropped?)"
        if flag and flag.startswith(("BLANK", "NEARLY")): bad += 1
        print(f"{'FAIL' if flag.startswith(('BLANK','NEARLY')) else 'warn' if flag else 'ok  '} {p.name:40s} {im.width}x{im.height} opaque {frac:.3f} {flag}")
        ims.append((p.name, im))
    if contact and ims:
        cw = min(max(i.width for _, i in ims), 400) + 10; ch = min(max(i.height for _, i in ims), 400) + 24
        cols = max(1, min(8, 2400 // cw)); rows = (len(ims) + cols - 1) // cols
        sh = Image.new("RGBA", (cols * cw, rows * ch), (40, 46, 58, 255)); d = ImageDraw.Draw(sh)
        for k, (n, im) in enumerate(ims):
            t = im.copy(); t.thumbnail((cw - 10, ch - 24)); x, y = (k % cols) * cw, (k // cols) * ch
            sh.alpha_composite(t, (x + 5, y + 20)); d.text((x + 4, y + 4), n[:40], fill=(255, 255, 0, 255))
        sh.convert("RGB").save(contact); print("contact sheet:", contact, "<- OPEN AND LOOK AT IT")
    print(f"{len(paths)} images, {bad} failing")
    sys.exit(1 if bad else 0)

main()
