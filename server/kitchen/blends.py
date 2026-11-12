"""The owner's spice blends (spec 2026-10-19 §4.4, §6.2, §8): storage, the seeds, summaries and the blend's GF line.

The flavour verdict comes from the spice engine (a pure function of the parts); the gluten line comes from the gluten
engine (catalogue + pantry), like a recipe's — the two never mix. Seeds: the 16 DIY classics, inserted once (a
`counter` row `seeded:blends` remembers it, so deleting every blend never brings them back).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from . import gluten
from .catalogue import Catalogue, fold
from .recipes import guess_lang
from .spice_data import SpiceData
from .spice_engine import SpiceEngine

SEEDED = 'seeded:blends'
CAUTION = {'ok': 0, 'yours': 1, 'check': 2}     # a blend's GF state is its most cautious jar's


class NotFound(KeyError):
    pass


class InUse(Exception):
    """A sauce uses this blend: deleting it would leave the sauce with a hole (spec §4.4)."""

    def __init__(self, sauces: list[dict[str, Any]]):
        super().__init__('used by sauces')
        self.sauces = sauces


def get_row(conn: sqlite3.Connection, bid: int) -> sqlite3.Row:
    r = conn.execute('SELECT * FROM blend WHERE id = ?', (bid,)).fetchone()
    if r is None:
        raise NotFound(bid)
    return r


def parts(conn: sqlite3.Connection, bid: int) -> list[tuple[str, float]]:
    return [(p['spice_id'], p['parts']) for p in
            conn.execute('SELECT spice_id, parts FROM blend_part WHERE blend_id = ? ORDER BY pos', (bid,))]


def tags(conn: sqlite3.Connection, bid: int) -> list[str]:
    return [t['tag'] for t in conn.execute('SELECT tag FROM blend_tag WHERE blend_id = ? ORDER BY tag', (bid,))]


def save(conn: sqlite3.Connection, data: dict[str, Any], now: datetime, bid: int | None = None,
         origin: str = 'typed', classic_id: str | None = None) -> int:
    """Create (bid None) or replace a blend. `data`: name, notes?, tags?, parts [{spice, parts}], lang?"""
    ts = now.isoformat()
    name = data['name'].strip()
    lang = data.get('lang') or guess_lang(name, data.get('notes') or '')
    conn.execute('BEGIN')
    try:
        if bid is None:
            bid = conn.execute('INSERT INTO blend (name, lang, notes, origin, classic_id, created_at, updated_at) '
                               'VALUES (?,?,?,?,?,?,?)', (name, lang, data.get('notes'), origin, classic_id, ts, ts)).lastrowid
        else:
            get_row(conn, bid)
            conn.execute('UPDATE blend SET name=?, lang=?, notes=?, updated_at=? WHERE id=?',
                         (name, lang, data.get('notes'), ts, bid))
            for t in ('blend_part', 'blend_tag'):
                conn.execute(f'DELETE FROM {t} WHERE blend_id = ?', (bid,))
        for pos, p in enumerate(data['parts']):
            conn.execute('INSERT INTO blend_part (blend_id, pos, spice_id, parts) VALUES (?,?,?,?)',
                         (bid, pos, p['spice'], float(p['parts'])))
        for t in sorted({t.strip().lower() for t in data.get('tags') or [] if t.strip()}):
            conn.execute('INSERT INTO blend_tag (blend_id, tag) VALUES (?,?)', (bid, t))
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise
    return bid


def users(conn: sqlite3.Connection, bid: int) -> list[dict[str, Any]]:
    """The sauces that use a blend (none until the sauces exist — SP11 adds the table)."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sauce_ingredient'").fetchone():
        return []
    return [{'id': r['id'], 'name': r['name']} for r in conn.execute(
        'SELECT DISTINCT s.id, s.name FROM sauce s JOIN sauce_ingredient i ON i.sauce_id = s.id WHERE i.blend_id = ? '
        'ORDER BY s.name', (bid,))]


def delete(conn: sqlite3.Connection, bid: int) -> None:
    get_row(conn, bid)
    used = users(conn, bid)
    if used:
        raise InUse(used)
    for t in ('blend_part', 'blend_tag'):
        conn.execute(f'DELETE FROM {t} WHERE blend_id = ?', (bid,))
    conn.execute('DELETE FROM blend WHERE id = ?', (bid,))


def names(r: sqlite3.Row, data: SpiceData) -> dict[str, str]:
    """A seed shows the classic's name in each language while it still has its own (English) name; once the owner
    renames it, the typed name stands in both."""
    if r['origin'] == 'seed' and r['classic_id']:
        c = next((c for c in data.classics if c['id'] == r['classic_id']), None)
        if c is not None and r['name'] == c['en']:
            return {'en': c['en'], 'hu': c['hu']}
    return {'en': r['name'], 'hu': r['name']}


def riff(conn: sqlite3.Connection, data: SpiceData, bid: int, lang: str, now: datetime) -> int:
    """A copy to play with: "<name> (2)", (3)… in the UI's language."""
    r = get_row(conn, bid)
    base = names(r, data)[lang]
    taken = {fold(x['name']) for x in conn.execute('SELECT name FROM blend')}
    n = 2
    while fold(f'{base} ({n})') in taken:
        n += 1
    return save(conn, {'name': f'{base} ({n})', 'notes': r['notes'], 'tags': tags(conn, bid), 'lang': lang,
                       'parts': [{'spice': s, 'parts': p} for s, p in parts(conn, bid)]}, now,
                origin='riff', classic_id=r['classic_id'])


def seed(conn: sqlite3.Connection, data: SpiceData, now: datetime) -> int:
    """The 16 DIY classics, once in the life of the database."""
    if conn.execute('SELECT 1 FROM counter WHERE name = ?', (SEEDED,)).fetchone():
        return 0
    n = 0
    for c in data.classics:
        if c['source'] != 'diy':
            continue
        save(conn, {'name': c['en'], 'notes': c['method']['en'], 'lang': 'en', 'tags': [],
                    'parts': [{'spice': s, 'parts': p} for s, p in c['parts'].items()]}, now, origin='seed', classic_id=c['id'])
        n += 1
    conn.execute('INSERT INTO counter (name, value) VALUES (?, ?)', (SEEDED, n))
    return n


def method(r: sqlite3.Row, data: SpiceData) -> dict[str, str] | None:
    """A seed's method note in both languages while it is still the seed's own text."""
    if r['origin'] == 'seed' and r['classic_id']:
        c = next((c for c in data.classics if c['id'] == r['classic_id']), None)
        if c is not None and c.get('method') and (r['notes'] or '') == c['method']['en']:
            return dict(c['method'])
    return {'en': r['notes'], 'hu': r['notes']} if r['notes'] else None


def gluten_line(engine: SpiceEngine, cat: Catalogue, state: dict[str, Any], spice_ids: list[str]) -> dict[str, Any]:
    """The blend's GF state, from the gluten engine: single spices are GF; a `label` jar (asafoetida, chilli powder,
    mustard powder) reads `check` until it is the owner's own (in the pantry) — then `yours`."""
    per = {s: gluten.check_line(cat, state, s, False).status for s in spice_ids}
    status = max(per.values(), key=lambda s: CAUTION[s]) if per else 'ok'
    f = engine.f
    if status == 'ok':
        text = {'en': f['gluten-ok']['en'], 'hu': f['gluten-ok']['hu']}
    else:
        which = [s for s, st in per.items() if st == status]
        key = 'gluten-label' if status == 'check' else 'gluten-yours'
        text = engine._fmt(f[key], spices=engine._jars(which))
    return {'status': status, 'about': [s for s, st in per.items() if st != 'ok'], **text}


def view(conn: sqlite3.Connection, engine: SpiceEngine, cat: Catalogue, state: dict[str, Any], r: sqlite3.Row,
         full: bool, batch_tbsp: float | None = None) -> dict[str, Any]:
    ps = [(s, p) for s, p in parts(conn, r['id']) if s in engine.p]       # a jar that left the rack drops out
    missing = [s for s, _ in parts(conn, r['id']) if s not in engine.p]
    e = engine.evaluate(ps, batch_tbsp) if ps else None
    out: dict[str, Any] = {
        'id': r['id'], 'names': names(r, engine.data), 'origin': r['origin'], 'classic_id': r['classic_id'],
        'tags': tags(conn, r['id']), 'parts': [{'spice': s, 'parts': p} for s, p in ps],
        'score': e['score'] if e else None, 'word': e['word'] if e else None, 'jar_fill': e['jar_fill'] if e else '#CCBFA8',
        'heat': e['heat']['word'] if e else 'mild', 'gluten': gluten_line(engine, cat, state, [s for s, _ in ps]),
        'created_at': r['created_at'], 'updated_at': r['updated_at'], 'missing_jars': missing,
    }
    if full:
        out.update({'name': r['name'], 'lang': r['lang'], 'notes': r['notes'], 'method': method(r, engine.data),
                    'evaluation': e, 'used_by': users(conn, r['id'])})
    return out


def summaries(conn: sqlite3.Connection, engine: SpiceEngine, cat: Catalogue, state: dict[str, Any],
              q: str | None = None) -> list[dict[str, Any]]:
    fq = fold(q) if q else None
    out = []
    for r in conn.execute('SELECT * FROM blend ORDER BY updated_at DESC, id DESC'):
        v = view(conn, engine, cat, state, r, full=False)
        if fq and not any(fq in fold(x) for x in (*v['names'].values(), *v['tags'])):
            continue
        out.append(v)
    return out


def get(conn: sqlite3.Connection, engine: SpiceEngine, cat: Catalogue, state: dict[str, Any], bid: int,
        batch_tbsp: float | None = None) -> dict[str, Any]:
    return view(conn, engine, cat, state, get_row(conn, bid), full=True, batch_tbsp=batch_tbsp)


def rack(engine: SpiceEngine, cat: Catalogue, knowhow_lib: list[dict[str, Any]]) -> dict[str, Any]:
    """GET /api/spices: the rack picker's shelves and jars, the foods, and every label the screens show. A jar that is
    also on the know-how's rack carries that page's note and its route (a long press opens it)."""
    notes: dict[tuple[str, str], tuple[dict[str, str], str]] = {}
    for s in knowhow_lib:
        for p in s['pages'] if s['id'] == 'spices' else []:
            ch = p.get('chart') or {}
            for it in ch.get('items') or [] if ch.get('type') == 'swatches' else []:
                v = it.get('value')
                if isinstance(v, dict) and isinstance(it.get('note'), dict):
                    notes[(it['fill'].upper(), v['en'])] = (it['note'], f"{s['id']}/{p['id']}")
    data = engine.data
    meta = data.meta
    shelves = []
    for sh in meta['shelves']:
        jars = []
        for sid, p in data.profiles.items():
            if p['shelf'] != sh['id']:
                continue
            item = cat.items[sid]
            note, page = notes.get((p['fill'].upper(), p['tag']['en']), (None, None))
            jars.append({'id': sid, 'label': engine.names[sid], 'name': {'en': item.en, 'hu': item.hu}, 'fill': p['fill'],
                         'tag': p['tag'], 'heat': p['heat'], 'role': p['role'], 'timing': p['timing'], 'form': p['form'],
                         'fragile': p['fragile'], 'gluten': item.gluten, 'g_per_tsp': p['g_per_tsp'], 'note': note, 'page': page})
        shelves.append({'id': sh['id'], 'en': sh['en'], 'hu': sh['hu'], 'jars': jars})
    def icon(ref: str) -> str:
        return 'om-' + ref[3:].lower() if ref.startswith('om:') else 'c-' + ref[2:]
    return {
        'shelves': shelves,
        'foods': [{'id': f['id'], 'icon': icon(f['icon']), 'en': f['en'], 'hu': f['hu']} for f in data.foods.values()],
        'axes': meta['axes'], 'cuisines': meta['cuisines'], 'roles': meta['roles'], 'timings': meta['timings'],
        'words': meta['words'], 'heat': meta['heat'],
        'classics': [{'id': c['id'], 'en': c['en'], 'hu': c['hu'], 'source': c['source']} for c in data.classics],
        'max_spices': 16,
    }
