"""The owner's sauces (spec 2026-10-19 §4.4, §6.3, §7, §8): storage, the seeds, typed lines, the views and the GF lines.

The flavour, body and stability verdict comes from the sauce engine (a pure function of the lines and steps); the
gluten lines come from the gluten engine (catalogue + pantry), exactly like a recipe's — the two never mix. **Every line's
gluten state is `gluten.check_line`, and the sauce's is `gluten.verdict`** (a guard test fails if this file decides a
gluten state any other way): a blend line has no item of its own, so it reads the most cautious `check_line` over the
blend's jars — never an owner's "OK" — and its tip names the jar. Seeds: the twelve classics, inserted once (a `counter`
row `seeded:sauces` remembers it, so deleting every sauce never brings them back).

A stored line is one of: a sauce-shelf item (`shelf_id`, with its catalogue `item_id`), a rack jar (`spice_id`), one of
the owner's blends (`blend_id`), a typed line matched to a catalogue item off the shelves (`item_id` + `raw`), or a typed
line nothing matched (`raw` only — it counts for nothing and reads `unknown` until matched or marked OK).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from . import blends, gluten, timers
from .catalogue import Catalogue, fold
from .ingredients import parse_line
from .matcher import Matcher
from .recipes import guess_lang
from .sauce_data import SauceData
from .sauce_engine import BODY_CLASSES, MAX_LINES, UNIT_ML, SauceEngine, SauceInputError

SEEDED = 'seeded:sauces'
CAUTION = {'ok': 0, 'yours': 1, 'check': 2, 'unknown': 3, 'swap': 4}     # spec §7: a blend line reads its most cautious jar


class NotFound(KeyError):
    pass


class BadLine(ValueError):
    pass


def get_row(conn: sqlite3.Connection, sid: int) -> sqlite3.Row:
    r = conn.execute('SELECT * FROM sauce WHERE id = ?', (sid,)).fetchone()
    if r is None:
        raise NotFound(sid)
    return r


def rows(conn: sqlite3.Connection, sid: int) -> list[sqlite3.Row]:
    return conn.execute('SELECT * FROM sauce_ingredient WHERE sauce_id = ? ORDER BY pos', (sid,)).fetchall()


def steps(conn: sqlite3.Connection, sid: int) -> list[str]:
    return [s['text'] for s in conn.execute('SELECT text FROM sauce_step WHERE sauce_id = ? ORDER BY pos', (sid,))]


def tags(conn: sqlite3.Connection, sid: int) -> list[str]:
    return [t['tag'] for t in conn.execute('SELECT tag FROM sauce_tag WHERE sauce_id = ? ORDER BY tag', (sid,))]


# --- lines -------------------------------------------------------------------------------------------------------------
def check_lines(conn: sqlite3.Connection, data: SauceData, rack: set[str], cat: Catalogue,
                lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate the lines a client sends ({shelf|spice|blend|item|raw, qty?, unit?, ok_gf?}) and give each its stored
    form. Units and amounts are checked by the engine; this checks the references."""
    if not 1 <= len(lines) <= MAX_LINES:
        raise BadLine(f'a sauce has 1 to {MAX_LINES} lines')
    out = []
    for pos, ln in enumerate(lines):
        what = f'line {pos + 1}'
        refs = [k for k in ('shelf', 'spice', 'blend', 'item') if ln.get(k) is not None]
        if len(refs) > 1 or (not refs and ln.get('raw') is None):
            raise BadLine(f'{what}: one of shelf, spice, blend, item or raw')   # a typed line keeps its raw text beside it
        row: dict[str, Any] = {'shelf_id': None, 'item_id': None, 'spice_id': None, 'blend_id': None, 'raw': None,
                               'qty': ln.get('qty'), 'unit': ln.get('unit'), 'ok_gf': bool(ln.get('ok_gf')),
                               'match_how': ln.get('match_how')}
        if ln.get('shelf') is not None:
            e = data.ingredients.get(ln['shelf'])
            if e is None:
                raise BadLine(f'{what}: {ln["shelf"]} is not on the sauce shelves')
            row.update(shelf_id=ln['shelf'], item_id=e.get('item', ln['shelf']), name=ln['shelf'], raw=ln.get('raw'))
        elif ln.get('spice') is not None:
            if ln['spice'] not in rack:
                raise BadLine(f'{what}: {ln["spice"]} is not a rack jar')
            row.update(spice_id=ln['spice'], item_id=ln['spice'], name=ln['spice'])
        elif ln.get('blend') is not None:
            if not conn.execute('SELECT 1 FROM blend WHERE id = ?', (ln['blend'],)).fetchone():
                raise BadLine(f'{what}: no such blend')
            row.update(blend_id=ln['blend'], name=f'blend:{ln["blend"]}')
        elif ln.get('item') is not None:
            if ln['item'] not in cat.items:
                raise BadLine(f'{what}: {ln["item"]} is not a catalogue item')
            row.update(item_id=ln['item'], raw=str(ln.get('raw') or ''), name=str(ln.get('raw') or ln['item']))
        else:
            text = str(ln['raw']).strip()
            if not text:
                raise BadLine(f'{what}: a typed line is text')
            row.update(raw=text, name=text)
        out.append(row)
    return out


def engine_lines(conn: sqlite3.Connection, stored: list[dict[str, Any]] | list[sqlite3.Row],
                 lang: str = 'en', data: Any = None) -> list[dict[str, Any]]:
    """Stored lines as the sauce engine reads them (a blend line carries its parts and its name)."""
    out = []
    for r in stored:
        if r['shelf_id']:
            out.append({'id': r['shelf_id'], 'qty': r['qty'], 'unit': r['unit']})
        elif r['spice_id']:
            out.append({'spice': r['spice_id'], 'qty': r['qty'], 'unit': r['unit']})
        elif r['blend_id'] is not None:
            b = conn.execute('SELECT * FROM blend WHERE id = ?', (r['blend_id'],)).fetchone()
            out.append({'blend': r['blend_id'], 'qty': r['qty'], 'unit': r['unit'],
                        'name': blends.names(b, data)[lang] if b is not None and data is not None else (b['name'] if b else ''),
                        'parts': [list(p) for p in blends.parts(conn, r['blend_id'])]})
        elif r['item_id']:
            out.append({'item': r['item_id'], 'name': r['raw'] or ''})
        else:
            out.append({'raw': r['raw']})
    return out


def gluten_lines(conn: sqlite3.Connection, eng: SauceEngine, cat: Catalogue, state: dict[str, Any],
                 stored: list[dict[str, Any]] | list[sqlite3.Row], lang: str = 'en') -> dict[str, Any]:
    """Every line through the gluten engine, and the sauce's verdict (spec §7)."""
    lines = []
    for pos, r in enumerate(stored):
        if r['blend_id'] is not None:
            jars = [s for s, _ in blends.parts(conn, r['blend_id'])]
            per = {s: gluten.check_line(cat, state, s, False) for s in jars}
            worst = max(per.values(), key=lambda g: CAUTION[g.status])
            which = [s for s, g in per.items() if g.status == worst.status]
            line = {'pos': pos, 'status': worst.status, 'swap_id': None, 'tip_en': None, 'tip_hu': None, 'about': which}
            if CAUTION[worst.status] > CAUTION['yours']:
                b = conn.execute('SELECT * FROM blend WHERE id = ?', (r['blend_id'],)).fetchone()
                text = eng._fmt(eng.f['blend-gluten'], blend=blends.names(b, eng.spices.data) if b else {'en': '', 'hu': ''},
                                spices=eng._items(which))
                line.update(tip_en=text['en'], tip_hu=text['hu'])
        else:
            g = gluten.check_line(cat, state, r['item_id'], bool(r['ok_gf']), _field(r, 'note_gluten'))
            line = {'pos': pos, 'status': g.status, 'swap_id': g.swap_id, 'tip_en': g.tip_en, 'tip_hu': g.tip_hu, 'about': []}
        lines.append(line)
    return {'lines': lines, 'verdict': gluten.verdict(ln['status'] for ln in lines)}


def _field(r: dict[str, Any] | sqlite3.Row, key: str) -> Any:
    keys = r.keys() if isinstance(r, sqlite3.Row) else r
    return r[key] if key in keys else None


def typed(matcher: Matcher, data: SauceData, rack: dict[str, dict[str, Any]], text: str) -> dict[str, Any]:
    """A line typed into the editor ("something else…"): parsed and matched like a recipe line. A shelf item joins as
    that item in one of its units; a rack jar as a spice in teaspoons; any other catalogue item as an off-shelf line
    (it counts for gluten only); nothing matched stays the raw text."""
    text = (text or '').strip()
    parsed = parse_line(text)
    if not text or not parsed:
        raise BadLine('nothing to read in that line')
    p = parsed[0]
    m = matcher.match(p.name, p.unit, p.qty)
    if m.item_id is None:
        return {'raw': text}
    entry = data.ingredients.get(m.item_id)
    if entry is None:
        entry = next((e for e in data.ingredients.values() if e.get('item') == m.item_id), None)
    if entry is not None:
        qty, unit = _fit(entry, p.qty, p.unit)
        return {'shelf': entry['id'], 'qty': qty, 'unit': unit, 'raw': text, 'match_how': m.how}
    if m.item_id in rack:
        return {'spice': m.item_id, 'qty': _tsp(rack[m.item_id], p.qty, p.unit), 'unit': 'tsp', 'raw': text, 'match_how': m.how}
    return {'item': m.item_id, 'raw': text, 'match_how': m.how}


def _ml(entry: dict[str, Any], qty: float, unit: str) -> float | None:
    if unit in UNIT_ML:
        return qty * UNIT_ML[unit]
    if unit == 'pinch':
        return qty * 0.625
    if unit == 'g':
        return qty / entry['g_per_ml']
    if unit in ('pcs', 'clove', 'head') and entry.get('g_per_pc'):
        return qty * entry['g_per_pc'] / entry['g_per_ml']
    return None


def _fit(entry: dict[str, Any], qty: float | None, unit: str | None) -> tuple[float, str]:
    """A typed amount in one of the entry's own units (the natural one when it converts), else its default."""
    units = [entry['unit'], *(entry.get('alt') or [])]
    if qty is None:
        return entry['default'], entry['unit']
    if unit in units:
        return round(qty, 2), unit
    if unit in ('clove', 'head') and 'pcs' in units:
        return round(qty, 2), 'pcs'
    ml = _ml(entry, qty, unit) if unit else None
    if ml is None:
        return entry['default'], entry['unit']
    for u in units:
        if u in UNIT_ML:
            return round(ml / UNIT_ML[u], 2), u
        if u == 'g':
            return round(ml * entry['g_per_ml'], 1), u
        if u == 'pcs' and entry.get('g_per_pc'):
            return round(ml * entry['g_per_ml'] / entry['g_per_pc'], 2), u
    return entry['default'], entry['unit']


def _tsp(profile: dict[str, Any], qty: float | None, unit: str | None) -> float:
    if qty is None:
        return 1.0
    if unit == 'tbsp':
        return round(qty * 3, 2)
    if unit == 'g':
        return round(qty / profile['g_per_tsp'], 2)
    if unit == 'pinch':
        return round(qty * 0.125, 3)
    return round(qty, 2)


# --- storage -----------------------------------------------------------------------------------------------------------
def save(conn: sqlite3.Connection, data: dict[str, Any], stored: list[dict[str, Any]], now: datetime,
         sid: int | None = None, origin: str = 'typed', classic_id: str | None = None) -> int:
    """Create (sid None) or replace a sauce. `data`: name, notes?, tags?, yield_ml?, family? (the owner's override),
    steps, lang?; `stored`: the lines from check_lines."""
    ts = now.isoformat()
    name = data['name'].strip()
    lang = data.get('lang') or guess_lang(name, data.get('notes') or '', *(data.get('steps') or []))
    family = data.get('family') or None
    conn.execute('BEGIN')
    try:
        if sid is None:
            sid = conn.execute('INSERT INTO sauce (name, lang, family, family_user, yield_ml, notes, origin, classic_id, '
                               'created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                               (name, lang, family, int(family is not None), data.get('yield_ml'), data.get('notes'),
                                origin, classic_id, ts, ts)).lastrowid
        else:
            get_row(conn, sid)
            conn.execute('UPDATE sauce SET name=?, lang=?, family=?, family_user=?, yield_ml=?, notes=?, updated_at=? WHERE id=?',
                         (name, lang, family, int(family is not None), data.get('yield_ml'), data.get('notes'), ts, sid))
            for t in ('sauce_ingredient', 'sauce_step', 'sauce_tag'):
                conn.execute(f'DELETE FROM {t} WHERE sauce_id = ?', (sid,))
        for pos, r in enumerate(stored):
            conn.execute('INSERT INTO sauce_ingredient (sauce_id, pos, shelf_id, item_id, spice_id, blend_id, raw, qty, unit, '
                         'name, match_how, ok_gf) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                         (sid, pos, r['shelf_id'], r['item_id'], r['spice_id'], r['blend_id'], r['raw'], r['qty'], r['unit'],
                          r['name'], r.get('match_how'), int(r['ok_gf'])))
        for pos, text in enumerate(s for s in (data.get('steps') or []) if s.strip()):
            conn.execute('INSERT INTO sauce_step (sauce_id, pos, text) VALUES (?,?,?)', (sid, pos, text.strip()))
        for t in sorted({t.strip().lower() for t in data.get('tags') or [] if t.strip()}):
            conn.execute('INSERT INTO sauce_tag (sauce_id, tag) VALUES (?,?)', (sid, t))
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise
    return sid


def delete(conn: sqlite3.Connection, sid: int) -> None:
    get_row(conn, sid)
    for t in ('sauce_ingredient', 'sauce_step', 'sauce_tag'):
        conn.execute(f'DELETE FROM {t} WHERE sauce_id = ?', (sid,))
    conn.execute('DELETE FROM sauce WHERE id = ?', (sid,))


def _classic(data: SauceData, r: sqlite3.Row) -> dict[str, Any] | None:
    if r['origin'] in ('seed', 'riff') and r['classic_id']:
        return next((c for c in data.classics if c['id'] == r['classic_id']), None)
    return None


def names(r: sqlite3.Row, data: SauceData) -> dict[str, str]:
    """A seed shows the classic's name in each language while it still has its own (English) name."""
    c = _classic(data, r) if r['origin'] == 'seed' else None
    if c is not None and r['name'] == c['en']:
        return {'en': c['en'], 'hu': c['hu']}
    return {'en': r['name'], 'hu': r['name']}


def step_texts(conn: sqlite3.Connection, r: sqlite3.Row, data: SauceData) -> dict[str, list[str]]:
    """A seed's steps in both languages while they are still the seed's own; otherwise as written."""
    own = steps(conn, r['id'])
    c = _classic(data, r) if r['origin'] == 'seed' else None
    if c is not None and own == c['steps']['en']:
        return {'en': list(c['steps']['en']), 'hu': list(c['steps']['hu'])}
    return {'en': own, 'hu': own}


def method(r: sqlite3.Row, data: SauceData) -> dict[str, str] | None:
    c = _classic(data, r) if r['origin'] == 'seed' else None
    if c is not None and c.get('method') and (r['notes'] or '') == c['method']['en']:
        return dict(c['method'])
    return {'en': r['notes'], 'hu': r['notes']} if r['notes'] else None


def riff(conn: sqlite3.Connection, data: SauceData, sid: int, lang: str, now: datetime) -> int:
    """A copy to play with: "<name> (2)", (3)… in the UI's language; the steps in that language too."""
    r = get_row(conn, sid)
    base = names(r, data)[lang]
    taken = {fold(x['name']) for x in conn.execute('SELECT name FROM sauce')}
    n = 2
    while fold(f'{base} ({n})') in taken:
        n += 1
    stored = [dict(x) for x in rows(conn, sid)]
    return save(conn, {'name': f'{base} ({n})', 'notes': r['notes'], 'tags': tags(conn, sid), 'lang': lang,
                       'yield_ml': r['yield_ml'], 'family': r['family'] if r['family_user'] else None,
                       'steps': step_texts(conn, r, data)[lang]}, stored, now, origin='riff', classic_id=r['classic_id'])


def classic_lines(data: SauceData, c: dict[str, Any]) -> list[dict[str, Any]]:
    """A classic's ingredients as stored lines."""
    stored = []
    for ln in c['ingredients']:
        if 'id' in ln:
            e = data.ingredients[ln['id']]
            stored.append({'shelf_id': ln['id'], 'item_id': e.get('item', ln['id']), 'spice_id': None, 'blend_id': None,
                           'raw': None, 'qty': ln['qty'], 'unit': ln['unit'], 'name': ln['id'], 'ok_gf': False})
        else:
            stored.append({'shelf_id': None, 'item_id': ln['spice'], 'spice_id': ln['spice'], 'blend_id': None,
                           'raw': None, 'qty': ln['qty'], 'unit': ln['unit'], 'name': ln['spice'], 'ok_gf': False})
    return stored


def seed(conn: sqlite3.Connection, data: SauceData, now: datetime) -> int:
    """The twelve classics, once in the life of the database."""
    if conn.execute('SELECT 1 FROM counter WHERE name = ?', (SEEDED,)).fetchone():
        return 0
    n = 0
    for c in data.classics:
        stored = classic_lines(data, c)
        save(conn, {'name': c['en'], 'notes': (c.get('method') or {}).get('en'), 'lang': 'en', 'tags': [],
                    'yield_ml': c['yield_ml'], 'steps': c['steps']['en']}, stored, now, origin='seed', classic_id=c['id'])
        n += 1
    conn.execute('INSERT INTO counter (name, value) VALUES (?, ?)', (SEEDED, n))
    return n


# --- views -------------------------------------------------------------------------------------------------------------
def _line_view(r: sqlite3.Row, g: dict[str, Any]) -> dict[str, Any]:
    kind = ('shelf' if r['shelf_id'] else 'spice' if r['spice_id'] else 'blend' if r['blend_id'] is not None
            else 'off-shelf' if r['item_id'] else 'raw')
    return {'pos': r['pos'], 'kind': kind, 'shelf_id': r['shelf_id'], 'spice_id': r['spice_id'], 'blend_id': r['blend_id'],
            'item_id': r['item_id'], 'raw': r['raw'], 'qty': r['qty'], 'unit': r['unit'], 'ok_gf': bool(r['ok_gf']),
            'match_how': r['match_how'],
            'gluten': {k: g[k] for k in ('status', 'swap_id', 'tip_en', 'tip_hu', 'about')}}


def view(conn: sqlite3.Connection, eng: SauceEngine, cat: Catalogue, state: dict[str, Any], r: sqlite3.Row,
         full: bool, lang: str = 'en') -> dict[str, Any]:
    stored = rows(conn, r['id'])
    st = step_texts(conn, r, eng.data)
    try:
        e = eng.evaluate(engine_lines(conn, stored, lang, eng.spices.data), st['en'],
                         r['family'] if r['family_user'] else None)
    except SauceInputError:
        e = None                                      # nothing on it weighs anything (only typed lines): no verdict
    g = gluten_lines(conn, eng, cat, state, stored, lang)
    out: dict[str, Any] = {
        'id': r['id'], 'names': names(r, eng.data), 'origin': r['origin'], 'classic_id': r['classic_id'], 'tags': tags(conn, r['id']),
        'family': e['family'] if e else None, 'family_user': bool(r['family_user']), 'vessel': e['vessel'] if e else 'jug',
        'fill': e['fill'] if e else '#E8DCC4', 'score': e['score'] if e else None, 'word': e['word'] if e else None,
        'keeps': {k: e['keeps'][k] for k in ('class', 'days')} if e else None, 'heat': e['heat']['word'] if e else 'mild',
        'gluten': g['verdict'], 'yield_ml': r['yield_ml'], 'created_at': r['created_at'], 'updated_at': r['updated_at'],
    }
    if full:
        out.update({'name': r['name'], 'lang': r['lang'], 'notes': r['notes'], 'method': method(r, eng.data),
                    'lines': [_line_view(x, gl) for x, gl in zip(stored, g['lines'])], 'steps': st,
                    'timers': {lg: [[{'seconds': t.seconds, 'start': t.start, 'end': t.end} for t in timers.detect(s)]
                                    for s in st[lg]] for lg in ('en', 'hu')},
                    'evaluation': e})
    return out


def summaries(conn: sqlite3.Connection, eng: SauceEngine, cat: Catalogue, state: dict[str, Any],
              q: str | None = None, lang: str = 'en') -> list[dict[str, Any]]:
    fq = fold(q) if q else None
    out = []
    for r in conn.execute('SELECT * FROM sauce ORDER BY updated_at DESC, id DESC'):
        v = view(conn, eng, cat, state, r, full=False, lang=lang)
        if fq and not any(fq in fold(x) for x in (*v['names'].values(), *v['tags'])):
            continue
        out.append(v)
    return out


def get(conn: sqlite3.Connection, eng: SauceEngine, cat: Catalogue, state: dict[str, Any], sid: int,
        lang: str = 'en') -> dict[str, Any]:
    return view(conn, eng, cat, state, get_row(conn, sid), full=True, lang=lang)


def shelves(eng: SauceEngine, cat: Catalogue) -> dict[str, Any]:
    """GET /api/sauces/shelves: the editor's shelves and their items, and every label the sauce screens show. Static (the
    owner's blends and the rack jars come from /api/blends and /api/spices, which the web already has)."""
    data, meta = eng.data, eng.data.meta

    def display(iid: str) -> dict[str, str]:
        e = data.ingredients[iid]
        if e.get('say'):
            return {k: v[:1].upper() + v[1:] for k, v in e['say'].items()}
        it = cat.items[e.get('item', iid)]
        return {'en': it.en, 'hu': it.hu}
    out_shelves = []
    for sh in meta['shelves']:
        items = []
        for iid, e in data.ingredients.items():
            if e['shelf'] != sh['id'] or e.get('offer') is False:
                continue
            item = cat.items[e.get('item', iid)]
            items.append({'id': iid, 'name': display(iid), 'role': e['role'], 'driver': e['driver'], 'unit': e['unit'],
                          'default': e['default'], 'step': e['step'], 'alt': e.get('alt') or [], 'g_per_ml': e['g_per_ml'],
                          'g_per_pc': e.get('g_per_pc'), 'fill': e['fill'], 'gluten': item.gluten,
                          'body': e['body']['method'], 'keeps': e['keeps']})
        out_shelves.append({'id': sh['id'], 'en': sh['en'], 'hu': sh['hu'], 'items': items})

    def icon(ref: str) -> str:
        return 'om-' + ref[3:].lower() if ref.startswith('om:') else 'c-' + ref[2:]
    return {
        'shelves': out_shelves,
        'families': [{k: f.get(k) for k in ('id', 'en', 'hu', 'parent', 'vessel', 'chip', 'body', 'note')} | {'kind': f.get('kind', 'savoury')}
                     for f in data.families],
        'foods': [{'id': f['id'], 'icon': icon(f['icon']), 'en': f['en'], 'hu': f['hu']} for f in data.foods.values()],
        **{k: meta[k] for k in ('roles', 'taste', 'units', 'keeps', 'chips', 'stability', 'levels', 'words', 'heat')},
        # the body gauge's bands: the engine's own limits (the last one open-ended, sent as 99 like the heat's)
        'body': [b | {'below': min(dict((c, lim) for lim, c in BODY_CLASSES)[b['id']], 99)} for b in meta['body']],
        'max_lines': MAX_LINES,
    }
