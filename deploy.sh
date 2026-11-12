#!/usr/bin/env bash
# Deploy JXN Kitchen to a Docker host over SSH: run every test, sync the source, rebuild and restart the container
# there, then wait until it answers. Usage: KITCHEN_HOST=user@server ./deploy.sh [--skip-tests]
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
HOST="${KITCHEN_HOST:?set KITCHEN_HOST=user@server}"
BUILD="$(git -C "$REPO" describe --always --dirty 2>/dev/null || date +%s)"
VENV="$HOME/.local/share/venvs/jxn-kitchen"

if [ "${1:-}" != "--skip-tests" ]; then
  (cd "$REPO" && "$VENV/bin/python" -m pytest -q)
  "$REPO/scripts/build-web.sh" --test-only
fi

ssh "$HOST" 'mkdir -p /srv/compose/kitchen/src && test -f /etc/kitchen/kitchen.env || sudo test -f /etc/kitchen/kitchen.env'
# Only files git can see leave this machine: tracked + untracked-but-not-ignored. Ignored files — .env*, *.token,
# kitchen.env, build output — never reach the server or the image's build context (the hygiene tests keep every
# secret-shaped file ignored). Staged locally first so --delete mirrors exactly that set.
STAGE="${KITCHEN_SCRATCH:-$HOME/.cache/jxn-kitchen}/deploy-src"
rm -rf "$STAGE" && mkdir -p "$STAGE"
git -C "$REPO" ls-files -z --cached --others --exclude-standard \
  | rsync -a --from0 --files-from=- "$REPO/" "$STAGE/"
rsync -az --delete "$STAGE/" "$HOST:/srv/compose/kitchen/src/"
# pipefail: the build is piped through tail, and a pipeline's status is its last stage's -- without it a failed build
# went on to `up -d` the old image and the deploy reported success
ssh "$HOST" "set -o pipefail; install -m 0644 /srv/compose/kitchen/src/deploy/compose.yaml /srv/compose/kitchen/compose.yaml \
  && sudo install -d -o 10001 -g 10001 -m 0750 /srv/kitchen/data \
  && cd /srv/compose/kitchen && sudo env KITCHEN_BUILD='$BUILD' docker compose build --pull 2>&1 | tail -3 && sudo env KITCHEN_BUILD='$BUILD' docker compose up -d 2>&1 | tail -3"   # sudo: compose reads the 0600 root env file

for i in $(seq 1 60); do
  out="$(ssh "$HOST" 'curl -s -w " HTTP%{http_code}" http://127.0.0.1:8090/api/health' 2>/dev/null || true)"
  case "$out" in
    *HTTP200) echo "deployed $BUILD: ${out% HTTP200}"; exit 0 ;;
    *'"dangling"'*) echo "deployed $BUILD, but stored ids are missing from the catalogue — add them to" \
                         "catalogue/replaced.yaml and deploy again: ${out% HTTP*}" >&2; exit 1 ;;
  esac
  sleep 2
done
echo "kitchen did not come up — docker logs:" >&2
ssh "$HOST" 'docker logs --tail 40 kitchen' >&2
exit 1
