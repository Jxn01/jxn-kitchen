"""Recipes: storage, the per-line view (parse → match → gluten → pantry), summaries, "what can I cook".

Ingredient lines are stored parsed AND raw; matching is redone on every save, except where the user corrected a
line by hand (kept by raw text). The view is computed on read so pantry changes show at once.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime
from typing import Any

from . import gluten, pantry, timers
from .catalogue import Catalogue, fold
from .ingredients import Parsed, format_qty, parse_line, scale
from .matcher import Matcher

log = logging.getLogger('kitchen.recipes')

_HU_CHARS = re.compile(r'[őűáéíóöúüŐŰÁÉÍÓÖÚÜ]')
_VERDICT_RANK = {'gf': 0, 'check': 1, 'swaps': 2, 'unknown': 3, 'empty': 4}


class NotFound(KeyError):
    pass


def guess_lang(*texts: str) -> str:
    return 'hu' if any(_HU_CHARS.search(t or '') for t in texts) else 'en'


def get_row(conn: sqlite3.Connection, rid: int) -> sqlite3.Row:
    r = conn.execute('SELECT * FROM recipe WHERE id = ?', (rid,)).fetchone()
    if r is None:
        raise NotFound(rid)
    return r


def save(conn: sqlite3.Connection, matcher: Matcher, data: dict[str, Any], now: datetime,
         rid: int | None = None) -> int:
    """Create (rid None) or replace a recipe. Hand corrections survive for lines whose raw text is unchanged."""
    ts = now.isoformat()
    lang = data.get('lang') or guess_lang(data['title'], *data.get('ingredients', []))
    fields = (data['title'].strip(), lang, data.get('source_url'), data.get('source_site'), data.get('servings', 4),
              data.get('prep_min'), data.get('cook_min'), data.get('total_min'), data.get('notes'),
              data.get('origin', 'typed'))
    conn.execute('BEGIN')
    try:
        keep: dict[str, tuple[str | None, int, int]] = {}
        if rid is None:
            cur = conn.execute('INSERT INTO recipe (title, lang, source_url, source_site, servings, prep_min, cook_min, '
                               'total_min, notes, origin, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                               (*fields, ts, ts))
            rid = cur.lastrowid
        else:
            get_row(conn, rid)
            for r in conn.execute('SELECT raw, name, item_id, ok_gf, user_item FROM recipe_ingredient '
                                  'WHERE recipe_id = ?', (rid,)):
                if r['user_item'] or r['ok_gf']:
                    keep[(r['raw'], r['name'])] = (r['item_id'], r['ok_gf'], r['user_item'])
            conn.execute('UPDATE recipe SET title=?, lang=?, source_url=?, source_site=?, servings=?, prep_min=?, '
                         'cook_min=?, total_min=?, notes=?, origin=?, updated_at=? WHERE id=?', (*fields, ts, rid))
            for t in ('recipe_ingredient', 'recipe_step', 'recipe_tag'):
                conn.execute(f'DELETE FROM {t} WHERE recipe_id = ?', (rid,))
        pos = 0
        for raw in data.get('ingredients', []):
            for p in parse_line(raw):
                m = matcher.match(p.name, unit=p.unit, qty=p.qty)
                item_id, how, ok_gf, user = m.item_id, m.how, 0, 0
                if (p.raw, p.name) in keep:
                    item_id, ok_gf, user = keep[(p.raw, p.name)]
                    how = 'user' if user else how
                conn.execute('INSERT INTO recipe_ingredient (recipe_id, pos, raw, qty, qty_max, unit, name, note, item_id, '
                             'match_how, ok_gf, user_item, note_gluten) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                             (rid, pos, p.raw, p.qty, p.qty_max, p.unit, p.name, p.note, item_id, how, ok_gf, user,
                              matcher.gluten_in(p.note)))
                pos += 1
        for i, text in enumerate(s for s in data.get('steps', []) if s and s.strip()):
            conn.execute('INSERT INTO recipe_step (recipe_id, pos, text) VALUES (?,?,?)', (rid, i, text.strip()))
        for tag in sorted({t.strip().lower() for t in data.get('tags', []) if t and t.strip()}):
            conn.execute('INSERT INTO recipe_tag (recipe_id, tag) VALUES (?,?)', (rid, tag))
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise
    return rid


_CAUTION = {'contains': 3, None: 2, 'label': 1, 'free': 0}     # None = unmatched: never GF, but no swap either


def rematch_all(conn: sqlite3.Connection, matcher: Matcher) -> int:
    """Re-run parsing and matching on every line the user did not correct by hand, against the parser and catalogue
    as they are NOW (run at start-up), so fixes reach recipes saved earlier. That is a safety matter, not a nicety —
    when a wheat word is re-pointed from a GF tile to its wheat item, an old recipe must lose its ✓ GF too.

    It may only make a line MORE cautious on its own. A line that was `contains` or `label` is never moved to a less
    cautious item behind the user's back: such a line is left exactly as stored and
    logged — the user can still fix it by hand. A line's note is re-scanned for mentioned gluten (`note_gluten`),
    which can only add caution. Only a raw line that still parses to ONE ingredient with the same quantity and unit
    gets a new name/note. Returns how many lines changed."""
    changed, held = 0, 0
    cat = matcher.cat
    rows = conn.execute('SELECT recipe_id, pos, raw, name, note, unit, qty, item_id, match_how, note_gluten '
                        'FROM recipe_ingredient WHERE user_item = 0').fetchall()
    conn.execute('BEGIN')
    try:
        for r in rows:
            name, note = r['name'], r['note']
            again = parse_line(r['raw'])
            if len(again) == 1 and again[0].unit == r['unit'] and again[0].qty == r['qty']:
                name, note = again[0].name, again[0].note
            m = matcher.match(name, unit=r['unit'], qty=r['qty'])
            old = cat.items.get(r['item_id'] or '')
            new = cat.items.get(m.item_id or '')
            old_c = _CAUTION[old.gluten if old else None]
            new_c = _CAUTION[new.gluten if new else None]
            if old is not None and old.gluten in ('contains', 'label') and new_c < old_c:
                held += 1
                log.warning('rematch: kept %r as %r (would have become %r) — a downgrade needs a manual match',
                            r['raw'], r['item_id'], m.item_id)
                name, note, m = r['name'], r['note'], None
            if m is not None and ((name, note) != (r['name'], r['note']) or (m.item_id, m.how) != (r['item_id'], r['match_how'])):
                conn.execute('UPDATE recipe_ingredient SET name = ?, note = ?, item_id = ?, match_how = ? '
                             'WHERE recipe_id = ? AND pos = ?', (name, note, m.item_id, m.how, r['recipe_id'], r['pos']))
                changed += 1
            ng = matcher.gluten_in(note)
            if ng != r['note_gluten'] and (ng is not None or m is not None):
                conn.execute('UPDATE recipe_ingredient SET note_gluten = ? WHERE recipe_id = ? AND pos = ?',
                             (ng, r['recipe_id'], r['pos']))
                changed += 1
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise
    if held:
        log.warning('rematch: %d line(s) kept as they were rather than made less cautious', held)
    return changed


def set_image(conn: sqlite3.Connection, rid: int, name: str | None) -> None:
    get_row(conn, rid)
    conn.execute('UPDATE recipe SET image = ? WHERE id = ?', (name, rid))


def set_line(conn: sqlite3.Connection, cat: Catalogue, rid: int, pos: int, item_id: str | None, ok_gf: bool) -> None:
    get_row(conn, rid)
    if item_id is not None and item_id not in cat.items:
        raise NotFound(item_id)
    cur = conn.execute('UPDATE recipe_ingredient SET item_id = COALESCE(?, item_id), match_how = CASE WHEN ? IS NULL '
                       'THEN match_how ELSE \'user\' END, user_item = CASE WHEN ? IS NULL THEN user_item ELSE 1 END, '
                       'ok_gf = ? WHERE recipe_id = ? AND pos = ?', (item_id, item_id, item_id, int(ok_gf), rid, pos))
    if cur.rowcount == 0:
        raise NotFound(pos)


def delete(conn: sqlite3.Connection, rid: int) -> str | None:
    r = get_row(conn, rid)
    for t in ('recipe_ingredient', 'recipe_step', 'recipe_tag'):
        conn.execute(f'DELETE FROM {t} WHERE recipe_id = ?', (rid,))
    conn.execute('DELETE FROM recipe WHERE id = ?', (rid,))
    return r['image']


def _counts(cat: Catalogue, state: dict[str, Any], item_ids: list[str | None]) -> tuple[int, int, list[str]]:
    """have / total / missing over the distinct FOOD items (tile-less staples like water don't count)."""
    seen: list[str] = []
    for iid in item_ids:
        item = cat.items.get(iid or '')
        if item is None or item.kind != 'food' or (item.staple and not item.pantry) or iid in seen:
            continue
        seen.append(iid)
    missing = [i for i in seen if not pantry.has(cat, state, i)]
    return len(seen) - len(missing), len(seen), missing


def _line_view(cat: Catalogue, state: dict[str, Any], r: sqlite3.Row, factor: float, lang: str,
               rlang: str) -> dict[str, Any]:
    """One ingredient line. The line itself (quantity, item and GF-swap names) reads in the RECIPE's language, like
    its steps; the tip is in the UI language `lang`."""
    p = scale(Parsed(r['raw'], r['qty'], r['qty_max'], r['unit'], r['name'], r['note']), factor)
    qty_text = format_qty(p.qty, p.unit, rlang, p.qty_max)
    g = gluten.check_line(cat, state, r['item_id'], bool(r['ok_gf']), r['note_gluten'])
    item = cat.items.get(r['item_id'] or '')
    gf = gluten.gf_name(cat, r['item_id'], rlang)
    return {
        'pos': r['pos'], 'raw': r['raw'], 'qty_text': qty_text, 'name': r['name'], 'note': r['note'],
        'item_id': r['item_id'], 'item_name': (item.hu if rlang == 'hu' else item.en) if item else None,
        'how': r['match_how'], 'gluten': g.status, 'ok_gf': bool(r['ok_gf']),
        'gf_text': f'{qty_text} {gf}'.strip() if gf else None,
        'tip': (g.tip_hu if lang == 'hu' else g.tip_en),
        'have': pantry.has(cat, state, r['item_id']) if item and item.kind == 'food' else None,
        'pantry_id': _pantry_tile(cat, item),
    }


def _pantry_tile(cat: Catalogue, item: Any) -> str | None:
    """The pantry tile a line stands for: a wheat item's GF version, the item itself if it is a tile, else None."""
    if item is None:
        return None
    if item.gluten == 'contains' and item.swap:
        item = cat.items[item.swap]
    return item.id if item.pantry else None


def get(conn: sqlite3.Connection, cat: Catalogue, state: dict[str, Any], rid: int, lang: str,
        servings: int | None = None) -> dict[str, Any]:
    r = get_row(conn, rid)
    base = r['servings'] or 1
    want = servings or base
    lines = [_line_view(cat, state, x, want / base, lang, r['lang'] or lang) for x in
             conn.execute('SELECT * FROM recipe_ingredient WHERE recipe_id = ? ORDER BY pos', (rid,))]
    have, total, missing = _counts(cat, state, [l['item_id'] for l in lines])
    steps = [{'pos': s['pos'], 'text': s['text'],
              'timers': [{'start': t.start, 'end': t.end, 'seconds': t.seconds} for t in timers.detect(s['text'])]}
             for s in conn.execute('SELECT * FROM recipe_step WHERE recipe_id = ? ORDER BY pos', (rid,))]
    def name(i: str) -> str:
        it = cat.items[i]
        if it.gluten == 'contains' and it.swap:
            it = cat.items[it.swap]
        return it.hu if lang == 'hu' else it.en
    return {
        'id': rid, 'title': r['title'], 'lang': r['lang'], 'source_url': r['source_url'], 'source_site': r['source_site'],
        'image': f"/api/images/{r['image']}" if r['image'] else None, 'servings': want, 'base_servings': base,
        'prep_min': r['prep_min'], 'cook_min': r['cook_min'], 'total_min': r['total_min'], 'notes': r['notes'],
        'origin': r['origin'], 'tags': tags(conn, rid), 'created_at': r['created_at'], 'folder_id': r['folder_id'],
        'verdict': gluten.verdict(l['gluten'] for l in lines), 'have': have, 'total': total,
        'missing': [{'item_id': i, 'name': name(i)} for i in missing], 'lines': lines, 'steps': steps,
    }


def tags(conn: sqlite3.Connection, rid: int) -> list[str]:
    return [t['tag'] for t in conn.execute('SELECT tag FROM recipe_tag WHERE recipe_id = ? ORDER BY tag', (rid,))]


def summaries(conn: sqlite3.Connection, cat: Catalogue, state: dict[str, Any], lang: str,
              q: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
    out = []
    lines_by: dict[int, list[sqlite3.Row]] = {}
    for x in conn.execute('SELECT recipe_id, item_id, ok_gf, note_gluten FROM recipe_ingredient ORDER BY recipe_id, pos'):
        lines_by.setdefault(x['recipe_id'], []).append(x)
    fq = fold(q) if q else None
    for r in conn.execute('SELECT * FROM recipe ORDER BY updated_at DESC'):
        t = tags(conn, r['id'])
        if tag and tag.lower() not in t:
            continue
        if fq and fq not in fold(r['title']) and not any(fq in fold(x) for x in t):
            continue
        ls = lines_by.get(r['id'], [])
        have, total, missing = _counts(cat, state, [x['item_id'] for x in ls])
        def nm(i: str) -> str:
            it = cat.items[i]
            if it.gluten == 'contains' and it.swap:
                it = cat.items[it.swap]
            return it.hu if lang == 'hu' else it.en
        statuses = [gluten.check_line(cat, state, x['item_id'], bool(x['ok_gf']), x['note_gluten']).status for x in ls]
        minutes = r['total_min'] or ((r['prep_min'] or 0) + (r['cook_min'] or 0)) or None
        out.append({'id': r['id'], 'title': r['title'], 'image': f"/api/images/{r['image']}" if r['image'] else None,
                    'minutes': minutes, 'servings': r['servings'], 'tags': t, 'source_site': r['source_site'],
                    'verdict': gluten.verdict(statuses), 'have': have, 'total': total, 'missing': len(missing),
                    'missing_names': [nm(i) for i in missing[:4]],
                    'origin': r['origin'], 'created_at': r['created_at'], 'folder_id': r['folder_id']})
    return out


def cookable(conn: sqlite3.Connection, cat: Catalogue, state: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    """Fewest missing first, then the larger share in stock, then GF-ready before check before swaps."""
    rows = [s for s in summaries(conn, cat, state, lang) if s['total']]
    return sorted(rows, key=lambda s: (s['missing'], -s['have'] / s['total'], _VERDICT_RANK[s['verdict']['state']]))


def missing_items(conn: sqlite3.Connection, cat: Catalogue, state: dict[str, Any], rid: int) -> list[str]:
    get_row(conn, rid)
    ids = [x['item_id'] for x in conn.execute('SELECT item_id FROM recipe_ingredient WHERE recipe_id = ? ORDER BY pos',
                                              (rid,))]
    return _counts(cat, state, ids)[2]
