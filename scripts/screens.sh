#!/usr/bin/env bash
# Screenshot routes of the scratch build at the three sizes the standing rules require, in EN and HU:
#   kiosk 1024x640 @ DPR 1.25 · desktop 1280x720 · phone 390x844 @ DPR 2
# usage: scripts/screens.sh [route ...]     (routes are hashes, default: / /settings /idle)
#        SCREENS_PANTRY='item group:<id> …' scripts/screens.sh /pantry   — seed some pantry state first
#        SCREENS_RECIPES=1 scripts/screens.sh /recipes /recipe/1          — seed the fixture recipes
#        SCREENS_RECIPES=1 SCREENS_FOLDERS=1 scripts/screens.sh /recipes /recipes/1 — and file them into demo folders
#        SCREENS_TIMERS='Tészta:600;Rizs:1' scripts/screens.sh / /timers  — running timers (and an ended one)
#        SCREENS_LANGS='en' SCREENS_SIZES='kiosk phone' scripts/screens.sh …   — only these languages / sizes
#        (sizes: kiosk 720p phone iphone = 393x852 @ DPR 3, an iPhone 15/16; iphone-app = 393x759 @ 3, the same phone
#         running the home-screen app, whose notch and home bar take 59 + 34 px — what the owner sees; se = 375x667 @ 2,
#         the smallest iPhone; land = 844x390 @ 3, an iPhone on its side, which gets the two-column kiosk layout)
#        SCREENS_STILL=1 …   — animations off (prefers-reduced-motion), so two builds can be compared pixel for pixel
# Output: ~/.cache/jxn-kitchen/screens/<lang>-<size>-<route>.png. LOOK at them — that is the point.
# The FIRST shot of a run can catch the app mid-load (2026-11-11: a pantry with one tile of twelve); shoot it again, or put
# a cheap route first, before reading anything into it.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${KITCHEN_SCRATCH:-$HOME/.cache/jxn-kitchen}"
OUT="$CACHE/screens"; DATA="$CACHE/screens-data"; PORT="${PORT:-8765}"
mkdir -p "$OUT" "$DATA"
# a FRESH browser profile every run: the app's service worker would otherwise serve the previous build's shell (and its
# assets) from the profile's cache — a screenshot that may not show the current build proves nothing (2026-10-11)
rm -rf "$CACHE/chrome-shots"
ROUTES=("$@"); [ ${#ROUTES[@]} -eq 0 ] && ROUTES=(/ /settings /idle)
CHROME="$(command -v google-chrome-stable || command -v google-chrome || command -v chromium)"
# the shared headless flags (scripts/chrome-flags.txt says why; scripts/cdp.py reads the same file)
mapfile -t CHROME_FLAGS < <(grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' "$REPO/scripts/chrome-flags.txt")
VENV="$HOME/.local/share/venvs/jxn-kitchen"

# HA weather is optional for screenshots: use a token from the environment if the caller provides one.
# KITCHEN_SHOPPING_SYNC_SECONDS=0: a screenshot server must never touch the real HA to-do list (demo items!)
KITCHEN_SHOPPING_SYNC_SECONDS=0 KITCHEN_DATA_DIR="$DATA" KITCHEN_STATIC_DIR="$CACHE/web/dist" PYTHONPATH="$REPO/server" \
  "$VENV/bin/uvicorn" kitchen.main:app --host 127.0.0.1 --port "$PORT" --log-level warning &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for i in $(seq 1 50); do curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null && break; sleep 0.2; done

shot() { # lang size w h dpr route
  local name="${1}-${2}-$(echo "$6" | tr '/' '_' | sed 's/^_$/home/;s/^_//')"
  timeout 60 "$CHROME" --headless=new "${CHROME_FLAGS[@]}" --disable-gpu --hide-scrollbars --user-data-dir="$CACHE/chrome-shots" \
    --window-size="$3,$4" --force-device-scale-factor="$5" --virtual-time-budget=4000 ${SCREENS_STILL:+--force-prefers-reduced-motion} \
    --screenshot="$OUT/$name.png" "http://127.0.0.1:$PORT/?shot=1#$6" >/dev/null 2>&1 || echo "TIMEOUT $name" >&2
  echo "$OUT/$name.png"
}
# optional demo state: SCREENS_PANTRY="chicken-breast chicken-drumsticks group:pork" switches those on first
for node in ${SCREENS_PANTRY:-}; do
  curl -sf -X PUT -H 'Content-Type: application/json' -d '{"have":true}' "http://127.0.0.1:$PORT/api/pantry/$node" >/dev/null \
    || { echo "screens.sh: could not seed pantry node '$node' (not in the catalogue?)" >&2; exit 1; }
done
# SCREENS_SHOPPING='Tej;Kenyér;item:sour-cream' seeds the shopping list (item:<id> adds a catalogue item)
IFS=';' read -ra SHOP <<< "${SCREENS_SHOPPING:-}"
for s in "${SHOP[@]}"; do
  [ -z "$s" ] && continue
  if [[ "$s" == item:* ]]; then body="{\"item_id\":\"${s#item:}\"}"; else body="{\"text\":\"$s\"}"; fi
  curl -sf -X POST -H 'Content-Type: application/json' -d "$body" "http://127.0.0.1:$PORT/api/shopping" >/dev/null \
    || { echo "screens.sh: could not seed shopping entry '$s' (unknown item id?)" >&2; exit 1; }
done
# SCREENS_TIMERS='Tészta:600;Rizs:1' starts timers (label:seconds); one of 1 s has ended (Done card) by the first shot
IFS=';' read -ra TIMERS <<< "${SCREENS_TIMERS:-}"
for tm in "${TIMERS[@]}"; do
  [ -z "$tm" ] && continue
  curl -sf -X POST -H 'Content-Type: application/json' -d "{\"label\":\"${tm%%:*}\",\"seconds\":${tm##*:}}" \
    "http://127.0.0.1:$PORT/api/timers" >/dev/null || { echo "screens.sh: could not start timer '$tm'" >&2; exit 1; }
done
[ ${#TIMERS[@]} -gt 0 ] && sleep 2
# SCREENS_DAY=1 switches the night window off (night_start = night_end), so a night-time run still shows the day look
if [ -n "${SCREENS_DAY:-}" ]; then
  curl -sf -X PUT -H 'Content-Type: application/json' -d '{"night_start":0,"night_end":0}' "http://127.0.0.1:$PORT/api/settings" >/dev/null \
    || { echo "screens.sh: could not switch the night window off" >&2; exit 1; }
fi
# SCREENS_RECIPES=1 seeds the recipe pages in the test fixtures (offline, via the importer's extraction)
if [ -n "${SCREENS_RECIPES:-}" ] && [ "$(curl -sf "http://127.0.0.1:$PORT/api/recipes")" = "[]" ]; then
  "$VENV/bin/python" "$REPO/scripts/demo-recipes.py" | "$VENV/bin/python" -c '
import json, sys, urllib.request
for r in json.load(sys.stdin):
    req = urllib.request.Request(sys.argv[1] + "/api/recipes", json.dumps(r).encode(), {"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()' "http://127.0.0.1:$PORT"
fi
# SCREENS_FOLDERS=1 (with SCREENS_RECIPES=1) files the demo recipes into a small folder tree: Levesek › Magyar, Édességek,
# Gyors vacsorák — the first recipe in Levesek › Magyar, the second in Levesek, the third in Gyors vacsorák, the rest on top
if [ -n "${SCREENS_FOLDERS:-}" ] && [ "$(curl -sf "http://127.0.0.1:$PORT/api/folders")" = "[]" ]; then
  "$VENV/bin/python" - "http://127.0.0.1:$PORT" <<'PYSEED' || { echo "screens.sh: could not seed folders" >&2; exit 1; }
import json, sys, urllib.request
base = sys.argv[1]
def call(method, path, body=None):
    req = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None,
                                 {"Content-Type": "application/json"}, method=method)
    return json.load(urllib.request.urlopen(req))
mk = lambda name, parent=None: call("POST", "/api/folders", {"name": name, "parent_id": parent})["id"]
soups = mk("Levesek"); hu = mk("Magyar", soups); mk("Édességek"); quick = mk("Gyors vacsorák")
ids = sorted(r["id"] for r in call("GET", "/api/recipes"))
for rid, fid in zip(ids, (hu, soups, quick)):
    call("POST", "/api/recipes/move", {"ids": [rid], "folder_id": fid})
print(f"folders: Levesek={soups} Magyar={hu} Gyors={quick}", file=sys.stderr)
PYSEED
fi
for lang in ${SCREENS_LANGS:-en hu}; do
  curl -sf -X PUT -H 'Content-Type: application/json' -d "{\"language\":\"$lang\"}" "http://127.0.0.1:$PORT/api/settings" >/dev/null
  for r in "${ROUTES[@]}"; do
    for size in ${SCREENS_SIZES:-kiosk 720p phone}; do
      case "$size" in
        kiosk)  shot "$lang" kiosk 1024 640 1.25 "$r" ;;
        720p)   shot "$lang" 720p 1280 720 1 "$r" ;;
        phone)  shot "$lang" phone 390 844 2 "$r" ;;
        iphone) shot "$lang" iphone 393 852 3 "$r" ;;
        iphone-app) shot "$lang" iphone-app 393 759 3 "$r" ;;
        se)     shot "$lang" se 375 667 2 "$r" ;;
        land)   shot "$lang" land 844 390 3 "$r" ;;
        *) echo "screens.sh: unknown size '$size'" >&2; exit 2 ;;
      esac
    done
  done
done
