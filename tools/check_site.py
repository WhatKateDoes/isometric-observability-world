#!/usr/bin/env python3
"""check_site.py URL [--screenshot-stats shot.png] [--min-status-age 10]
URL = the world's base, e.g. http://localhost:8080/
1. index.html loads; every <script src>, <link href>, <img src> resolves 200.
2. Every ES-module import (relative) of every JS file resolves 200.
3. Every JSON index (assets/audio/index.json, assets/music/index.json, assets/art/*.json) is valid and each `file` it names exists.
4. api/status.json is fresh (ts within --min-status-age s) and lists servers + services.
5. --screenshot-stats: a screenshot you took of the running page must not be (almost) one colour.
Exit 1 on any failure. stdlib + Pillow (only for stats)."""
import sys, re, json, time, urllib.request, urllib.parse, urllib.error

def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"Cache-Control": "no-cache"}), timeout=20) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, b""
    except Exception as e: return 0, str(e).encode()

def main():
    a = sys.argv[1:]; base = a[0].rstrip("/") + "/"; bad = []
    maxage = float(a[a.index("--min-status-age") + 1]) if "--min-status-age" in a else 10
    st, html = get(base)
    print("index", st)
    if st != 200: bad.append("index.html " + str(st)); print("\n".join(bad)); sys.exit(1)
    html = html.decode("utf8", "replace")
    refs = re.findall(r'(?:src|href)="([^"#]+)"', html)
    todo = [r for r in refs if not r.startswith(("http", "//", "data:"))]
    todo += ["assets/audio/index.json", "assets/music/index.json", "assets/art/plate.json", "assets/art/posts.json", "assets/art/crew.json", "config.default.json", "assets/layout.json"]   # fetched by the app at run time
    seen = set(); js = []
    while todo:
        r = todo.pop(); u = urllib.parse.urljoin(base, r)
        if u in seen: continue
        seen.add(u); s, body = get(u)
        if s != 200: bad.append(f"{s} {u}"); continue
        if u.split("?")[0].endswith(".js"):
            js.append(u)
            for imp in re.findall(r'from\s+[\'"](\.[^\'"]+)[\'"]|import\([\'"](\.[^\'"]+)[\'"]\)', body.decode("utf8", "replace")):
                todo.append(urllib.parse.urljoin(u, imp[0] or imp[1]))
        if u.split("?")[0].endswith(".json") and ("index" in u or "/art/" in u):
            if u.endswith("posts.json"): continue   # sprite rectangles, not files
            try:
                d = json.loads(body)
                names = []
                def walk(o):
                    if isinstance(o, dict):
                        for k, v in o.items():
                            if k == "file" and isinstance(v, str): names.append(v)
                            else: walk(v)
                    elif isinstance(o, list):
                        for v in o: walk(v)
                walk(d)
                base_dir = u.rsplit("/", 1)[0] + "/"
                for n in names:
                    if "." not in n:   # music index lists names without extension
                        cands = [n + ".mp3"]
                    else: cands = [n]
                    for c in cands:
                        uu = urllib.parse.urljoin(base_dir, c)
                        if uu not in seen:
                            seen.add(uu); s2, _ = get(uu)
                            if s2 != 200: bad.append(f"{s2} {uu} (named in {u.rsplit('/',1)[-1]})")
            except ValueError: bad.append("bad JSON " + u)
    print(f"{len(seen)} resources checked, {len(js)} JS files")
    s, body = get(base + "api/status.json")
    if s == 200:
        d = json.loads(body); age = time.time() - d.get("ts", 0)
        print(f"status.json age {age:.1f}s servers {list(d.get('servers', {}))} services {len(d.get('services', {}))}")
        if age > maxage: bad.append(f"status.json is {age:.0f}s old (collector down?)")
        if not d.get("services"): bad.append("status.json has no services")
    else: bad.append(f"api/status.json {s}")
    if "--screenshot-stats" in a:
        from PIL import Image
        im = Image.open(a[a.index("--screenshot-stats") + 1]).convert("RGB").resize((160, 90)); cols = len(set(im.getdata()))
        print("screenshot distinct colours (160x90):", cols)
        if cols < 200: bad.append(f"screenshot has only {cols} colours: the world is not drawn")
    for b in bad: print("FAIL", b)
    print("OK" if not bad else f"{len(bad)} problems")
    sys.exit(1 if bad else 0)

main()
