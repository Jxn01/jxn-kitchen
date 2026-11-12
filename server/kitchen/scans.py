"""Scans -> draft recipes: the in-app photo upload (`POST /api/scan`) and the scan inbox (the share's
`scans/` folder, where the scanner UI saves; polled, each file imported once).

OCR runs in a worker thread (it is CPU-heavy); everything that touches SQLite stays on the event loop (the
connection is single-threaded on purpose). One import at a time.
"""
from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import sqlite3
import time
from datetime import datetime
from typing import Any, Callable

from . import images, ocr, recipes
from .matcher import Matcher

log = logging.getLogger(__name__)
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.bmp', '.gif'}
SCAN_EXT = IMAGE_EXT | {'.pdf'}
SETTLE_SECONDS = 15          # a file younger than this may still be being written by the scanner
MAX_BYTES = 80 * 1024 * 1024


class NotAScan(ValueError):
    pass


def _is_pdf(data: bytes) -> bool:
    return data[:5] == b'%PDF-'


def _pages_and_text(data: bytes) -> list[tuple[bytes, str]]:
    """Worker thread: [(page image, OCR text)] — a PDF is one entry per page."""
    pages = ocr.pdf_pages(data) if _is_pdf(data) else [data]
    out = []
    for p in pages:
        try:
            out.append((p, ocr.image_text(p)))
        except Exception as e:             # one bad page: still a draft (the photo, no text), never a lost scan
            log.warning('OCR failed on a page: %r', e)
            out.append((p, ''))
    return out


class Scanner:
    def __init__(self, conn: sqlite3.Connection, matcher: Matcher, data_dir: pathlib.Path, now: Callable[[], datetime],
                 changed: Callable[[int], None], scans_dir: pathlib.Path | None = None):
        self.conn, self.matcher, self.data_dir, self.now, self.changed = conn, matcher, data_dir, now, changed
        self.scans_dir = scans_dir
        self.lock = asyncio.Lock()

    async def import_bytes(self, data: bytes, source: str) -> list[int]:
        if not data or len(data) > MAX_BYTES:
            raise NotAScan('empty or too large')
        if not _is_pdf(data):
            try:
                images.open_image(data, images.SCAN_FORMATS, load=False)   # the shared guard (header only)
            except images.BadImage as e:
                raise NotAScan(f'not an image or a PDF ({e})') from e
        async with self.lock:
            pages = await asyncio.to_thread(_pages_and_text, data)
            ids = []
            for n, (img, text) in enumerate(pages, 1):
                r = ocr.recipe_from_text(text)
                stem = pathlib.Path(source).stem
                title = r['title'] or (f'{stem} ({n})' if len(pages) > 1 else stem) or 'Scan'
                note = (f'Szkennelésből ({source}' + (f', {n}. oldal' if len(pages) > 1 else '') + '): '
                        'nézd át minden sorát. / Read from a scan: check every line.')
                rid = recipes.save(self.conn, self.matcher, {
                    'title': title[:200], 'servings': r['servings'] or 4, 'ingredients': r['ingredients'][:200],
                    'steps': r['steps'][:100], 'tags': ['scan'], 'notes': note, 'origin': 'scan'}, self.now())
                try:
                    name = await asyncio.to_thread(images.store, self.data_dir / 'images', rid, img, images.SCAN_FORMATS)
                    recipes.set_image(self.conn, rid, name)
                except images.BadImage:
                    pass
                self.changed(rid)
                ids.append(rid)
            return ids

    async def poll(self) -> int:
        """Import every settled, not yet imported scan in the inbox. Returns how many files were imported."""
        d = self.scans_dir
        if d is None or not d.is_dir():
            return 0
        done = 0
        for f in sorted(d.rglob('*')):
            if not f.is_file() or f.suffix.lower() not in SCAN_EXT or f.name.startswith('.'):
                continue
            st = f.stat()
            if time.time() - st.st_mtime < SETTLE_SECONDS:
                continue
            key = (str(f.relative_to(d)), st.st_size, st.st_mtime)
            if self.conn.execute('SELECT 1 FROM scan_import WHERE path = ? AND size = ? AND mtime = ?', key).fetchone():
                continue
            try:
                ids = await self.import_bytes(f.read_bytes(), key[0])
            except Exception as e:
                # ANY failure is recorded too: an unrecorded file would be retried every minute
                # forever and, sorted first, block every scan after it
                log.warning('scan inbox: skipped %r (%r)', key[0], e)
                ids = []
            self.conn.execute('INSERT OR IGNORE INTO scan_import (path, size, mtime, recipe_ids, at) VALUES (?, ?, ?, ?, ?)',
                              (*key, json.dumps(ids), self.now().isoformat()))
            log.info('scan inbox: %r -> recipes %r', key[0], ids)
            done += 1
        return done

    def status(self) -> dict[str, Any]:
        n = self.conn.execute('SELECT COUNT(*) FROM scan_import').fetchone()[0]
        return {'inbox': self.scans_dir is not None and self.scans_dir.is_dir(), 'imported': n}

    async def run(self, every: float = 60.0) -> None:
        while True:
            try:
                await self.poll()
            except Exception:
                log.exception('scan inbox round failed')
            await asyncio.sleep(every)
