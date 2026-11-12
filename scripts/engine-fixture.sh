#!/usr/bin/env bash
# Refresh web/tests/fixtures/engine-*.json from the real engine (the web tests render the panel from them; a server
# test fails when they drift from what the server answers).
set -euo pipefail
cd "$(dirname "$0")/.."
"$HOME/.local/share/venvs/jxn-kitchen/bin/python" - <<'PY'
import json, pathlib, sys
sys.path.insert(0, 'server')
from kitchen import blends, catalogue, knowhow, spice_data, spice_engine
sys.path.insert(0, 'server/tests')
from engine_fixtures import BLENDS, build
out = build()
for name, data in out.items():
    pathlib.Path(f'web/tests/fixtures/engine-{name}.json').write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
print('wrote', ', '.join(f'engine-{n}.json' for n in out))
PY
