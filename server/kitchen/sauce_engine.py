"""The sauce engine (spec 2026-10-19 §5.2): a sauce in, its evaluation out — a pure function of the sauce.

No I/O, no pantry, no cookbook (owner's decision D2); gluten is not computed here (sauces.py runs every line through the
gluten engine). Everything it knows is engine/sauces/ (sauce_data.py) plus the spice engine for the spices in a sauce.
**The ledger is the score:** score = clamp(50 + Σ finding weights, 0, 100); every weight is a line in both languages.

A sauce is a list of lines — {id, qty, unit} a shelf item · {spice, qty, unit} a rack jar · {blend, name, parts, qty,
unit} one of the owner's blends (the caller resolves its parts) · {item, name, qty?, unit?} a typed line matched to a
catalogue item that is not on the shelves (gluten only) · {raw} a typed line nothing matched (counts for nothing) —
and its steps (text, in either language: the engine reads heat, boiling, long simmering, reducing, blending, mounting,
marinating and chilling from them).

Every spice dimension is counted once (plan SP11 §7): a dual item (paprika, pepper, salt, sugar…) brings its plain
tastes through `per100`; the spices — rack jars, blend parts and the duals — are one virtual blend for the spice engine,
which adds aroma for all of them and heat only for the non-dual ones; its pair lines join at half weight except pairs of
two drivers (the sauce matrix judges those); the duals' foods come from their driver rows only.
"""
from __future__ import annotations

import math
import re
from typing import Any

from .sauce_data import DUALS, NO_FOODS, SauceData, say
from .spice_engine import SpiceEngine, _cap, _fill, _hex_to_lin, _lin_to_hex

# the taste wheel: a sauce's concentration on an axis (Σ per100 × g / Σ g) that reads as "fully that taste"
FULL = {'salt': 0.15, 'acid': 2.5, 'fat': 7.0, 'sweet': 3.0, 'heat': 1.0, 'umami': 2.0, 'aromatic': 3.0}
UNIT_ML = {'tbsp': 15.0, 'tsp': 5.0, 'dl': 100.0, 'ml': 1.0}
MAX_LINES = 24
MAX_QTY = 5000.0
BODY_CLASSES = ((0.6, 'thin'), (1.9, 'coats'), (3.0, 'thick'), (math.inf, 'stiff'))
BODY_ORDER = ['thin', 'coats', 'thick', 'stiff']
EMULSION_FAT = 0.30          # an egg emulsion: the fat is at least this share of the sauce's grams
EMULSION_BASE, EMULSION_SLOPE = 0.25, 5.5     # its body index = (fat share − base) × slope (mayonnaise stands, hollandaise coats)
EMULSION_OK, EMULSION_LIMIT = 1.0, 1.3        # oil ÷ room: up to the know-how's 250 ml a yolk holds; up to 130 % at the limit
PUREE_UNBLENDED = 0.4        # a purée item left in pieces (no blending step) thickens this much of what it would
MOUNT_SHARE = 0.20           # butter whisked into a pan sauce: from this share of the sauce up
VINAIGRETTE_FAT = 0.30       # oil and acid without an egg, the oil at least this share of the volume: a vinaigrette
CURDLE_ACID = 0.30           # spec §5.2: a curdling dairy, the acid axis at least this, and heat
CORN_ACID = 0.40
KEEP_ACID = 0.40             # acid-preserved lifts fresh things to 14 days from this acid up (no raw egg, no fresh dairy)
GARLIC_ACID = 0.05           # fresh garlic or herbs in oil under this acid, uncooked: the safety warning
LONG_SIMMER = 15             # minutes
SPICE_PER100 = 2.0           # a rack jar's aroma per 100 g = its intensity (1-5) × this; heat = its heat (0-5) × this
SALT_DAMP = 0.10             # in a driver's flavour share, salt counts at this much: it seasons more than it flavours (at full
                             # weight a teaspoon outweighed everything, and "lemon and salt" headed every ledger)
SEASONED = (0.25, 0.90)      # the salt axis of a savoury or rich sauce in this range: seasoned right (≈ 0.4–1.35 % salt)
SALTY_PCT = {'savoury': 1.5, 'rich': 1.5, 'sweet': 0.9, 'condiment': 8.25}   # salt % from which a sauce is too salty…
SALTY_SLOPE, SALTY_FLOOR = -4, -40                                           # …and the line grows 4 a percent beyond, to -40

# the weights (README → Sauce engine). The pair factor is the spice engine's: s_a × s_b × score × 20, a clash × 50.
WEIGHTS = {
    'pair': 20.0, 'clash': 50.0, 'spice-pairs': 0.5,
    'family': 6, 'flat': -5, 'too-sharp': -6, 'too-salty': -8, 'under-salted': -3, 'too-sweet': -4, 'greasy': -4,
    # a failed sauce sinks: a split emulsion, a curdled one, a starch that never cooks; garlic in oil is a safety warning
    'emulsion-ok': 0, 'emulsion-at-limit': -4, 'emulsion-split': -25, 'vinaigrette': 0, 'yolk-heat': 0,
    'curdle-warn': -20, 'curdle-notice': -2, 'starch-long-boil': -2, 'starch-arrowroot-dairy': -4, 'starch-corn-acid': -1,
    'starch-raw': -15, 'raw-egg': 0, 'garlic-in-oil': -20, 'too-thin-for': -3, 'too-thick-for': -3,
    'seasoned': 4, 'body-right': 3,
}
PAIR_LINE = 2                # a strong pair gets its own line when it moves the score by this much

_STEPS = {
    'heat': r"\b(boil\w*|simmer\w*|cook\w*|heat\w*|warm\w*|fr(y|ies|ied|ying)|saut[eé]\w*|melt\w*|toast\w*|roast\w*|bak(e|ed|ing)|"
            r"poach\w*|reduc\w*)\b|forr\w*|f[őo]z\w*|meleg[ií]t\w*|p[aá]rol\w*|pir[ií]t\w*|olvaszt\w*|gy[öo]ngy[öo]z\w*|"
            r"l[aá]ngon|beforral\w*",
    'boil': r"\bboil\w*|\bforr\w*|felforr\w*",
    'reduce': r"\breduc\w*|by half|forrald (be|vissza)|beforral\w*|s[űu]r[ií]tsd\b|besz[űu]r[ií]t\w*",
    'blend': r"\bblend\w*|\bblitz\w*|\bpur[eé]e\w*|liquidi[sz]\w*|turmix\w*|botmixer\w*|p[üu]r[eé]s[ií]t\w*|aprít[oó]\w*|\bpound\w*",
    'mount': r"whisk in (the )?(cold |warm )?butter|\bmonter\b|\bmount\w*|hideg vaj",
    'marinate': r"\bmarinat\w*|\bmarinade\b|\brub\b|p[aá]col\w*|\bp[aá]cb[ae]n?\b|bed[öo]rzs[öo]l\w*|d[öo]rzs[öo]ld",
    'chill': r"\bchill\w*|refrigerat\w*|\bfridge\b|h[űu]t[sőo]\w*|hidegen",
}
_STEP_RE = {k: re.compile(v, re.I) for k, v in _STEPS.items()}
_MINUTES = re.compile(r'(\d+)\s*(?:[–-]\s*(\d+)\s*)?(?:min|minute|perc)', re.I)


class SauceInputError(ValueError):
    pass


def step_classes(steps: list[str]) -> set[str]:
    """What the steps say, in either language: heat, boil, simmer-long, reduce, blend, mount, marinate, chill."""
    out = set()
    for s in steps:
        for k, rx in _STEP_RE.items():
            if rx.search(s):
                out.add(k)
        if _STEP_RE['heat'].search(s):
            mins = [int(b or a) for a, b in _MINUTES.findall(s)]
            if mins and max(mins) >= LONG_SIMMER:
                out.add('simmer-long')
    return out


def _round(x: float) -> int:
    return int(math.floor(x + 0.5))


class SauceEngine:
    """Built once at start from the validated knowledge; `evaluate` is then a pure function of its arguments."""

    def __init__(self, data: SauceData, spices: SpiceEngine, cat: Any):
        self.data = data
        self.ing = data.ingredients
        self.spices = spices
        self.sp = spices.p
        self.cat = cat
        self.names = {iid: {lang: say(data, cat, iid, lang) for lang in ('en', 'hu')} for iid in self.ing}
        self.f = data.findings
        self.meta = data.meta
        self.words = sorted(self.meta['words'], key=lambda w: -w['min'])
        self.keeps_days = {k['id']: k['days'] for k in self.meta['keeps']}
        self.keeps_label = {k['id']: {'en': k['en'], 'hu': k['hu']} for k in self.meta['keeps']}
        self.body_text = {b['id']: {'en': b['en'], 'hu': b['hu']} for b in self.meta['body']}
        self.levels = {lv['id']: lv for lv in self.meta.get('levels') or []}
        self.fam = {f['id']: f for f in data.families}
        self.children = {f['id']: [c for c in data.families if c.get('parent') == f['id']] for f in data.families}
        self.food_names = {fid: f['say'] for fid, f in data.foods.items()}

    # --- text helpers ------------------------------------------------------------------------------------------------
    def _name(self, key: str) -> dict[str, str]:
        """An ingredient's or a rack jar's name in a sentence."""
        return self.names.get(key) or self.spices.names.get(key) or {'en': key, 'hu': key}

    def _list(self, keys: list[str], lang: str) -> str:
        names = [self._name(k)[lang] for k in keys]
        if len(names) <= 1:
            return ''.join(names)
        return ', '.join(names[:-1]) + f' {self.f["and"][lang]} ' + names[-1]

    def _items(self, keys: list[str]) -> dict[str, str]:
        return {lang: self._list(keys, lang) for lang in ('en', 'hu')}

    def _fmt(self, template: dict[str, str], **kw: Any) -> dict[str, str]:
        return _fill(template, kw)

    # --- input -------------------------------------------------------------------------------------------------------
    @staticmethod
    def _qty(v: Any, what: str) -> float:
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or not 0 < v <= MAX_QTY:
            raise SauceInputError(f'{what}: the amount must be more than 0 and at most {MAX_QTY:g}')
        return float(v)

    def _grams(self, e: dict[str, Any], qty: float, unit: str) -> float:
        if unit in UNIT_ML:
            return qty * UNIT_ML[unit] * e['g_per_ml']
        if unit == 'g':
            return qty
        return qty * e['g_per_pc']

    def _jar_tsp(self, jar: str, qty: float, unit: str, what: str) -> float:
        if unit == 'tsp':
            return qty
        if unit == 'tbsp':
            return qty * 3
        if unit == 'g':
            return qty / self.sp[jar]['g_per_tsp']
        raise SauceInputError(f'{what}: a spice is measured in tsp, tbsp or g')

    def _read(self, lines: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, float]]:
        """The lines with their grams, and the virtual blend (rack jar -> teaspoons)."""
        if not isinstance(lines, list) or not lines:
            raise SauceInputError('a sauce needs at least one line')
        if len(lines) > MAX_LINES:
            raise SauceInputError(f'at most {MAX_LINES} lines in a sauce')
        out: list[dict[str, Any]] = []
        jars: dict[str, float] = {}
        for pos, ln in enumerate(lines):
            if not isinstance(ln, dict):
                raise SauceInputError(f'line {pos + 1}: not a line')
            kinds = [k for k in ('id', 'spice', 'blend', 'item', 'raw') if k in ln]
            if len(kinds) != 1:
                raise SauceInputError(f'line {pos + 1}: one of id, spice, blend, item or raw')
            kind = kinds[0]
            what = f'line {pos + 1}'
            if kind == 'id':
                e = self.ing.get(ln['id'])
                if e is None:
                    raise SauceInputError(f'{what}: {ln["id"]} is not on the sauce shelves')
                unit = ln.get('unit')
                if unit not in [e['unit'], *(e.get('alt') or [])]:
                    raise SauceInputError(f'{what}: {ln["id"]} is measured in {[e["unit"], *(e.get("alt") or [])]}')
                q = self._qty(ln.get('qty'), what)
                g = self._grams(e, q, unit)
                out.append({'pos': pos, 'kind': 'item', 'id': ln['id'], 'g': g, 'qty': q, 'unit': unit})
                if ln['id'] in DUALS:
                    jars[ln['id']] = jars.get(ln['id'], 0.0) + g / self.sp[ln['id']]['g_per_tsp']
            elif kind == 'spice':
                jar = ln['spice']
                if jar not in self.sp:
                    raise SauceInputError(f'{what}: {jar} is not a rack jar')
                tsp = self._jar_tsp(jar, self._qty(ln.get('qty'), what), ln.get('unit'), what)
                out.append({'pos': pos, 'kind': 'spice', 'id': jar, 'g': tsp * self.sp[jar]['g_per_tsp']})
                jars[jar] = jars.get(jar, 0.0) + tsp
            elif kind == 'blend':
                parts = ln.get('parts')
                if not isinstance(parts, list) or not parts:
                    raise SauceInputError(f'{what}: a blend line carries its parts')
                total = 0.0
                for p in parts:
                    if not (isinstance(p, (list, tuple)) and len(p) == 2 and p[0] in self.sp):
                        raise SauceInputError(f'{what}: a part is [rack jar, parts]')
                    total += self._qty(p[1], what)
                q = self._qty(ln.get('qty'), what)
                unit = ln.get('unit')
                if unit == 'g':
                    g_per_tsp = sum(p[1] / total * self.sp[p[0]]['g_per_tsp'] for p in parts)
                    tsp_total = q / g_per_tsp
                elif unit in ('tsp', 'tbsp'):
                    tsp_total = q * (3 if unit == 'tbsp' else 1)
                else:
                    raise SauceInputError(f'{what}: a blend is measured in tsp, tbsp or g')
                g = 0.0
                for jar, n in parts:
                    tsp = tsp_total * n / total
                    jars[jar] = jars.get(jar, 0.0) + tsp
                    g += tsp * self.sp[jar]['g_per_tsp']
                out.append({'pos': pos, 'kind': 'blend', 'id': ln['blend'], 'g': g,
                            'name': str(ln.get('name') or ''), 'parts': [list(p) for p in parts]})
            elif kind == 'item':
                if not isinstance(ln['item'], str):
                    raise SauceInputError(f'{what}: item is a catalogue id')
                out.append({'pos': pos, 'kind': 'off-shelf', 'id': ln['item'], 'g': 0.0, 'name': str(ln.get('name') or '')})
            else:
                if not isinstance(ln['raw'], str) or not ln['raw'].strip():
                    raise SauceInputError(f'{what}: a typed line is text')
                out.append({'pos': pos, 'kind': 'raw', 'g': 0.0, 'name': ln['raw'].strip()})
        if not any(x['g'] > 0 for x in out):
            raise SauceInputError('nothing on the tray weighs anything yet')
        return out, jars

    # --- the evaluation ----------------------------------------------------------------------------------------------
    def evaluate(self, lines: list[dict[str, Any]], steps: list[str] | None = None,
                 family: str | None = None) -> dict[str, Any]:
        steps = [s for s in (steps or []) if isinstance(s, str)]
        rows, jars = self._read(lines)
        sc = step_classes(steps)
        heat = 'heat' in sc
        items = [r for r in rows if r['kind'] == 'item']
        total = sum(r['g'] for r in rows)
        findings: list[dict[str, Any]] = []

        def add(fid: str, kind: str, weight: float, about: list[str], text: dict[str, str]) -> None:
            findings.append({'id': fid, 'kind': kind, 'weight': int(weight), 'about': about, **text})

        def e(r: dict[str, Any]) -> dict[str, Any]:
            return self.ing[r['id']]

        # --- the taste wheel --------------------------------------------------------------------------------------
        conc = {a: 0.0 for a in FULL}
        for r in items:
            for a in FULL:
                conc[a] += e(r)['per100'][a] * r['g']
        jar_g = {j: tsp * self.sp[j]['g_per_tsp'] for j, tsp in jars.items()}
        for j, g in jar_g.items():
            conc['aromatic'] += SPICE_PER100 * self.sp[j]['intensity'] * g
            if j not in DUALS:
                conc['heat'] += SPICE_PER100 * self.sp[j]['heat'] * g
        conc = {a: v / total for a, v in conc.items()}
        taste = {a: round(min(1.0, conc[a] / FULL[a]), 3) for a in FULL}

        # --- what the sauce is made of -----------------------------------------------------------------------------
        role_g: dict[str, float] = {}
        for r in items:
            role_g[e(r)['role']] = role_g.get(e(r)['role'], 0.0) + r['g']
        present = {r['id'] for r in items} | {self.data.pair_id(r['id']) for r in items}
        roles = set(role_g)
        methods = {e(r)['body']['method'] for r in items if e(r)['body']['power'] > 0 or e(r)['body']['method'] == 'reduce'}
        fat_g = sum(e(r)['per100']['fat'] / 10 * r['g'] for r in items)
        eggs = [r for r in items if e(r)['role'] == 'egg']
        egg_emulsifier = any(e(r)['stability']['emulsifier_ml'] > 0 for r in eggs)
        emulsion = egg_emulsifier and fat_g / total >= EMULSION_FAT
        thickeners = [r for r in items if e(r)['role'] == 'thickener']

        # --- body ------------------------------------------------------------------------------------------------------
        non_thick = total - sum(r['g'] for r in thickeners)
        thick_units = 0.0
        raw_starch: list[str] = []
        for r in items:
            b = e(r)['body']
            if b['method'] in ('slurry', 'roux'):
                if heat or e(r)['stability']['starch'] == 'xanthan':
                    thick_units += r['g'] / b['power']
                else:
                    raw_starch.append(r['id'])
            elif b['method'] == 'liaison' and heat and not emulsion:
                thick_units += r['g'] / b['power']
        r_index = thick_units * 1000 / non_thick if non_thick > 0 else 0.0
        matrix = sum(r['g'] for r in items if e(r)['role'] not in ('thickener', 'allium', 'herb', 'heat')
                     and not (e(r)['role'] == 'veg' and e(r)['body']['method'] == 'none')) or total
        base_num = 0.0
        for r in items:
            b = e(r)['body']
            if b['method'] in ('base', 'puree'):
                k = PUREE_UNBLENDED if b['method'] == 'puree' and 'blend' not in sc else 1.0
                base_num += b['power'] * r['g'] * k
        base_index = base_num / matrix
        em_index = max(0.0, fat_g / total - EMULSION_BASE) * EMULSION_SLOPE if emulsion else 0.0
        mount_index = 0.0
        if not thickeners and not eggs:
            for r in items:
                if e(r)['body']['method'] == 'mount' and r['g'] / total >= MOUNT_SHARE:
                    mount_index += e(r)['body']['power'] * r['g'] / total
        parts = {'thickener': r_index, 'base': base_index, 'emulsion': em_index, 'mount': mount_index}
        index = sum(parts.values())
        body_class = next(c for limit, c in BODY_CLASSES if index < limit)
        main = max(parts, key=lambda k: parts[k]) if index > 0 else 'none'
        reduce = 'reduce' in sc
        body = {'index': round(index, 2), 'class': body_class, 'by': main, 'reduce': reduce,
                **self.body_text[body_class]}
        if reduce:
            add('body-reduce', 'info', 0, [], self._fmt(self.f['body-reduce']))

        # --- stability -------------------------------------------------------------------------------------------------
        stability: list[dict[str, Any]] = []

        def stable(kind: str, level: str, text: dict[str, str], about: list[str]) -> None:
            stability.append({'kind': kind, 'level': level, 'about': about, **text})

        oil_ml = sum(r['g'] / e(r)['g_per_ml'] * e(r)['per100']['fat'] / 10 for r in items if e(r)['role'] == 'fat')
        if egg_emulsifier and oil_ml > 0 and emulsion:
            cap = sum(e(r)['stability']['emulsifier_ml'] * self._units(r) for r in items if e(r)['stability']['emulsifier_ml'] > 0)
            ratio = oil_ml / cap
            level, fid = (('ok', 'emulsion-ok') if ratio <= EMULSION_OK else
                          ('at-limit', 'emulsion-at-limit') if ratio <= EMULSION_LIMIT else ('warn', 'emulsion-split'))
            text = self._fmt(self.f[fid], oil=_round(oil_ml), cap=_round(cap), pct=_round(ratio * 100))
            about = [r['id'] for r in items if e(r)['stability']['emulsifier_ml'] > 0]
            add(fid, {'ok': 'info', 'at-limit': 'notice', 'warn': 'warn'}[level], WEIGHTS[fid], about, text)
            stable('emulsion', level, text, about)
            if heat:
                add('yolk-heat', 'notice', WEIGHTS['yolk-heat'], [r['id'] for r in eggs], self._fmt(self.f['yolk-heat']))
        elif not eggs and 'acid' in roles and oil_ml > 0 and oil_ml / self._volume(items) >= VINAIGRETTE_FAT:
            text = self._fmt(self.f['vinaigrette'])
            add('vinaigrette', 'info', WEIGHTS['vinaigrette'], [], text)
            stable('emulsion', 'ok', text, [])

        curdling = [r['id'] for r in items if e(r)['stability']['curdles']]
        if curdling and heat and taste['acid'] >= CURDLE_ACID:
            starch = any(e(r)['body']['method'] in ('roux', 'slurry') for r in thickeners)
            fid = 'curdle-notice' if starch else 'curdle-warn'
            text = self._fmt(self.f[fid], items=self._items(curdling))
            add(fid, 'notice' if starch else 'warn', WEIGHTS[fid], curdling, text)
            stable('curdle', 'at-limit' if starch else 'warn', text, curdling)
        starches = {e(r)['stability']['starch']: r['id'] for r in thickeners}
        if 'potato' in starches and 'simmer-long' in sc:
            self._starch(add, stable, 'starch-long-boil', 'at-limit', [starches['potato']])
        if 'arrowroot' in starches and 'dairy' in roles:
            self._starch(add, stable, 'starch-arrowroot-dairy', 'warn', [starches['arrowroot']])
        if 'corn' in starches and taste['acid'] >= CORN_ACID:
            self._starch(add, stable, 'starch-corn-acid', 'at-limit', [starches['corn']])
        if raw_starch:
            text = self._fmt(self.f['starch-raw'], items=self._items(raw_starch))
            add('starch-raw', 'warn', WEIGHTS['starch-raw'], raw_starch, text)
            stable('starch', 'warn', text, raw_starch)
        if eggs and not heat:
            text = self._fmt(self.f['raw-egg'])
            add('raw-egg', 'notice', WEIGHTS['raw-egg'], [r['id'] for r in eggs], text)
            stable('raw-egg', 'at-limit', text, [r['id'] for r in eggs])
        fresh = [r['id'] for r in items if r['id'] == 'garlic' or e(r)['role'] == 'herb']
        oily = any(e(r)['role'] == 'fat' and e(r)['per100']['fat'] >= 9 for r in items)
        garlic_oil = bool(fresh) and oily and conc['acid'] / FULL['acid'] < GARLIC_ACID and not heat
        if garlic_oil:
            text = self._fmt(self.f['garlic-in-oil'], items=self._items(fresh))
            add('garlic-in-oil', 'warn', WEIGHTS['garlic-in-oil'], fresh, text)
            stable('garlic-in-oil', 'warn', text, fresh)

        # --- keeps -----------------------------------------------------------------------------------------------------
        classes = set()
        for r in rows:
            if r['kind'] == 'item':
                classes.add('cooked' if e(r)['role'] == 'egg' and heat else e(r)['keeps'])
            elif r['kind'] in ('spice', 'blend'):
                classes.add('dry-stable')
        if garlic_oil:
            classes.add('oil-infusion')
        if taste['acid'] >= KEEP_ACID and not classes & {'raw-egg', 'fresh-dairy'}:
            classes = {('acid-preserved' if c in ('fresh', 'cooked', 'oil-infusion') else c) for c in classes}
        keep = min(classes, key=lambda c: (self.keeps_days[c], 'oil-infusion' != c))
        keeps = {'class': keep, 'days': self.keeps_days[keep], **self._fmt(self.f['keeps'], days=self.keeps_days[keep],
                                                                           why=self._lower(self.keeps_label[keep]))}

        # --- the family --------------------------------------------------------------------------------------------------
        ctx = {'present': present, 'roles': roles, 'methods': methods, 'steps': sc, 'emulsion': emulsion,
               'spices': bool(jars), 'blend': any(r['kind'] == 'blend' for r in rows), 'jars': set(jars),
               'role_share': {k: v / total for k, v in role_g.items()}}
        user = family is not None and family in self.fam
        path = self._path(family) if user else self._detect(ctx)
        fam = self.fam[path[-1]] if path else None
        kind = (fam or {}).get('kind', 'savoury')
        if fam is not None:
            add(f'family:{fam["id"]}', 'good', WEIGHTS['family'], [],
                self._fmt(self.f['family'], name={'en': fam['en'], 'hu': fam['hu']}, note=fam.get('note') or {'en': '', 'hu': ''}))
            want = fam.get('body')
            if want and want == body_class:
                add('body-right', 'good', WEIGHTS['body-right'], [], self._fmt(self.f['body-right'], name={'en': fam['en'], 'hu': fam['hu']},
                                                                           body=self.f['body'][body_class]))
            elif want and not (reduce and BODY_ORDER.index(body_class) < BODY_ORDER.index(want)):
                fid = 'too-thin-for' if BODY_ORDER.index(body_class) < BODY_ORDER.index(want) else 'too-thick-for'
                add(fid, 'notice', WEIGHTS[fid], [], self._fmt(self.f[fid], name={'en': fam['en'], 'hu': fam['hu']},
                                                             body=self.f['body'][body_class]))
        else:
            add('family-other', 'info', 0, [], self._fmt(self.f['family-other']))

        # --- balance ---------------------------------------------------------------------------------------------------
        salt_pct = round(conc['salt'] * 10, 1)
        if salt_pct >= SALTY_PCT[kind]:
            w = max(SALTY_FLOOR, WEIGHTS['too-salty'] + SALTY_SLOPE * (conc['salt'] * 10 - SALTY_PCT[kind]))
            add('too-salty', 'warn', w, [r['id'] for r in items if e(r)['per100']['salt'] >= 1],
                self._fmt(self.f['too-salty'], pct=salt_pct))
        elif kind == 'savoury' and taste['salt'] < 0.15:
            add('under-salted', 'notice', WEIGHTS['under-salted'], [], self._fmt(self.f['under-salted']))
        elif kind in ('savoury', 'rich') and SEASONED[0] <= taste['salt'] < SEASONED[1]:
            add('seasoned', 'good', WEIGHTS['seasoned'], [], self._fmt(self.f['seasoned'], pct=salt_pct))
        if kind == 'savoury' and taste['acid'] < 0.04 and taste['fat'] + taste['umami'] >= 0.6:
            add('flat', 'notice', WEIGHTS['flat'], [], self._fmt(self.f['flat'], suggest=self._name(self._acid_for(present))))
        if kind != 'condiment' and taste['acid'] >= 0.9 and taste['sweet'] + taste['fat'] < 0.3:
            add('too-sharp', 'warn', WEIGHTS['too-sharp'], [r['id'] for r in items if e(r)['role'] == 'acid'],
                self._fmt(self.f['too-sharp']))
        if kind in ('savoury', 'rich') and taste['sweet'] >= 0.5:
            add('too-sweet', 'notice', WEIGHTS['too-sweet'], [r['id'] for r in items if e(r)['role'] == 'sweet'],
                self._fmt(self.f['too-sweet']))
        if kind == 'savoury' and taste['fat'] >= 0.45 and not emulsion:
            add('greasy', 'notice', WEIGHTS['greasy'], [r['id'] for r in items if e(r)['role'] == 'fat'], self._fmt(self.f['greasy']))
        heat_word = next(h for h in self.meta['heat'] if taste['heat'] < h['below'])
        add(f'heat:{heat_word["id"]}', 'notice' if heat_word['id'] in ('hot', 'fiery') else 'info', 0,
            [r['id'] for r in items if e(r)['per100']['heat'] >= 2], self._fmt(self.f['heat'][heat_word['id']]))

        # --- the typed lines ---------------------------------------------------------------------------------------------
        for r in rows:
            if r['kind'] == 'raw':
                add('unknown-line', 'notice', 0, [], self._fmt(self.f['unknown-line'], line=r['name']))
        off = [r for r in rows if r['kind'] == 'off-shelf']
        if off:
            add('off-shelf', 'info', 0, [], self._fmt(self.f['off-shelf'], items={lang: ', '.join(
                (r['name'] or self._cat_name(r['id'], lang)) for r in off) for lang in ('en', 'hu')}))

        # --- the drivers: pairs and foods ----------------------------------------------------------------------------------
        flavour: dict[str, float] = {}
        named: dict[str, str] = {}         # pair id -> the line id to name in sentences (Greek yoghurt, not yoghurt)
        for r in items:
            if e(r)['driver']:
                pid = self.data.pair_id(r['id'])
                w = r['g'] * sum(e(r)['per100'][a] / FULL[a] * (SALT_DAMP if a == 'salt' else 1) for a in FULL if a != 'fat')
                flavour[pid] = flavour.get(pid, 0.0) + w
                named.setdefault(pid, r['id'])
        edges, pair_total, shown = self._pairs(flavour, named, add)
        spice_eval = self.spices.evaluate(list(jars.items())) if len(jars) >= 2 else None
        if spice_eval is not None:
            for sf in spice_eval['findings']:
                if not sf['id'].startswith('pair:') or all(a in DUALS for a in sf['about']):
                    continue
                w = sf['weight'] * WEIGHTS['spice-pairs']
                pair_total += w
                if abs(_round(w)) >= 1:
                    add(sf['id'], sf['kind'], _round(w), sf['about'], {'en': sf['en'], 'hu': sf['hu']})
                    shown += _round(w)
        rest = _round(pair_total) - shown
        if rest:
            n_rest = max(1, len(edges) - sum(1 for f in findings if f['id'].startswith('pair:')))
            add('pairs-rest', 'good' if rest > 0 else 'warn', rest, [],
                self._fmt(self.f['pairs-rest-good' if rest > 0 else 'pairs-rest-bad'], n=n_rest))

        order = {'good': 0, 'warn': 0, 'notice': 1, 'info': 2}
        findings.sort(key=lambda f: (order[f['kind']] == 2, -abs(f['weight']), order[f['kind']]))
        score = max(0, min(100, 50 + sum(f['weight'] for f in findings)))
        word = next(w for w in self.words if score >= w['min'])
        ids = {f['id'] for f in findings}
        return {
            'score': score, 'base': 50, 'word': word['id'], 'word_text': {'en': word['en'], 'hu': word['hu']},
            'mascot': word['mascot'], 'findings': findings,
            'taste': taste, 'salt_pct': salt_pct,
            'body': body, 'stability': stability, 'keeps': keeps,
            'family': {'id': fam['id'], 'en': fam['en'], 'hu': fam['hu'], 'path': path, 'user': user, 'kind': kind,
                       'chip': fam['chip']} if fam else None,
            'vessel': fam['vessel'] if fam else 'jug', 'fill': self._fill(rows, jar_g),
            'heat': {'value': taste['heat'], 'word': heat_word['id'], 'en': heat_word['en'], 'hu': heat_word['hu']},
            'web': {'nodes': [{'id': named[p], 'share': round(s, 4)} for p, s in self._shares(flavour).items()], 'edges': edges},
            'foods': self._foods(flavour, named, jar_g),
            'fixes': self._fixes(ids, thickeners, emulsion, curdling and heat),
            'suggest': self._suggest(flavour),
            'spices': {'jars': {j: round(t, 2) for j, t in jars.items()},
                       'radar': spice_eval['radar'] if spice_eval else None},
            'lines': [{'pos': r['pos'], 'kind': r['kind'], 'id': r.get('id'), 'g': round(r['g'], 1),
                       'share': round(r['g'] / total, 4)} for r in rows],
            'total_g': round(total, 1),
        }

    # --- pieces ----------------------------------------------------------------------------------------------------------
    def _units(self, r: dict[str, Any]) -> float:
        """A line's amount in its entry's own unit (an emulsifier's room is per unit: a yolk, a teaspoon of mustard)."""
        e = self.ing[r['id']]
        if r['unit'] == e['unit']:
            return r['qty']
        per_unit = self._grams(e, 1.0, e['unit'])
        return r['g'] / per_unit

    def _volume(self, items: list[dict[str, Any]]) -> float:
        return sum(r['g'] / self.ing[r['id']]['g_per_ml'] for r in items) or 1.0

    def _starch(self, add: Any, stable: Any, fid: str, level: str, about: list[str]) -> None:
        text = self._fmt(self.f[fid])
        add(fid, {'ok': 'info', 'at-limit': 'notice', 'warn': 'warn'}[level], WEIGHTS[fid], about, text)
        stable('starch', level, text, about)

    @staticmethod
    def _lower(t: dict[str, str]) -> dict[str, str]:
        return {k: v[:1].lower() + v[1:] for k, v in t.items()}

    def _cat_name(self, iid: str, lang: str) -> str:
        it = self.cat.items.get(iid) if self.cat is not None else None
        return (it.hu if lang == 'hu' else it.en) if it else iid

    def _path(self, fid: str) -> list[str]:
        path = [fid]
        while self.fam[path[0]].get('parent'):
            path.insert(0, self.fam[path[0]]['parent'])
        return path

    def _holds(self, pred: str, ctx: dict[str, Any]) -> bool:
        kind, _, arg = pred.partition(':')
        if pred == 'emulsion':
            return ctx['emulsion']
        if pred == 'spices':
            return ctx['spices']
        if pred == 'blend':
            return ctx['blend']
        if kind == 'item':
            return arg in ctx['present']
        if kind == 'role':
            return arg in ctx['roles']
        if kind == 'body':
            return arg in ctx['methods']
        if kind == 'step':
            return arg in ctx['steps']
        if kind == 'spice':
            return arg in ctx['jars']
        if kind == 'share':
            role, _, x = arg.partition('>=')
            return ctx['role_share'].get(role, 0.0) >= float(x)
        return False

    def _passes(self, fam: dict[str, Any], ctx: dict[str, Any]) -> bool:
        det = fam['detect']
        if det.get('any_child'):
            return False
        return (all(self._holds(p, ctx) for p in det.get('all') or [])
                and (not det.get('any') or any(self._holds(p, ctx) for p in det['any']))
                and not any(self._holds(p, ctx) for p in det.get('none') or []))

    def _match(self, fam: dict[str, Any], ctx: dict[str, Any]) -> list[str] | None:
        if fam['detect'].get('any_child'):
            for child in self.children[fam['id']]:
                deeper = self._match(child, ctx)
                if deeper:
                    return [fam['id'], *deeper]
            return None
        if not self._passes(fam, ctx):
            return None
        for child in self.children[fam['id']]:
            deeper = self._match(child, ctx)
            if deeper:
                return [fam['id'], *deeper]
        return [fam['id']]

    def _detect(self, ctx: dict[str, Any]) -> list[str]:
        for fam in self.data.families:
            if fam.get('parent') is None:
                path = self._match(fam, ctx)
                if path:
                    return path
        return []

    @staticmethod
    def _shares(flavour: dict[str, float]) -> dict[str, float]:
        tot = sum(flavour.values())
        return {k: v / tot for k, v in flavour.items()} if tot > 0 else {}

    def _pairs(self, flavour: dict[str, float], named: dict[str, str], add: Any) -> tuple[list[dict[str, Any]], float, int]:
        share = self._shares(flavour)
        ids = list(share)
        edges, lines, total = [], [], 0.0
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                a, b = sorted((ids[x], ids[y]))
                cell = self.data.pairs.get((a, b))
                if cell is None:            # the matrices are written block by block; the server validates them complete
                    continue
                na, nb = named[a], named[b]
                text = {'en': cell.en, 'hu': cell.hu} if cell.en else self._fmt(
                    self.data.reasons[cell.reason], a=self._name(na), b=self._name(nb))
                edges.append({'a': na, 'b': nb, 'score': cell.score, 'reason': cell.reason, **text})
                w = share[a] * share[b] * cell.score * (WEIGHTS['pair'] if cell.score > 0 else WEIGHTS['clash'])
                total += w
                lines.append((w, na, nb, text, cell.score))
        shown = 0
        for w, a, b, text, s in sorted(lines, key=lambda t: -abs(t[0])):
            if abs(s) >= 2 and abs(_round(w)) >= PAIR_LINE:
                x, y = sorted((a, b))
                add(f'pair:{x}+{y}', 'good' if s > 0 else 'warn', _round(w), [a, b], text)
                shown += _round(w)
        return edges, total, shown

    def _acid_for(self, present: set[str]) -> str:
        """The acid the sauce's drivers like best (lemon juice when nothing says otherwise)."""
        acids = [i for i in self.data.drivers() if self.ing[i]['role'] == 'acid']
        drivers = [p for p in present if p in self.ing and self.ing[p]['driver'] and not self.ing[p].get('pairs_as')]
        best, score = 'lemon-juice', -99
        for acid in acids:
            cells = [self.data.pairs.get(tuple(sorted((acid, d)))) for d in drivers if d != acid]
            s = sum(c.score for c in cells if c is not None)
            if s > score:
                best, score = acid, s
        return best

    def _foods(self, flavour: dict[str, float], named: dict[str, str], jar_g: dict[str, float]) -> list[dict[str, Any]]:
        weights = {k: v for k, v in flavour.items() if k not in NO_FOODS}
        spice_w = {j: g * (SPICE_PER100 * self.sp[j]['intensity'] / FULL['aromatic']
                           + SPICE_PER100 * self.sp[j]['heat'] / FULL['heat'])
                   for j, g in jar_g.items() if j not in DUALS}
        tot = sum(weights.values()) + sum(spice_w.values())
        if tot <= 0:
            return []
        out = []
        for fid in self.data.foods:
            score = 0.0
            vouch = []
            for p, w in weights.items():
                cell = self.data.driver_foods.get((p, fid))
                if cell is None:
                    continue
                score += w / tot * cell.score / 3
                if cell.score >= 2:
                    vouch.append((w / tot * cell.score, named[p], cell, 'sauce'))
            for j, w in spice_w.items():
                cell = self.spices.data.spice_foods.get((j, fid))
                if cell is None:
                    continue
                score += w / tot * cell.score / 3
                if cell.score >= 2:
                    vouch.append((w / tot * cell.score, j, cell, 'spice'))
            vouch.sort(key=lambda v: -v[0])
            out.append({'id': fid, 'score': round(score, 3), 'vouchers': [
                {'item': key, 'score': cell.score, **self._fmt(
                    (self.data.reasons if src == 'sauce' else self.spices.data.reasons)[cell.reason],
                    s=self._name(key), f=self.food_names[fid])} for _, key, cell, src in vouch[:4]]})
        out.sort(key=lambda f: (-f['score'], list(self.data.foods).index(f['id'])))
        return out

    def _fixes(self, ids: set[str], thickeners: list[dict[str, Any]], emulsion: bool, curdle_risk: Any) -> list[dict[str, Any]]:
        fx = self.f['fixes']
        roux = any(self.ing[r['id']]['body']['method'] == 'roux' for r in thickeners)
        want = [
            ('too-thin', 'body', 'up', 'too-thin-for' in ids),
            ('too-thick', 'body', 'down', 'too-thick-for' in ids),
            ('lumpy', 'body', 'smooth', bool(thickeners)),
            ('curdled', 'stability', 'mend', bool(curdle_risk)),
            ('split', 'stability', 'mend', emulsion),
            ('too-salty', 'salt', 'down', 'too-salty' in ids),
            ('too-sour', 'acid', 'down', 'too-sharp' in ids),
            ('greasy', 'fat', 'down', 'greasy' in ids),
            ('raw-flour', 'body', 'cook', roux),
        ]
        return [{'id': key, 'axis': axis, 'direction': d, 'label': fx[key]['label'], 'en': fx[key]['en'], 'hu': fx[key]['hu']}
                for key, axis, d, on in want if on]

    def _suggest(self, flavour: dict[str, float], n: int = 5) -> list[str]:
        """Drivers not in the sauce that its drivers like best (share-weighted), no clash allowed."""
        share = self._shares(flavour)
        if not share:
            return []
        best = []
        for j in self.data.drivers():
            if j in share:
                continue
            cells = [self.data.pairs.get(tuple(sorted((i, j)))) for i in share]
            if any(c is None for c in cells) or min(c.score for c in cells) <= -2:
                continue
            best.append((sum(share[i] * c.score for i, c in zip(share, cells)), j))
        best.sort(key=lambda t: -t[0])
        return [j for v, j in best[:n] if v > 0]

    def _fill(self, rows: list[dict[str, Any]], jar_g: dict[str, float]) -> str:
        mix, tot = [0.0, 0.0, 0.0], 0.0
        for r in rows:
            if r['kind'] == 'item':
                rgb, g = _hex_to_lin(self.ing[r['id']]['fill']), r['g']
                for k in range(3):
                    mix[k] += rgb[k] * g
                tot += g
        for j, g in jar_g.items():
            if j in DUALS:
                continue
            rgb = _hex_to_lin(self.sp[j]['fill'])
            for k in range(3):
                mix[k] += rgb[k] * g
            tot += g
        return _lin_to_hex(tuple(c / tot for c in mix)) if tot else '#E8DCC4'   # type: ignore[arg-type]

    def seed_lines(self, classic: dict[str, Any]) -> list[dict[str, Any]]:
        """A classic's ingredients as engine lines."""
        return [({'id': ln['id']} if 'id' in ln else {'spice': ln['spice']}) | {'qty': ln['qty'], 'unit': ln['unit']}
                for ln in classic['ingredients']]


def finding_ids(evaluation: dict[str, Any]) -> list[str]:
    return sorted(f['id'] for f in evaluation['findings'])
