"""Know-how infographics drawn from data.

A page may carry `chart: {type, ...}` instead of a hand-made `illustration`. The web app draws each type as an object
the data fills (web/src/components/illus/Chart.svelte): a measuring jug or a pot that fills to the tapped measure, a
wall thermometer with coloured bands, a pantry board of grouped icons, a strip of numbered recipe-card steps, bars, and
colour swatches. This module is the ONLY validator of that data — the web trusts what passes here.

Shared value kinds:
  Text   a non-empty string shown as-is in both languages ("1 dl", "°C"), or {en: str, hu: str}, both non-empty
  Fill   a drawing colour: a palette name (knowhow.COLORS) or "#RRGGBB" — never behind text
  Color  a palette name only (text sits on it, so it must carry ink text at >= 7:1, which every palette colour does)
  Icon   an OpenMoji reference "om:XXXX" or one of our own drawings "c:name" (icons/custom/name.svg); must be in the sprite

Types (keys marked ? are optional; every number is a plain int/float):
  vessel    shape: jug|pot|cup · max · unit?: Text · ticks?: [{value, label: Text}] ·
            items (2–8): [{value (0 < value <= max), label: Text, note: Text, fill?: Fill, icons?: [Icon] (<= 4)}]
  scale     unit: Text · min < max · bands (2–8): [{from < to, within min..max, fill: Fill, label: Text, note: Text,
            range?: Text (what the card prints instead of 'from–to unit', e.g. "−18 °C or colder")}] ·
            marks?: [{value within min..max, label: Text}]
  board     groups (2–4): [{color: Color, label: Text, note?: Text, icon?: Icon, items (1–14): [{label: Text, icon?: Icon}]}]
  steps     items (3–8): [{label: Text, note: Text, icon?: Icon, time?: Text}]
  bars      unit: Text · max · items (2–10): [{value (0 < value <= max), to? (value <= to <= max), label: Text,
            note?: Text, fill?: Fill}] · marker?: {value, label: Text}
  swatches  shape?: spoons|jars · items (2–10): [{fill: Fill, label: Text, note: Text, heat?: 0–5, value?: Text}]
  layers    shape: cup|glass|pot|jar · unit?: Text · items (2–10): [{label: Text, note: Text, value?: Text,
            layers (1–5): [{fill: Fill, part > 0, label: Text}] (bottom up)}] — the chosen item's layers stack in the
            vessel, each part's height relative to the largest item's total (a `vessel` is the one-layer case; both
            exist on purpose — vessel draws a level and floating contents, layers draws a recipe of parts)
  matrix    levels: [Text, Text, Text] (what 0 / 1 / 2 mean: no · works · best) · cols (2–6): [{label: Text, icon?: Icon,
            note: Text}] · rows (2–14): [{label: Text, icon?: Icon, cells: [0|1|2] — one per column}] — a column is the touch
            target (what it is for), a highlight slides to it
  picker    items (2–14): [{label: Text, note: Text, icon?: Icon, value?: Text}] — a grid of icon tiles, the chosen one's
            note on the card
"""
from __future__ import annotations

import re
from typing import Any

HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')

# type -> (required keys, optional keys); per-item rules are in the checkers below
TYPES: dict[str, tuple[set[str], set[str]]] = {
    'vessel': ({'type', 'shape', 'max', 'items'}, {'unit', 'ticks'}),
    'scale': ({'type', 'unit', 'min', 'max', 'bands'}, {'marks'}),
    'board': ({'type', 'groups'}, set()),
    'steps': ({'type', 'items'}, set()),
    'bars': ({'type', 'unit', 'max', 'items'}, {'marker'}),
    'swatches': ({'type', 'items'}, {'shape'}),
    'layers': ({'type', 'shape', 'items'}, {'unit'}),
    'matrix': ({'type', 'levels', 'cols', 'rows'}, set()),
    'picker': ({'type', 'items'}, set()),
}


def _sprite_id(ref: str) -> str:
    return 'om-' + ref[3:].lower() if ref.startswith('om:') else 'c-' + ref[2:]


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class _Check:
    def __init__(self, where: str, colors: tuple[str, ...], icon_ids: set[str] | None):
        self.where, self.colors, self.icon_ids, self.errors = where, colors, icon_ids, []

    def err(self, msg: str) -> None:
        self.errors.append(f'{self.where}: chart {msg}')

    def text(self, v: Any, what: str) -> None:
        if isinstance(v, str):
            if not v.strip():
                self.err(f'{what} is empty')
        elif isinstance(v, dict) and set(v) == {'en', 'hu'}:
            for lang in ('en', 'hu'):
                if not isinstance(v[lang], str) or not v[lang].strip():
                    self.err(f'{what} has no {lang}')
        else:
            self.err(f'{what} must be a string or {{en, hu}}')

    def fill(self, v: Any, what: str) -> None:
        if not (isinstance(v, str) and (v in self.colors or HEX.match(v))):
            self.err(f'{what} must be a palette colour or #RRGGBB, not {v!r}')

    def color(self, v: Any, what: str) -> None:
        if v not in self.colors:
            self.err(f'{what} must be a palette colour, not {v!r}')

    def icon(self, v: Any, what: str) -> None:
        if not (isinstance(v, str) and (v.startswith('om:') or v.startswith('c:'))):
            self.err(f'{what} must be an om:XXXX or c:name icon, not {v!r}')
        elif self.icon_ids is not None and _sprite_id(v) not in self.icon_ids:
            self.err(f'{what} {v} is not in the sprite')

    def keys(self, d: Any, req: set[str], opt: set[str], what: str) -> bool:
        if not isinstance(d, dict):
            self.err(f'{what} must be a mapping')
            return False
        if req - set(d):
            self.err(f'{what} misses {sorted(req - set(d))}')
        if set(d) - req - opt:
            self.err(f'{what} has unknown keys {sorted(set(d) - req - opt)}')
        return not (req - set(d))

    def items(self, v: Any, lo: int, hi: int, what: str) -> list:
        if not isinstance(v, list) or not lo <= len(v) <= hi:
            self.err(f'{what} needs {lo}–{hi} entries')
            return v if isinstance(v, list) else []
        return v


def validate(where: str, chart: Any, colors: tuple[str, ...], icon_ids: set[str] | None = None) -> list[str]:
    c = _Check(where, colors, icon_ids)
    if not isinstance(chart, dict) or chart.get('type') not in TYPES:
        c.err(f'type must be one of {sorted(TYPES)}')
        return c.errors
    t = chart['type']
    req, opt = TYPES[t]
    if not c.keys(chart, req, opt, t):
        return c.errors
    getattr(_Types, t)(c, chart)
    return c.errors


class _Types:
    @staticmethod
    def vessel(c: _Check, ch: dict) -> None:
        if ch['shape'] not in ('jug', 'pot', 'cup'):
            c.err('vessel shape must be jug, pot or cup')
        if not _num(ch['max']) or ch['max'] <= 0:
            c.err('vessel max must be a positive number')
            return
        if 'unit' in ch:
            c.text(ch['unit'], 'unit')
        for i, tk in enumerate(c.items(ch.get('ticks', []), 0, 12, 'ticks')):
            if c.keys(tk, {'value', 'label'}, set(), f'tick {i}'):
                if not _num(tk['value']) or not 0 < tk['value'] <= ch['max']:
                    c.err(f'tick {i} value must be within 0..max')
                c.text(tk['label'], f'tick {i} label')
        for i, it in enumerate(c.items(ch['items'], 2, 8, 'items')):
            if not c.keys(it, {'value', 'label', 'note'}, {'fill', 'icons'}, f'item {i}'):
                continue
            if not _num(it['value']) or not 0 < it['value'] <= ch['max']:
                c.err(f'item {i} value must be within 0..max')
            c.text(it['label'], f'item {i} label')
            c.text(it['note'], f'item {i} note')
            if 'fill' in it:
                c.fill(it['fill'], f'item {i} fill')
            for j, ic in enumerate(c.items(it.get('icons', []), 0, 4, f'item {i} icons')):
                c.icon(ic, f'item {i} icon {j}')

    @staticmethod
    def scale(c: _Check, ch: dict) -> None:
        c.text(ch['unit'], 'unit')
        lo, hi = ch['min'], ch['max']
        if not (_num(lo) and _num(hi) and lo < hi):
            c.err('scale needs numbers min < max')
            return
        for i, b in enumerate(c.items(ch['bands'], 2, 8, 'bands')):
            if not c.keys(b, {'from', 'to', 'fill', 'label', 'note'}, {'range'}, f'band {i}'):
                continue
            if 'range' in b:
                c.text(b['range'], f'band {i} range')
            if not (_num(b['from']) and _num(b['to']) and lo <= b['from'] < b['to'] <= hi):
                c.err(f'band {i} needs min <= from < to <= max')
            c.fill(b['fill'], f'band {i} fill')
            c.text(b['label'], f'band {i} label')
            c.text(b['note'], f'band {i} note')
        for i, m in enumerate(c.items(ch.get('marks', []), 0, 12, 'marks')):
            if c.keys(m, {'value', 'label'}, set(), f'mark {i}'):
                if not (_num(m['value']) and lo <= m['value'] <= hi):
                    c.err(f'mark {i} value must be within min..max')
                c.text(m['label'], f'mark {i} label')

    @staticmethod
    def board(c: _Check, ch: dict) -> None:
        for i, g in enumerate(c.items(ch['groups'], 2, 4, 'groups')):
            if not c.keys(g, {'color', 'label', 'items'}, {'note', 'icon'}, f'group {i}'):
                continue
            if 'icon' in g:
                c.icon(g['icon'], f'group {i} icon')
            c.color(g['color'], f'group {i} color')
            c.text(g['label'], f'group {i} label')
            if 'note' in g:
                c.text(g['note'], f'group {i} note')
            for j, it in enumerate(c.items(g['items'], 1, 14, f'group {i} items')):
                if c.keys(it, {'label'}, {'icon'}, f'group {i} item {j}'):
                    c.text(it['label'], f'group {i} item {j} label')
                    if 'icon' in it:
                        c.icon(it['icon'], f'group {i} item {j} icon')

    @staticmethod
    def steps(c: _Check, ch: dict) -> None:
        for i, it in enumerate(c.items(ch['items'], 3, 8, 'items')):
            if not c.keys(it, {'label', 'note'}, {'icon', 'time'}, f'step {i}'):
                continue
            c.text(it['label'], f'step {i} label')
            c.text(it['note'], f'step {i} note')
            if 'icon' in it:
                c.icon(it['icon'], f'step {i} icon')
            if 'time' in it:
                c.text(it['time'], f'step {i} time')

    @staticmethod
    def bars(c: _Check, ch: dict) -> None:
        c.text(ch['unit'], 'unit')
        if not _num(ch['max']) or ch['max'] <= 0:
            c.err('bars max must be a positive number')
            return
        for i, it in enumerate(c.items(ch['items'], 2, 10, 'items')):
            if not c.keys(it, {'value', 'label'}, {'to', 'note', 'fill'}, f'item {i}'):
                continue
            if not _num(it['value']) or not 0 < it['value'] <= ch['max']:
                c.err(f'item {i} value must be within 0..max')
            if 'to' in it and not (_num(it['to']) and _num(it['value']) and it['value'] <= it['to'] <= ch['max']):
                c.err(f'item {i} to must be within value..max')
            c.text(it['label'], f'item {i} label')
            if 'note' in it:
                c.text(it['note'], f'item {i} note')
            if 'fill' in it:
                c.fill(it['fill'], f'item {i} fill')
        if 'marker' in ch and c.keys(ch['marker'], {'value', 'label'}, set(), 'marker'):
            if not (_num(ch['marker']['value']) and 0 < ch['marker']['value'] <= ch['max']):
                c.err('marker value must be within 0..max')
            c.text(ch['marker']['label'], 'marker label')

    @staticmethod
    def swatches(c: _Check, ch: dict) -> None:
        if ch.get('shape', 'spoons') not in ('spoons', 'jars'):
            c.err('swatches shape must be spoons or jars')
        for i, it in enumerate(c.items(ch['items'], 2, 10, 'items')):
            if not c.keys(it, {'fill', 'label', 'note'}, {'heat', 'value'}, f'item {i}'):
                continue
            if 'value' in it:
                c.text(it['value'], f'item {i} value')
            c.fill(it['fill'], f'item {i} fill')
            c.text(it['label'], f'item {i} label')
            c.text(it['note'], f'item {i} note')
            if 'heat' in it and not (isinstance(it['heat'], int) and 0 <= it['heat'] <= 5):
                c.err(f'item {i} heat must be 0–5')


    @staticmethod
    def layers(c: _Check, ch: dict) -> None:
        if ch['shape'] not in ('cup', 'glass', 'pot', 'jar'):
            c.err('layers shape must be cup, glass, pot or jar')
        if 'unit' in ch:
            c.text(ch['unit'], 'unit')
        for i, it in enumerate(c.items(ch['items'], 2, 10, 'items')):
            if not c.keys(it, {'label', 'note', 'layers'}, {'value'}, f'item {i}'):
                continue
            c.text(it['label'], f'item {i} label')
            c.text(it['note'], f'item {i} note')
            if 'value' in it:
                c.text(it['value'], f'item {i} value')
            for j, ly in enumerate(c.items(it['layers'], 1, 5, f'item {i} layers')):
                if c.keys(ly, {'fill', 'part', 'label'}, set(), f'item {i} layer {j}'):
                    c.fill(ly['fill'], f'item {i} layer {j} fill')
                    c.text(ly['label'], f'item {i} layer {j} label')
                    if not _num(ly['part']) or ly['part'] <= 0:
                        c.err(f'item {i} layer {j} part must be a positive number')


    @staticmethod
    def matrix(c: _Check, ch: dict) -> None:
        lv = ch['levels']
        if not isinstance(lv, list) or len(lv) != 3:
            c.err('matrix levels must be three texts (0 · 1 · 2)')
        else:
            for i, t in enumerate(lv):
                c.text(t, f'level {i}')
        cols = c.items(ch['cols'], 2, 6, 'cols')
        for i, col in enumerate(cols):
            if c.keys(col, {'label', 'note'}, {'icon'}, f'col {i}'):
                c.text(col['label'], f'col {i} label')
                c.text(col['note'], f'col {i} note')
                if 'icon' in col:
                    c.icon(col['icon'], f'col {i} icon')
        for i, row in enumerate(c.items(ch['rows'], 2, 14, 'rows')):
            if not c.keys(row, {'label', 'cells'}, {'icon'}, f'row {i}'):
                continue
            c.text(row['label'], f'row {i} label')
            if 'icon' in row:
                c.icon(row['icon'], f'row {i} icon')
            cells = row['cells']
            if not (isinstance(cells, list) and len(cells) == len(cols) and all(x in (0, 1, 2) and not isinstance(x, bool) for x in cells)):
                c.err(f'row {i} cells must be one 0, 1 or 2 per column')

    @staticmethod
    def picker(c: _Check, ch: dict) -> None:
        for i, it in enumerate(c.items(ch['items'], 2, 14, 'items')):
            if not c.keys(it, {'label', 'note'}, {'icon', 'value'}, f'item {i}'):
                continue
            c.text(it['label'], f'item {i} label')
            c.text(it['note'], f'item {i} note')
            if 'icon' in it:
                c.icon(it['icon'], f'item {i} icon')
            if 'value' in it:
                c.text(it['value'], f'item {i} value')


def icon_refs(chart: dict) -> list[str]:
    """Every icon a chart uses (for the sprite and for to_json's id mapping)."""
    out: list[str] = []

    def walk(n: Any) -> None:
        if isinstance(n, dict):
            for k, v in n.items():
                if k == 'icon' and isinstance(v, str):
                    out.append(v)
                elif k == 'icons' and isinstance(v, list):
                    out.extend(x for x in v if isinstance(x, str))
                else:
                    walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(chart)
    return out


def to_json(chart: dict) -> dict:
    """The chart as the web gets it: icons as sprite ids (om:1F969 -> om-1f969), everything else unchanged."""
    def conv(n: Any) -> Any:
        if isinstance(n, dict):
            return {k: (_sprite_id(v) if k == 'icon' and isinstance(v, str) else
                        [_sprite_id(x) for x in v] if k == 'icons' and isinstance(v, list) else conv(v))
                    for k, v in n.items()}
        if isinstance(n, list):
            return [conv(v) for v in n]
        return n
    return conv(chart)
