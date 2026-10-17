#!/bin/sh
# Smoke test: demo collector -> procedural assets -> art gate -> JS syntax. No network, no GPU. Exit 0 = ok.
set -e; cd "$(dirname "$0")/.."
python3 collector/collector.py --demo --once
python3 pipeline/generate.py --backend procedural >/dev/null
python3 tools/check_art.py web/assets/post_*_on.png web/assets/crew.png >/dev/null
for f in web/js/*.js; do node --check "$f"; done
python3 -c "import json;d=json.load(open('web/api/status.json'));assert d['version']==1 and d['services']"
echo "selftest ok"
