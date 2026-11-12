"""Digitising: a printed recipe (a scan or a photo) -> text -> a draft recipe.

OCR is the `tesseract` CLI (Hungarian + English models; `--psm 1` = automatic page layout WITH orientation detection,
so a page scanned sideways comes out upright). Images are cleaned up first with Pillow; PDFs are split into one image
per page with `pdftoppm`. `recipe_from_text()` turns the text into title / servings / ingredient lines / steps. The
result is always a DRAFT for the user to check: OCR text never earns a gluten verdict by itself — every line still
goes through the parser, the matcher and the gluten engine, and an unreadable line stays "unknown".
"""
from __future__ import annotations

import io
import pathlib
import re
import subprocess
import tempfile
from typing import Any

from PIL import Image, ImageOps

from . import images
from .catalogue import fold
from .ingredients import parse_line

TESSERACT_TIMEOUT = 180     # s per page (the kiosk never waits on it: imports run off the request path or async)
MAX_PDF_PAGES = 60
MAX_PAGE_PX = 3000          # a PDF page is rendered to at most this many pixels on its long side, whatever size it declares


class OcrFailed(RuntimeError):
    pass


def _prepare(data: bytes) -> Image.Image:
    try:
        img = images.open_image(data, images.SCAN_FORMATS)       # the shared guard: formats + pixel count first
    except images.BadImage as e:
        raise OcrFailed(str(e)) from e
    img = ImageOps.exif_transpose(img).convert('L')
    if max(img.size) < 1600:                     # small photos: Tesseract reads best around 300 dpi
        scale = 1600 / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    return ImageOps.autocontrast(img, cutoff=1)


def image_text(data: bytes) -> str:
    img = _prepare(data)       # raises OcrFailed for anything that isn't a usable image
    with tempfile.TemporaryDirectory() as d:
        src = pathlib.Path(d) / 'page.png'
        img.save(src)
        try:
            out = subprocess.run(['tesseract', str(src), 'stdout', '-l', 'hun+eng', '--psm', '1'],
                                 capture_output=True, timeout=TESSERACT_TIMEOUT, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise OcrFailed(f'tesseract: {type(e).__name__}') from e
    return out.stdout.decode('utf-8', errors='replace')


def pdf_pages(data: bytes, dpi: int = 200) -> list[bytes]:
    """Each page of a PDF as a PNG (a scanned stack: one recipe per page)."""
    with tempfile.TemporaryDirectory() as d:
        src = pathlib.Path(d) / 'in.pdf'
        src.write_bytes(data)
        try:
            # -scale-to caps the long side whatever page size the PDF declares (a "200-inch page" stays 3000 px)
            subprocess.run(['pdftoppm', '-r', str(dpi), '-scale-to', str(MAX_PAGE_PX), '-png', '-l', str(MAX_PDF_PAGES),
                            str(src), str(pathlib.Path(d) / 'p')], capture_output=True, timeout=300, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise OcrFailed(f'pdftoppm: {type(e).__name__}') from e
        return [p.read_bytes() for p in sorted(pathlib.Path(d).glob('p-*.png'))]


# --- structuring ----------------------------------------------------------------------------------------------

_ING_HEAD = re.compile(r'^(hozzavalok?|hozzavalo\b.*|ingredients?)\s*:?\s*$')
_STEP_HEAD = re.compile(r'^(elkeszites(e)?|elkeszitesi mod|keszites(e)?|a keszites menete|method|directions|'
                        r'instructions|preparation)\s*:?\s*$')
_SERVINGS = re.compile(r'(\d+)\s*(szemelyre|fore|adag|szelet)|serves\s*(\d+)|(\d+)\s*(servings|portions)')
_NUMBERED = re.compile(r'^\s*(\d{1,2})\s*[.)]\s+')


def _servings(line: str) -> int | None:
    m = _SERVINGS.search(fold(line))
    if not m:
        return None
    n = int(next(g for g in (m.group(1), m.group(3), m.group(4)) if g))
    return n if 1 <= n <= 50 else None


def _is_ingredient(line: str) -> bool:
    if len(line) > 70:
        return False
    return any(p.qty is not None or p.unit is not None for p in parse_line(line))


def _paragraphs(lines: list[str]) -> list[str]:
    """Steps from OCR lines. A new step starts at a numbered line ("2. ", "3) "), or where a sentence ended and the next
    line starts with a capital. A line starting lowercase always continues the current step — also across a blank
    line (Tesseract splits a wrapped paragraph into blocks) — and "meg-" + "főzzük" is rejoined."""
    steps: list[str] = []
    cur = ''
    gap = False
    for raw in lines:
        line = raw.strip()
        if not line:
            gap = True
            continue
        m = _NUMBERED.match(line)
        if m:
            if cur:
                steps.append(cur)
            cur, gap = line[m.end():], False
            continue
        continues = line[:1].islower() or (cur and not gap and not re.search(r'[.!?:]["”)]?$', cur))
        if cur and continues:
            cur = cur[:-1] + line if cur.endswith('-') and line[:1].islower() else f'{cur} {line}'
        else:
            if cur:
                steps.append(cur)
            cur = line
        gap = False
    if cur:
        steps.append(cur)
    return [re.sub(r'\s+', ' ', s).strip() for s in steps if s.strip()]


def recipe_from_text(text: str) -> dict[str, Any]:
    lines = [l.rstrip() for l in (text or '').replace('\x0c', '\n').splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    folded = [fold(l) for l in lines]
    ing_at = next((i for i, f in enumerate(folded) if _ING_HEAD.match(f)), None)
    step_at = next((i for i, f in enumerate(folded) if _STEP_HEAD.match(f) and (ing_at is None or i > ing_at)), None)

    title, servings, head_end = '', None, 0
    for i, l in enumerate(lines):
        if i == ing_at or i == step_at:
            head_end = i
            break
        s = l.strip()
        if not s:
            continue
        sv = _servings(s)
        if sv and servings is None:
            servings = sv
            head_end = i + 1
            continue
        if not title and not _is_ingredient(s):
            title = s
            head_end = i + 1
            continue
        head_end = i
        break
    else:
        head_end = len(lines)

    if ing_at is not None:
        ing_block = lines[ing_at + 1:step_at if step_at is not None else len(lines)]
        ingredients = [l.strip() for l in ing_block if l.strip()]
        rest = lines[step_at + 1:] if step_at is not None else []
        if step_at is None:        # no method header: the ingredient lines end where the quantities stop
            ingredients, rest = _split_trailing(ingredients)
    else:
        body = lines[head_end:step_at if step_at is not None else len(lines)]
        ingredients, tail = [], []
        for j, l in enumerate(body):
            s = l.strip()
            if not s:
                if ingredients:
                    tail = body[j + 1:]
                    break
                continue
            if _is_ingredient(s):
                ingredients.append(s)
            else:
                tail = body[j:]
                break
        rest = lines[step_at + 1:] if step_at is not None else tail
    return {'title': title, 'servings': servings, 'ingredients': ingredients, 'steps': _paragraphs(rest)}


def _split_trailing(block: list[str]) -> tuple[list[str], list[str]]:
    for i, l in enumerate(block):
        if not _is_ingredient(l) and len(l) > 40:
            return block[:i], block[i:]
    return block, []
