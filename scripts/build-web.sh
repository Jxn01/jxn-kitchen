#!/usr/bin/env bash
# Build the web app in a SCRATCH COPY, never inside the shared tree (~/Projects is on the Shared NTFS drive:
# a Linux node_modules there is wrong for Windows and slow on ntfs3). Output: ~/.cache/jxn-kitchen/web/dist
#   scripts/build-web.sh            build
#   scripts/build-web.sh --test     run the vitest suite and the type check (svelte-check, no warnings), then build
#   scripts/build-web.sh --test-only
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH="${KITCHEN_SCRATCH:-$HOME/.cache/jxn-kitchen}/web"
mkdir -p "$SCRATCH"
rsync -a --delete --exclude node_modules --exclude dist "$REPO/web/" "$SCRATCH/"
cd "$SCRATCH"
if [ -f package-lock.json ]; then
  npm ci --no-audit --no-fund --loglevel=error
else
  npm install --no-audit --no-fund --loglevel=error
  cp package-lock.json "$REPO/web/package-lock.json"     # first run: commit the lockfile it produced
fi
# the type check is part of the tests: no error and no warning (errors in the test files alone could hide
# a real one in src/)
check() { npx svelte-check --tsconfig ./tsconfig.json --fail-on-warnings --output human-verbose >/dev/null 2>&1 \
            || { npx svelte-check --tsconfig ./tsconfig.json --fail-on-warnings; return 1; }; echo "svelte-check: 0 errors, 0 warnings"; }
case "${1:-}" in
  --test)      npx vitest run; check ;;
  --test-only) npx vitest run; check; exit 0 ;;
esac
# `npm run build` = the app + dist/overlay.js (the Browse overlay) — the SAME command the Dockerfile runs
KITCHEN_BUILD="$(git -C "$REPO" describe --always --dirty 2>/dev/null || date +%s)" npm run build --silent
echo "built: $SCRATCH/dist ($(stat -c %s dist/overlay.js) byte overlay)"
