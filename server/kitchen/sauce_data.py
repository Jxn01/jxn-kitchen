"""The sauce engine's knowledge: engine/sauces/*.yaml, every cell hand-judged.

Loaded and validated at start — like the spice knowledge, the server refuses to start on one bad cell. `load()` never
raises on bad content: it records what it could not read in `errors`, and `validate()` adds every rule breach.

Files: meta.yaml (labels), ingredients.yaml (one entry per shelf item: role, driver, unit, physics), reasons.yaml (reason
code -> bilingual sentence), pairs/<shelfA>--<shelfB>.yaml (every pair of DRIVERS once, row form like the spices'),
driver_foods/<shelf>.yaml (`<driver>: {<food>: [score, reason]}` for every food), families.yaml (the mother-sauce tree
and how a sauce is recognised), findings.yaml (the engine's sentences), classics.yaml (the twelve seeds). The foods are
the spice engine's (engine/spices/foods.yaml) — one list.
"""
from __future__ import annotations

import itertools
import pathlib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import yaml

from .spice_data import Cell, _bilingual, _cell, _sign_ok, _yaml

SHELVES = ('fats', 'acids', 'dairy-eggs', 'alliums', 'herbs', 'umami', 'sweet', 'heat', 'thickeners', 'liquids', 'veg')
ROLES = ('fat', 'acid', 'dairy', 'egg', 'allium', 'herb', 'umami', 'sweet', 'heat', 'thickener', 'liquid', 'veg')
TASTE = ('salt', 'acid', 'fat', 'sweet', 'heat', 'umami', 'aromatic')
UNITS = ('tbsp', 'tsp', 'ml', 'dl', 'g', 'pcs')
BODY_METHODS = ('none', 'slurry', 'roux', 'reduce', 'emulsify', 'puree', 'mount', 'liaison', 'base')
STARCHES = ('none', 'potato', 'corn', 'tapioca', 'arrowroot', 'rice', 'wheat', 'xanthan', 'mix')
KEEPS = ('raw-egg', 'fresh-dairy', 'fresh', 'oil-infusion', 'cooked', 'acid-preserved', 'dry-stable')
VESSELS = ('jug', 'sauceboat', 'bowl', 'bottle', 'jar')
CHIPS = ('hungarian', 'roux-dairy', 'emulsions', 'dressings', 'dips-cold', 'marinades', 'asian', 'sweet')
STEP_CLASSES = ('heat', 'boil', 'simmer-long', 'reduce', 'blend', 'mount', 'marinate', 'chill')
# the rack jars that are sauce ingredients in their own right: drivers, with a spice profile too
DUALS = ('sweet-paprika', 'smoked-paprika', 'hot-paprika', 'chili-flakes', 'cayenne', 'black-pepper', 'white-pepper',
         'mustard-powder', 'salt', 'sugar', 'brown-sugar', 'garlic-powder', 'onion-powder')
PAIRS_AS = {'greek-yogurt': 'yogurt', 'dijon': 'mustard', 'red-onion': 'onion'}     # three only
NO_FOODS = ('salt',)         # salt seasons everything and decides nothing about what a sauce suits: a driver with no food row
ING_KEYS = {'id', 'item', 'say', 'role', 'driver', 'shelf', 'unit', 'default', 'step', 'alt', 'g_per_ml', 'g_per_pc',
            'per100', 'body', 'stability', 'keeps', 'fill', 'pairs_as', 'offer'}
FAMILY_KEYS = {'id', 'en', 'hu', 'parent', 'vessel', 'chip', 'body', 'kind', 'detect', 'note'}
KINDS = ('savoury', 'rich', 'sweet', 'condiment')
CLASSIC_KEYS = {'id', 'en', 'hu', 'family', 'yield_ml', 'ingredients', 'steps', 'method', 'expected'}
FINDING_KEYS = ('family', 'family-other', 'flat', 'too-sharp', 'too-salty', 'under-salted', 'too-sweet', 'greasy',
                'emulsion-ok', 'emulsion-at-limit', 'emulsion-split', 'vinaigrette', 'yolk-heat', 'curdle-warn', 'curdle-notice',
                'starch-long-boil', 'starch-arrowroot-dairy', 'starch-corn-acid', 'starch-raw', 'raw-egg',
                'garlic-in-oil', 'body-reduce', 'too-thin-for', 'too-thick-for', 'body-right', 'seasoned', 'unknown-line', 'off-shelf', 'pairs-rest-good', 'pairs-rest-bad', 'and',
                'blend-gluten', 'keeps')
FIXES = ('too-thin', 'too-thick', 'lumpy', 'curdled', 'split', 'too-salty', 'too-sour', 'greasy', 'raw-flour')
_HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')
_PRED = re.compile(r'^(item|role|body|step|spice):[a-z0-9-]+$|^share:[a-z]+>=(0(\.\d+)?|1(\.0+)?)$|^emulsion$|^spices$|^blend$')


@dataclass
class SauceData:
    meta: dict[str, Any]
    ingredients: dict[str, dict[str, Any]]       # id -> entry, in file order (= shelf order on screen)
    reasons: dict[str, dict[str, Any]]
    foods: dict[str, dict[str, Any]]             # the spice engine's foods
    pairs: dict[tuple[str, str], Cell]
    driver_foods: dict[tuple[str, str], Cell]
    families: list[dict[str, Any]]
    classics: list[dict[str, Any]]
    findings: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def drivers(self) -> list[str]:
        return [i for i, e in self.ingredients.items() if e.get('driver') is True and not e.get('pairs_as')]

    def pair_id(self, iid: str) -> str:
        """The driver a line pairs as: itself, or its `pairs_as` target."""
        return (self.ingredients.get(iid) or {}).get('pairs_as') or iid

    def pair(self, a: str, b: str) -> Cell:
        a, b = self.pair_id(a), self.pair_id(b)
        return self.pairs[(a, b) if a < b else (b, a)]

    def family(self, fid: str) -> dict[str, Any] | None:
        return next((f for f in self.families if f.get('id') == fid), None)


def load(directory: pathlib.Path | str, foods_file: pathlib.Path | str | None = None) -> SauceData:
    d = pathlib.Path(directory)
    errors: list[str] = []
    meta = _yaml(d / 'meta.yaml', errors) or {}
    ingredients: dict[str, dict[str, Any]] = {}
    for e in (_yaml(d / 'ingredients.yaml', errors) or {}).get('ingredients') or []:
        iid = e.get('id') if isinstance(e, dict) else None
        if not isinstance(iid, str):
            errors.append(f'ingredients.yaml: an entry without an id: {e!r}')
            continue
        if iid in ingredients:
            errors.append(f'ingredients.yaml: duplicate entry {iid}')
        ingredients.setdefault(iid, e)
    reasons = _yaml(d / 'reasons.yaml', errors) or {}
    foods: dict[str, dict[str, Any]] = {}
    ff = pathlib.Path(foods_file) if foods_file else d.parent / 'spices' / 'foods.yaml'
    for f in (_yaml(ff, errors) or {}).get('foods') or []:
        if isinstance(f, dict) and isinstance(f.get('id'), str):
            foods[f['id']] = f

    shelf_of = {i: e.get('shelf') for i, e in ingredients.items()}
    pairs: dict[tuple[str, str], Cell] = {}
    pair_dir = d / 'pairs'
    for path in sorted(pair_dir.glob('*.yaml')) if pair_dir.is_dir() else []:
        m = re.fullmatch(r'([a-z-]+?)--([a-z-]+)', path.stem)
        if not m or m.group(1) not in SHELVES or m.group(2) not in SHELVES:
            errors.append(f'pairs/{path.name}: name it <shelf>--<shelf>.yaml after two sauce shelves')
            continue
        sa, sb = m.group(1), m.group(2)
        if SHELVES.index(sa) > SHELVES.index(sb):
            errors.append(f'pairs/{path.name}: name the earlier shelf first ({sb}--{sa}.yaml)')
        rows = _yaml(path, errors) or {}
        if not isinstance(rows, dict):
            errors.append(f'pairs/{path.name}: must be a mapping of rows')
            continue
        for a, row in rows.items():
            if not isinstance(row, dict):
                errors.append(f'pairs/{path.name}: row {a} must be a mapping')
                continue
            for b, raw in row.items():
                where = f'pairs/{path.name}: {a} + {b}'
                unknown = [x for x in (a, b) if x not in ingredients]
                for x in unknown:
                    errors.append(f'{where}: {x} is not a sauce ingredient')
                if unknown:
                    continue
                got = sorted([shelf_of[a], shelf_of[b]], key=lambda s: SHELVES.index(s) if s in SHELVES else 99)
                if got != [sa, sb]:
                    errors.append(f'{where}: {a} ({shelf_of[a]}) + {b} ({shelf_of[b]}) belongs in {got[0]}--{got[1]}.yaml')
                if a == b:
                    errors.append(f'{where}: an ingredient is not paired with itself')
                    continue
                cell = _cell(raw, where, errors)
                if cell is None:
                    continue
                key = (a, b) if a < b else (b, a)
                if key in pairs:
                    errors.append(f'{where}: this pair is already stated in {pairs[key].where.split(":")[0]}')
                    continue
                pairs[key] = cell

    driver_foods: dict[tuple[str, str], Cell] = {}
    df_dir = d / 'driver_foods'
    for path in sorted(df_dir.glob('*.yaml')) if df_dir.is_dir() else []:
        if path.stem not in SHELVES:
            errors.append(f'driver_foods/{path.name}: name it after a sauce shelf')
            continue
        rows = _yaml(path, errors) or {}
        for s, row in (rows.items() if isinstance(rows, dict) else []):
            if s not in ingredients:
                errors.append(f'driver_foods/{path.name}: {s} is not a sauce ingredient')
                continue
            if shelf_of[s] != path.stem:
                errors.append(f'driver_foods/{path.name}: {s} is on the {shelf_of[s]} shelf — move its row')
            for f, raw in (row.items() if isinstance(row, dict) else []):
                where = f'driver_foods/{path.name}: {s} × {f}'
                if f not in foods:
                    errors.append(f'{where}: {f} is not a food')
                    continue
                cell = _cell(raw, where, errors)
                if cell is None:
                    continue
                if (s, f) in driver_foods:
                    errors.append(f'{where}: stated twice')
                    continue
                driver_foods[(s, f)] = cell

    families = (_yaml(d / 'families.yaml', errors) or {}).get('families') or []
    classics = (_yaml(d / 'classics.yaml', errors) or {}).get('classics') or []
    findings = _yaml(d / 'findings.yaml', errors) or {}
    return SauceData(meta=meta, ingredients=ingredients, reasons=reasons, foods=foods, pairs=pairs,
                     driver_foods=driver_foods, families=families, classics=classics, findings=findings, errors=errors)


def _num(v: Any, lo: float, hi: float) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi


def predicates(detect: Any) -> list[str]:
    """Every predicate string of a family's `detect` ({all, any, none: [...]}, `any_child: true`)."""
    if not isinstance(detect, dict):
        return []
    return [p for k in ('all', 'any', 'none') for p in detect.get(k) or []]


def validate(data: SauceData, cat: Any | None = None, spices: Any | None = None, complete: bool = True) -> list[str]:
    """Every problem, as readable lines. `cat` checks ids against the catalogue; `spices` (SpiceData) checks the dual
    spices; `complete=False` skips the missing-cell checks (for writing the matrices block by block)."""
    errors = list(data.errors)
    meta = data.meta
    for key, want in (('shelves', SHELVES), ('roles', ROLES), ('taste', TASTE), ('units', UNITS), ('keeps', KEEPS),
                      ('chips', CHIPS)):
        items = meta.get(key) or []
        for it in items:
            if not isinstance(it, dict) or not isinstance(it.get('id'), str) or not _bilingual(it):
                errors.append(f'meta.yaml: {key} entry needs id, en and hu: {it!r}')
        if [i.get('id') for i in items if isinstance(i, dict)] != list(want):
            errors.append(f'meta.yaml: {key} must be exactly {list(want)} in this order')
    for k in meta.get('keeps') or []:
        if isinstance(k, dict) and not (isinstance(k.get('days'), int) and k['days'] > 0):
            errors.append(f'meta.yaml: keeps {k.get("id")} needs whole days')
    for key in ('body', 'stability', 'words', 'heat'):
        if not meta.get(key):
            errors.append(f'meta.yaml: {key} missing')
    if [b.get('id') for b in meta.get('body') or []] != ['thin', 'coats', 'thick', 'stiff']:
        errors.append('meta.yaml: body must be thin, coats, thick, stiff')
    if [w.get('id') for w in meta.get('words') or []] != ['sings', 'good', 'muddled', 'fighting']:
        errors.append('meta.yaml: words must be sings, good, muddled, fighting')
    if [h.get('id') for h in meta.get('heat') or []] != ['mild', 'warm', 'hot', 'fiery']:
        errors.append('meta.yaml: heat must be mild, warm, hot, fiery')
    for key in ('body', 'stability', 'words', 'heat'):
        for it in meta.get(key) or []:
            if not isinstance(it, dict) or not _bilingual(it):
                errors.append(f'meta.yaml: {key} entry needs id, en and hu: {it!r}')

    # --- ingredients -----------------------------------------------------------------------------------------------
    rack = set(spices.profiles) if spices is not None else None
    for iid, e in data.ingredients.items():
        w = f'ingredients.yaml: {iid}'
        for k in sorted(set(e) - ING_KEYS):
            errors.append(f'{w}: unknown key {k!r}')
        for k in sorted(ING_KEYS - set(e) - {'item', 'say', 'g_per_pc', 'pairs_as', 'offer', 'alt'}):
            errors.append(f'{w}: {k} missing')
        item = e.get('item', iid)
        if cat is not None and item not in cat.items:
            errors.append(f'{w}: {item} is not a catalogue id')
        if 'item' in e and e['item'] == iid:
            errors.append(f'{w}: item repeats the id — leave it out')
        if 'say' in e and not _bilingual(e['say']):
            errors.append(f'{w}: say needs en and hu')
        if e.get('role') not in ROLES:
            errors.append(f'{w}: role must be one of {list(ROLES)}')
        if not isinstance(e.get('driver'), bool):
            errors.append(f'{w}: driver must be true or false')
        if e.get('shelf') not in SHELVES:
            errors.append(f'{w}: shelf must be one of {list(SHELVES)}')
        if e.get('unit') not in UNITS:
            errors.append(f'{w}: unit must be one of {list(UNITS)}')
        for u in e.get('alt') or []:
            if u not in UNITS or u == e.get('unit'):
                errors.append(f'{w}: alt unit {u!r} must be another of {list(UNITS)}')
        if not _num(e.get('default'), 0.01, 2000) or not _num(e.get('step'), 0.01, 500):
            errors.append(f'{w}: default and step must be positive numbers')
        if not _num(e.get('g_per_ml'), 0.05, 3):
            errors.append(f'{w}: g_per_ml must be 0.05-3')
        if (e.get('unit') == 'pcs' or 'pcs' in (e.get('alt') or [])) and not _num(e.get('g_per_pc'), 0.5, 2000):
            errors.append(f'{w}: a pcs item needs g_per_pc')
        p = e.get('per100') or {}
        if set(p) != set(TASTE) or not all(_num(p[a], 0, 10) for a in TASTE):
            errors.append(f'{w}: per100 must give each of {list(TASTE)} a number 0-10')
        b = e.get('body') or {}
        if b.get('method') not in BODY_METHODS or not _num(b.get('power'), 0, 500):
            errors.append(f'{w}: body needs a method of {list(BODY_METHODS)} and a power 0-500')
        elif (b['method'] == 'none') != (b['power'] == 0) and b['method'] not in ('reduce', 'emulsify'):
            errors.append(f'{w}: body method {b["method"]} with power {b["power"]} — none has 0, the others more')
        st = e.get('stability') or {}
        if set(st) != {'emulsifier_ml', 'curdles', 'starch'} or not _num(st.get('emulsifier_ml'), 0, 1000) \
                or not isinstance(st.get('curdles'), bool) or st.get('starch') not in STARCHES:
            errors.append(f'{w}: stability must be {{emulsifier_ml: 0-1000, curdles: bool, starch: one of {list(STARCHES)}}}')
        if e.get('keeps') not in KEEPS:
            errors.append(f'{w}: keeps must be one of {list(KEEPS)}')
        if not isinstance(e.get('fill'), str) or not _HEX.match(e['fill']):
            errors.append(f'{w}: fill must be #RRGGBB')
        if 'offer' in e and not isinstance(e['offer'], bool):
            errors.append(f'{w}: offer must be true or false')
        if e.get('offer') is False and cat is not None and cat.items.get(item) is not None \
                and cat.items[item].gluten != 'contains':
            errors.append(f'{w}: only a gluten-containing item is kept off the shelves (offer: false)')
        if cat is not None and cat.items.get(item) is not None and cat.items[item].gluten == 'contains' \
                and e.get('offer') is not False:
            errors.append(f'{w}: {item} contains gluten — it may be typed, never offered on a shelf (offer: false)')
        pa = e.get('pairs_as')
        if pa is not None:
            if PAIRS_AS.get(iid) != pa:
                errors.append(f'{w}: pairs_as is reserved for {sorted(PAIRS_AS)} (three only)')
            t = data.ingredients.get(pa)
            if t is None or t.get('driver') is not True or t.get('pairs_as') or t.get('role') != e.get('role'):
                errors.append(f'{w}: pairs_as {pa} must be a driver of the same role')
            if e.get('driver') is not True:
                errors.append(f'{w}: a pairs_as entry is a driver (it pairs)')
        if rack is not None:
            if iid in rack and iid not in DUALS:
                errors.append(f'{w}: {iid} is a rack spice — it enters a sauce through the spice engine, not here')
            if iid in DUALS and (e.get('driver') is not True or (e.get('per100') or {}).get('aromatic', 0) != 0):
                errors.append(f'{w}: a dual spice is a driver with aromatic 0 (its aroma comes from its spice profile)')
    if rack is not None:
        for dual in DUALS:
            if dual not in data.ingredients:
                errors.append(f'ingredients.yaml: the dual spice {dual} is missing')
            if dual not in rack:
                errors.append(f'ingredients.yaml: {dual} is listed as dual but is not a rack jar')

    # --- reasons ---------------------------------------------------------------------------------------------------
    used = Counter(c.reason for c in data.pairs.values()) + Counter(c.reason for c in data.driver_foods.values())
    for code, r in data.reasons.items():
        w = f'reasons.yaml: {code}'
        if not isinstance(r, dict) or r.get('kind') not in ('pair', 'food') or r.get('sign') not in ('+', '-', '0'):
            errors.append(f'{w}: needs kind pair|food and sign +|-|0')
            continue
        if not _bilingual(r):
            errors.append(f'{w}: needs en and hu')
            continue
        marks = ('{a}', '{b}') if r['kind'] == 'pair' else ('{s}', '{f}')
        for lang in ('en', 'hu'):
            if not all(m in r[lang] for m in marks):
                errors.append(f'{w}: the {lang} sentence must contain {" and ".join(marks)}')
        if r['kind'] == 'food' and r['sign'] == '-':
            errors.append(f'{w}: food scores are 0-3, a food reason cannot be negative')
        if complete and not used[code]:
            errors.append(f'{w}: never used — remove it or use it')

    # --- pairs -----------------------------------------------------------------------------------------------------
    drivers = data.drivers()
    for (a, b), c in data.pairs.items():
        for x in (a, b):
            e = data.ingredients.get(x) or {}
            if e.get('driver') is not True or e.get('pairs_as'):
                errors.append(f'{c.where}: {x} is not a driver — structural items are judged by the physics, not pairs')
        r = data.reasons.get(c.reason)
        if r is None or r.get('kind') != 'pair':
            errors.append(f'{c.where}: unknown pair reason {c.reason!r}')
        elif not _sign_ok(r['sign'], c.score):
            errors.append(f'{c.where}: score {c.score} does not fit reason {c.reason} (sign {r["sign"]})')
        if not -3 <= c.score <= 3:
            errors.append(f'{c.where}: score must be -3..3')
        if abs(c.score) == 3 and c.en is None:
            errors.append(f'{c.where}: a ±3 pair needs its own note (EN and HU)')
    if complete:
        for a, b in itertools.combinations(drivers, 2):
            if ((a, b) if a < b else (b, a)) not in data.pairs:
                errors.append(f'pairs: {a} + {b} missing (block {_block(data, a, b)})')

    # --- driver x food ---------------------------------------------------------------------------------------------
    for (s, f), c in data.driver_foods.items():
        e = data.ingredients.get(s) or {}
        if e.get('driver') is not True or e.get('pairs_as'):
            errors.append(f'{c.where}: {s} is not a driver — only drivers meet the foods')
        if s in NO_FOODS:
            errors.append(f'{c.where}: {s} seasons everything — it has no food row')
        r = data.reasons.get(c.reason)
        if r is None or r.get('kind') != 'food':
            errors.append(f'{c.where}: unknown food reason {c.reason!r}')
        elif not _sign_ok(r['sign'], c.score):
            errors.append(f'{c.where}: score {c.score} does not fit reason {c.reason} (sign {r["sign"]})')
        if not 0 <= c.score <= 3:
            errors.append(f'{c.where}: food score must be 0..3')
    if complete:
        for s in drivers:
            for f in data.foods if s not in NO_FOODS else []:
                if (s, f) not in data.driver_foods:
                    errors.append(f'driver_foods: {s} × {f} missing ({data.ingredients[s].get("shelf")}.yaml)')
        for s in drivers:
            row = [data.pair(s, o).score for o in drivers if o != s and (min(s, o), max(s, o)) in data.pairs]
            if row and len(set(row)) == 1:
                errors.append(f'pairs: every pair of {s} scores {row[0]} — judge them one by one')
            frow = [data.driver_foods[(s, f)].score for f in data.foods if (s, f) in data.driver_foods]
            if frow and len(set(frow)) == 1:
                errors.append(f'driver_foods: every food of {s} scores {frow[0]} — judge them one by one')

    # --- families --------------------------------------------------------------------------------------------------
    fids = [f.get('id') for f in data.families]
    for f in data.families:
        fid = f.get('id', '?')
        w = f'families.yaml: {fid}'
        if fids.count(fid) > 1:
            errors.append(f'{w}: duplicate')
        for k in sorted(set(f) - FAMILY_KEYS):
            errors.append(f'{w}: unknown key {k!r}')
        if not _bilingual(f):
            errors.append(f'{w}: needs en and hu')
        if f.get('parent') is not None and f.get('parent') not in fids:
            errors.append(f'{w}: parent {f.get("parent")} is not a family')
        if f.get('vessel') not in VESSELS:
            errors.append(f'{w}: vessel must be one of {list(VESSELS)}')
        if f.get('chip') not in CHIPS:
            errors.append(f'{w}: chip must be one of {list(CHIPS)}')
        if f.get('kind', 'savoury') not in KINDS:
            errors.append(f'{w}: kind must be one of {list(KINDS)}')
        if f.get('body') is not None and f.get('body') not in ('thin', 'coats', 'thick', 'stiff'):
            errors.append(f'{w}: body (the expected class) must be thin, coats, thick or stiff')
        det = f.get('detect')
        if not isinstance(det, dict) or set(det) - {'all', 'any', 'none', 'any_child'} or not det:
            errors.append(f'{w}: detect must be {{all|any|none: [predicates], any_child: true}}')
            continue
        if det.get('any_child') and not any(c.get('parent') == fid for c in data.families):
            errors.append(f'{w}: any_child, but it has no children')
        for pred in predicates(det):
            if not isinstance(pred, str) or not _PRED.match(pred):
                errors.append(f'{w}: predicate {pred!r} is not understood')
                continue
            kind, _, arg = pred.partition(':')
            if kind == 'item' and arg not in data.ingredients:
                errors.append(f'{w}: item:{arg} is not a sauce ingredient')
            if kind == 'role' and arg not in ROLES:
                errors.append(f'{w}: role:{arg} is not a role')
            if kind == 'body' and arg not in BODY_METHODS:
                errors.append(f'{w}: body:{arg} is not a body method')
            if kind == 'step' and arg not in STEP_CLASSES:
                errors.append(f'{w}: step:{arg} is not a step class of {list(STEP_CLASSES)}')
            if kind == 'spice' and spices is not None and arg not in spices.profiles:
                errors.append(f'{w}: spice:{arg} is not a rack jar')
            if kind == 'share' and arg.split('>=')[0] not in ROLES:
                errors.append(f'{w}: {pred}: the share is of a role')
        if f.get('note') is not None and not _bilingual(f.get('note')):
            errors.append(f'{w}: note needs en and hu')

    # --- classics --------------------------------------------------------------------------------------------------
    words = {w.get('id') for w in meta.get('words') or []}
    for c in data.classics:
        cid = c.get('id', '?')
        w = f'classics.yaml: {cid}'
        for k in sorted(set(c) - CLASSIC_KEYS):
            errors.append(f'{w}: unknown key {k!r}')
        if not _bilingual(c):
            errors.append(f'{w}: needs en and hu')
        if c.get('family') not in fids:
            errors.append(f'{w}: family {c.get("family")} is not in families.yaml')
        if not _num(c.get('yield_ml'), 50, 3000):
            errors.append(f'{w}: yield_ml must be 50-3000')
        lines = c.get('ingredients') or []
        if len(lines) < 2:
            errors.append(f'{w}: a sauce has at least two ingredients')
        for ln in lines:
            if not isinstance(ln, dict) or (('id' in ln) == ('spice' in ln)):
                errors.append(f'{w}: a line is {{id|spice, qty, unit}}: {ln!r}')
                continue
            if 'id' in ln:
                e = data.ingredients.get(ln['id'])
                if e is None:
                    errors.append(f'{w}: {ln["id"]} is not a sauce ingredient')
                    continue
                if e.get('offer') is False:
                    errors.append(f'{w}: {ln["id"]} is not offered — a seed never needs a swap')
                if ln.get('unit') not in [e.get('unit'), *(e.get('alt') or [])]:
                    errors.append(f'{w}: {ln["id"]} in {ln.get("unit")!r} — its units are {e.get("unit")} {e.get("alt") or []}')
                if cat is not None and cat.items.get(e.get('item', ln['id'])) is not None \
                        and cat.items[e.get('item', ln['id'])].gluten == 'contains':
                    errors.append(f'{w}: {ln["id"]} contains gluten — a seed is GF by construction')
            else:
                if spices is not None and ln['spice'] not in spices.profiles:
                    errors.append(f'{w}: {ln["spice"]} is not a rack jar')
                if ln.get('unit') not in ('tsp', 'tbsp', 'g'):
                    errors.append(f'{w}: a spice line is in tsp, tbsp or g')
            if not _num(ln.get('qty'), 0.01, 5000):
                errors.append(f'{w}: {ln.get("id") or ln.get("spice")}: qty must be positive')
        steps = c.get('steps') or {}
        if not (isinstance(steps, dict) and steps.get('en') and steps.get('hu') and len(steps['en']) == len(steps['hu'])
                and all(isinstance(s, str) and s.strip() for s in [*steps['en'], *steps['hu']])):
            errors.append(f'{w}: steps need the same number of lines in en and hu')
        if c.get('method') is not None and not _bilingual(c.get('method')):
            errors.append(f'{w}: method needs en and hu')
        exp = c.get('expected')
        if complete:
            ok = isinstance(exp, dict) and exp.get('word') in words and isinstance(exp.get('findings'), list) \
                and exp.get('body') in ('thin', 'coats', 'thick', 'stiff') and exp.get('keeps') in KEEPS \
                and exp.get('gluten') in ('gf', 'check')
            if not ok:
                errors.append(f'{w}: expected must be {{word, body, keeps, gluten: gf|check, findings: [ids]}}')

    # --- findings.yaml ---------------------------------------------------------------------------------------------
    fd = data.findings
    for key in FINDING_KEYS:
        if not _bilingual(fd.get(key)):
            errors.append(f'findings.yaml: {key} needs en and hu')
    for key in FIXES:
        fx = (fd.get('fixes') or {}).get(key)
        if not (isinstance(fx, dict) and _bilingual(fx) and _bilingual(fx.get('label'))):
            errors.append(f'findings.yaml: fixes.{key} needs a label and the fix, in en and hu')
    for key in ('mild', 'warm', 'hot', 'fiery'):
        if not _bilingual((fd.get('heat') or {}).get(key)):
            errors.append(f'findings.yaml: heat.{key} needs en and hu')
    for key in ('thin', 'coats', 'thick', 'stiff'):
        if not _bilingual((fd.get('body') or {}).get(key)):
            errors.append(f'findings.yaml: body.{key} needs en and hu')
    return errors


def _block(data: SauceData, a: str, b: str) -> str:
    sa, sb = data.ingredients[a].get('shelf'), data.ingredients[b].get('shelf')
    if sa in SHELVES and sb in SHELVES and SHELVES.index(sa) > SHELVES.index(sb):
        sa, sb = sb, sa
    return f'{sa}--{sb}.yaml'


def say(data: SauceData, cat: Any, iid: str, lang: str) -> str:
    """The name of an ingredient inside a sentence: its `say` name, else the catalogue name, lower case, no brackets."""
    e = data.ingredients.get(iid) or {}
    if e.get('say'):
        return e['say'][lang]
    it = cat.items.get(e.get('item', iid)) if cat is not None else None
    name = (it.hu if lang == 'hu' else it.en) if it else iid
    return re.sub(r'\s*\(.*?\)', '', name).strip().lower()
