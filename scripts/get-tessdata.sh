#!/usr/bin/env bash
# Tesseract models for the OCR tests on this machine, into the scratch cache (nothing system-wide; the server image
# installs Debian's tesseract-ocr-hun/-eng instead). Pinned to tessdata_fast 4.1.0.
#   scripts/get-tessdata.sh        then tests find them via TESSDATA_PREFIX (set by server/tests/conftest.py)
set -euo pipefail
DIR="${KITCHEN_SCRATCH:-$HOME/.cache/jxn-kitchen}/tessdata"
mkdir -p "$DIR"
for lang in hun eng osd; do
  [ -s "$DIR/$lang.traineddata" ] && continue
  curl -fsSL -o "$DIR/$lang.traineddata.part" "https://github.com/tesseract-ocr/tessdata_fast/raw/4.1.0/$lang.traineddata"
  mv "$DIR/$lang.traineddata.part" "$DIR/$lang.traineddata"
done
ls -la "$DIR"
