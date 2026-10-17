#!/usr/bin/env python3
"""Tiny read-only dev server: serves web/ and maps /world.json to the project's world.json. `serve.py [port]` (default 8080).
For real hosting just copy web/ (plus world.json beside index.html) behind any static server; GET/HEAD only."""
import http.server, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=os.path.join(ROOT, "web"), **k)
    def translate_path(s, path):
        return os.path.join(ROOT, "world.json") if path.split("?")[0] == "/world.json" and not os.path.exists(os.path.join(ROOT, "web", "world.json")) else super().translate_path(path)
    def do_POST(s): s.send_error(405)
    do_PUT = do_DELETE = do_POST
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"http://localhost:{port}/"); http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
