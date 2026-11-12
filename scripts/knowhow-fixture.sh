#!/usr/bin/env bash
# Refresh web/tests/fixtures/knowhow.json from knowhow/*.yaml (the web tests render every real page from it; a server
# test fails when it drifts).
set -euo pipefail
cd "$(dirname "$0")/.."
"$HOME/.local/share/venvs/jxn-kitchen/bin/python" - <<'PY'
import json, pathlib, sys
sys.path.insert(0, 'server')
from kitchen import knowhow
import re
# the trap that kept biting (2026-10-11): in a YAML flow mapping {en: A, B, hu: C} the comma ends the value — the
# validator then reports a broken label; this names the line and the fix
lint = []
for f in sorted(pathlib.Path('knowhow').glob('*.yaml')):
    for n, line in enumerate(f.read_text().split('\n'), 1):
        for m in re.finditer(r'\{en: (?!["\'])([^{}]*?), hu: ', line):   # single- or double-quoted values are fine
            if ',' in m.group(1):
                lint.append(f'{f}:{n}: quote the en value — {m.group(0)[:70]}')
        for m in re.finditer(r'hu: (?!["\'])([^{}"\']*?)\}', line):
            if ',' in m.group(1):
                lint.append(f'{f}:{n}: quote the hu value — {m.group(0)[:70]}')
if lint:
    sys.exit('commas in unquoted flow-mapping values:\n  ' + '\n  '.join(lint))
raw = knowhow.load(pathlib.Path('knowhow'))
errors = knowhow.validate(raw)
if errors:                     # never write a fixture the server itself would refuse to start with
    sys.exit('invalid know-how library:\n  ' + '\n  '.join(errors))
lib = knowhow.to_json(raw)
pathlib.Path('web/tests/fixtures/knowhow.json').write_text(json.dumps(lib, ensure_ascii=False, indent=1) + '\n')
print(f'{len(lib)} sections, {sum(len(s["pages"]) for s in lib)} pages')
PY
