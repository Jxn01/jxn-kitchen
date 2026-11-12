"""The know-how library (spec §6.8): knowhow/<section>.yaml, bilingual from the start. Loaded and validated at start —
the server refuses to start on any error, like the catalogue — and served whole as /api/knowhow.

A section: {id, order, icon, color, en: {title, sub}, hu: {title, sub}, pages: [...]}.
A page: {id, illustration? | chart? (charts.py), en: {title, body}, hu: {title, body}}; body = a small Markdown subset the web app renders
(## heading, paragraphs, - / 1. lists, **bold**, | tables |, > tip).
"""
from __future__ import annotations

import pathlib
from typing import Any

import yaml

from . import charts

ILLUSTRATIONS = ('doneness', 'sugar', 'smoke', 'oven', 'cuts', 'blend', 'balance', 'onion', 'angle', 'cutsizes', 'press',
                 'moka', 'eggtimer', 'eggfloat', 'fridge')   # web/src/components/illus/*
SECTION_KEYS = {'id', 'order', 'icon', 'color', 'en', 'hu', 'pages'}
PAGE_KEYS = {'id', 'illustration', 'chart', 'open', 'en', 'hu'}   # chart: see charts.py
OPENS = ('spices', 'sauces')                                    # open: a button to that section's engine
# every tile colour of the web palette (web/src/lib/palette.ts minus ink and cream) — kept equal by a test
COLORS = ('tomato', 'mustard', 'herb', 'sky', 'tangerine', 'berry', 'teal', 'plum', 'cocoa', 'butter', 'slate', 'salmon',
          'leaf', 'olive', 'wine', 'rust', 'mint', 'indigo')


def load(directory: pathlib.Path) -> list[dict[str, Any]]:
    sections = [yaml.safe_load(p.read_text()) for p in sorted(directory.glob('*.yaml'))]
    return sorted((s for s in sections if isinstance(s, dict)), key=lambda s: (s.get('order', 99), s.get('id', '')))


def validate(lib: list[dict[str, Any]], icon_ids: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for s in lib:
        sid = s.get('id', '?')
        if set(s) - SECTION_KEYS:
            errors.append(f'{sid}: unknown keys {sorted(set(s) - SECTION_KEYS)}')
        if sid in seen:
            errors.append(f'duplicate section {sid}')
        seen.add(sid)
        if s.get('color') not in COLORS:
            errors.append(f'{sid}: bad color {s.get("color")}')
        if icon_ids is not None and _icon_id(s.get('icon', '')) not in icon_ids:
            errors.append(f'{sid}: unknown icon {s.get("icon")}')
        for lang in ('en', 'hu'):
            t = s.get(lang) or {}
            if not (t.get('title') or '').strip() or not (t.get('sub') or '').strip():
                errors.append(f'{sid}: {lang} title/sub missing')
        pages = s.get('pages') or []
        if not pages:
            errors.append(f'{sid}: no pages')
        pids: set[str] = set()
        for p in pages:
            pid = f'{sid}/{p.get("id", "?")}'
            if set(p) - PAGE_KEYS:
                errors.append(f'{pid}: unknown keys {sorted(set(p) - PAGE_KEYS)}')
            if p.get('id') in pids:
                errors.append(f'duplicate page {pid}')
            pids.add(p.get('id'))
            if p.get('open') is not None and p['open'] not in OPENS:
                errors.append(f'{pid}: open must be one of {list(OPENS)}')
            if p.get('illustration') is not None and p['illustration'] not in ILLUSTRATIONS:
                errors.append(f'{pid}: unknown illustration {p["illustration"]}')
            if p.get('chart') is not None:
                if p.get('illustration') is not None:
                    errors.append(f'{pid}: a page has an illustration OR a chart, not both')
                errors.extend(charts.validate(pid, p['chart'], COLORS, icon_ids))
            for lang in ('en', 'hu'):
                t = p.get(lang) or {}
                if not (t.get('title') or '').strip() or len((t.get('body') or '').strip()) < 40:
                    errors.append(f'{pid}: {lang} title or body missing')
    return errors


def _icon_id(ref: str) -> str:
    return 'om-' + ref[3:].lower() if ref.startswith('om:') else ('c-' + ref[2:] if ref.startswith('c:') else ref)


def to_json(lib: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{'id': s['id'], 'icon': _icon_id(s['icon']), 'color': s['color'], 'en': s['en'], 'hu': s['hu'],
             'pages': [{'id': p['id'], 'illustration': p.get('illustration'),
                        'chart': charts.to_json(p['chart']) if p.get('chart') else None, 'open': p.get('open'),
                        'en': p['en'], 'hu': p['hu']}
                       for p in s['pages']]} for s in lib]
