"""The spice engine: a blend in, its evaluation out — a pure function of the blend.

No I/O, no pantry, no cookbook. Everything it knows is engine/spices/ (spice_data.py), every cell of it hand-judged.
**The ledger is the score:** score = clamp(50 + Σ finding weights, 0, 100), and every weight is a line the user can
read, in English and Hungarian. The web composes no sentences.

Perceived share: s_i = parts_i × intensity_i / Σ parts × intensity — a teaspoon of cloves is not a teaspoon of parsley.
Volume share (parts_i / Σ parts) is used where the eye or the scale matters: the jar's colour, salt %, the batch grams.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from .spice_data import AXES, SpiceData, say, slot_ids

MAX_SPICES = 16
MAX_PARTS = 1000.0

# The weights of the structure findings and the pair factor, tuned until every classic blend reads
# good/sings with exactly its expected findings and every bad blend reads under 40 (server/tests/test_spice_engine.py).
WEIGHTS = {
    'pair': 20.0,             # every pair contributes s_a × s_b × score × this (a "random bite" of the blend)…
    'clash': 50.0,            # …and a negative pair two and a half times as much: a clash spoils more than a match helps
    'backbone': (8, 4, 2),    # the first (most specific) backbone, the second, every further one
    'one-note': -12,          # … and 40 more per unit of share over ONE_NOTE_SHARE
    'shouting': -10,
    'no-lift': -6,
    'no-backbone': -6,
    'seasoning-salt': 0,
    'sugar-burns': 0,
    'timing-conflict': 0,     # how to use it, not a flaw of the blend
    'toast-and-grind': -2,
    'single-spice': -12,
    'one-note-slope': -40,
}
ONE_NOTE_SHARE = 0.60        # one spice over this perceived share, and not a base
SHOUT_SHARE = 0.12           # an accent/finisher counts as loud above this share…
SHOUT_COUNT = 4              # …this many loud ones shout…
SHOUT_AGREE = 1.0            # …unless their pairs agree (mean pair score at least this)
LIFT_MIN = 0.15              # bright + herbal + floral under this part of the radar's mass: no lift
PAIR_LINE = 2                # a strong pair gets its own ledger line when it moves the score by this much
CARRIER_SHARE = 0.35         # base/body spices together under this share…
LEAD_SHARE = 0.30            # …and no single spice over this one (with more than three spices): no backbone
SALT_PCT = 30                # salt over this % of the jar's volume: a seasoning salt
WHOLE_WITH_GROUND = 3        # a whole spice among at least this many ground ones: toast and grind
CLASSIC_LINE = 60            # the nearest classic gets a ledger line from this similarity up
DOUBLE, HALF = 1.8, 0.55     # your share ÷ the classic's share: "double" / "half"
CUISINE_LINE = 10            # a cuisine is named from this % up


class EngineInputError(ValueError):
    pass


@dataclass(frozen=True)
class _Text:
    en: str
    hu: str


def _num(v: Any, lang: str) -> Any:
    """A number as a sentence in `lang` writes it: whole numbers without a decimal part (3, never 3.0), others with the
    language's decimal mark (0.6 / 0,6)."""
    if isinstance(v, float):
        if v.is_integer():
            return int(v)
        text = f'{v:g}'
        return text.replace('.', ',') if lang == 'hu' else text
    return v


def _fill(template: dict[str, str], kw: dict[str, Any]) -> dict[str, str]:
    """A bilingual template filled in, for both engines: a value given per language ({'en', 'hu'}) is picked by language,
    a number is written the language's way (`_num`). Every sentence either engine writes goes through here."""
    out = {}
    for lang in ('en', 'hu'):
        vals = {k: (v[lang] if isinstance(v, dict) else _num(v, lang)) for k, v in kw.items()}
        out[lang] = _cap(template[lang].format(**vals))
    return out


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _hex_to_lin(h: str) -> tuple[float, float, float]:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5))  # type: ignore[return-value]


def _lin_to_hex(rgb: tuple[float, float, float]) -> str:
    def srgb(c: float) -> int:
        c = max(0.0, min(1.0, c))
        v = c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
        return round(v * 255)
    return '#' + ''.join(f'{srgb(c):02X}' for c in rgb)


class SpiceEngine:
    """Built once at start from the validated knowledge; `evaluate` is then a pure function of its argument."""

    def __init__(self, data: SpiceData, cat: Any):
        self.data = data
        self.p = data.profiles
        self.names = {sid: {lang: say(data, cat, sid, lang) for lang in ('en', 'hu')} for sid in self.p}
        self.food_names = {fid: f['say'] for fid, f in data.foods.items()}
        self.f = data.findings
        self.words = sorted(data.meta['words'], key=lambda w: -w['min'])
        self.heat_words = data.meta['heat']
        self.cuisine_names = {c['id']: {'en': c['en'], 'hu': c['hu']} for c in data.meta['cuisines']}
        self.classics = data.classics

    # --- text helpers ------------------------------------------------------------------------------------------------
    def _list(self, ids: list[str], lang: str) -> str:
        names = [self.names[i][lang] for i in ids]
        if len(names) <= 1:
            return ''.join(names)
        return ', '.join(names[:-1]) + f' {self.f["and"][lang]} ' + names[-1]

    def _fmt(self, template: dict[str, str], **kw: Any) -> dict[str, str]:
        return _fill(template, kw)

    def _jars(self, ids: list[str]) -> dict[str, str]:
        return {lang: self._list(ids, lang) for lang in ('en', 'hu')}

    # --- the evaluation ----------------------------------------------------------------------------------------------
    def evaluate(self, parts: list[tuple[str, float]], batch_tbsp: float | None = None) -> dict[str, Any]:
        blend = self._check(parts)
        ids = list(blend)
        vol_total = sum(blend.values())
        vol = {i: blend[i] / vol_total for i in ids}
        weighted = {i: blend[i] * self.p[i]['intensity'] for i in ids}
        wt = sum(weighted.values())
        share = {i: weighted[i] / wt for i in ids}

        findings: list[dict[str, Any]] = []

        def add(fid: str, kind: str, weight: float, about: list[str], text: dict[str, str]) -> None:
            findings.append({'id': fid, 'kind': kind, 'weight': int(round(weight)), 'about': about, **text})

        # radar: share-weighted axes; `profile` keeps the 0-5 scale, `radar` is normalised to the strongest axis
        raw = {a: sum(share[i] * self.p[i]['axes'][a] for i in ids) for a in AXES}
        top = max(raw.values()) or 1.0
        radar = {a: round(raw[a] / top, 3) for a in AXES}
        mass = sum(raw.values()) or 1.0

        # pairs: every pair is an edge of the web and adds s_a × s_b × score × K to the score (K doubles for a clash):
        # the chance that two random bites of the blend meet that pair. Strong pairs (|score| >= 2) that move the score
        # by a whole point get their own ledger line; all the others are summed into one "the rest" line, so the ledger
        # still adds up exactly.
        edges = []
        pair_lines: list[tuple[float, str, str, dict[str, str], int]] = []
        pair_total = 0.0
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                a, b = sorted((ids[x], ids[y]))
                cell = self.data.pair(a, b)
                text = {'en': cell.en, 'hu': cell.hu} if cell.en else self._fmt(
                    self.data.reasons[cell.reason], a=self.names[a], b=self.names[b])
                edges.append({'a': a, 'b': b, 'score': cell.score, 'reason': cell.reason, **text})
                w = share[a] * share[b] * cell.score * (WEIGHTS['pair'] if cell.score > 0 else WEIGHTS['clash'])
                pair_total += w
                pair_lines.append((w, a, b, text, cell.score))
        shown = 0
        for w, a, b, text, sc in sorted(pair_lines, key=lambda t: -abs(t[0])):
            if abs(sc) >= 2 and abs(round(w)) >= PAIR_LINE:
                add(f'pair:{a}+{b}', 'good' if sc > 0 else 'warn', w, [a, b], text)
                shown += int(round(w))
        rest = int(round(pair_total)) - shown
        if rest:
            n_rest = len(pair_lines) - sum(1 for f in findings if f['id'].startswith('pair:'))
            add('pairs-rest', 'good' if rest > 0 else 'warn', rest, [],
                self._fmt(self.f['pairs-rest-good' if rest > 0 else 'pairs-rest-bad'], n=n_rest))

        # backbones: the most specific first (the most slots needed); each further one counts for less
        hits = []
        for bb in self.data.backbones:
            filled = [next(s for s in slot_ids(slot) if s in blend) for slot in bb['spices']
                      if any(s in blend for s in slot_ids(slot))]
            if len(filled) >= bb['need']:
                hits.append((bb, filled))
        hits.sort(key=lambda h: -h[0]['need'])
        steps = WEIGHTS['backbone']
        for n, (bb, filled) in enumerate(hits):
            add(f'backbone:{bb["id"]}', 'good', steps[min(n, len(steps) - 1)], filled,
                self._fmt(self.f['backbone'], name={'en': bb['en'], 'hu': bb['hu']}, note=bb['note']))

        cuisine_pct = self._cuisines(share)
        baking = bool(cuisine_pct) and cuisine_pct[0]['id'] == 'baking'

        if len(ids) == 1:
            add('single-spice', 'notice', WEIGHTS['single-spice'], ids, self._fmt(self.f['single-spice']))
        else:
            lead = max(ids, key=lambda i: share[i])
            if share[lead] > ONE_NOTE_SHARE and self.p[lead]['role'] != 'base':
                add('one-note', 'warn', WEIGHTS['one-note'] + WEIGHTS['one-note-slope'] * (share[lead] - ONE_NOTE_SHARE), [lead],
                    self._fmt(self.f['one-note'], spice=self.names[lead], pct=round(share[lead] * 100)))
            loud = [i for i in ids if self.p[i]['role'] in ('accent', 'finisher') and share[i] > SHOUT_SHARE]
            agree = [self.data.pair(x, y).score for n, x in enumerate(loud) for y in loud[n + 1:]]
            if len(loud) >= SHOUT_COUNT and sum(agree) / len(agree) < SHOUT_AGREE:
                loud.sort(key=lambda i: -share[i])
                add('shouting', 'warn', WEIGHTS['shouting'], loud, self._fmt(self.f['shouting'], spices=self._jars(loud)))
            lift = (raw['bright'] + raw['herbal'] + raw['floral']) / mass
            if lift < LIFT_MIN and not baking:
                sug = self._suggest(blend, share, lambda j: max(self.p[j]['axes']['bright'], self.p[j]['axes']['herbal']) >= 4)
                add('no-lift', 'notice', WEIGHTS['no-lift'], [], self._fmt(self.f['no-lift'], suggest=self._jars(sug)))
            carried = sum(share[i] for i in ids if self.p[i]['role'] in ('base', 'body'))
            if carried < CARRIER_SHARE and share[lead] <= LEAD_SHARE and len(ids) > 3 and not baking:
                sug = self._suggest(blend, share, lambda j: self.p[j]['role'] in ('base', 'body'))
                add('no-backbone', 'notice', WEIGHTS['no-backbone'], [], self._fmt(self.f['no-backbone'], suggest=self._jars(sug)))

        salt_pct = round(vol.get('salt', 0) * 100)
        sugar_pct = round((vol.get('sugar', 0) + vol.get('brown-sugar', 0)) * 100)
        if salt_pct > SALT_PCT:
            add('seasoning-salt', 'notice', WEIGHTS['seasoning-salt'], ['salt'],
                self._fmt(self.f['seasoning-salt'], pct=salt_pct))
        sugars = [i for i in ('sugar', 'brown-sugar') if i in blend]
        if sugars and not baking:
            add('sugar-burns', 'notice', WEIGHTS['sugar-burns'], sugars, self._fmt(self.f['sugar-burns']))

        timing = {t: [i for i in ids if self.p[i]['timing'] == t] for t in ('bloom', 'during', 'finish')}
        bloom = timing['bloom']
        fragile = [i for i in ids if self.p[i]['fragile'] and self.p[i]['timing'] != 'finish']
        conflict = bool(bloom and fragile) and not baking
        if conflict:
            add('timing-conflict', 'notice', WEIGHTS['timing-conflict'], bloom + fragile,
                self._fmt(self.f['timing-conflict'], bloom=self._jars(bloom), fragile=self._jars(fragile)))
        whole = [i for i in ids if self.p[i]['form'] == 'whole']
        ground = [i for i in ids if self.p[i]['form'] == 'ground']
        if whole and len(ground) >= WHOLE_WITH_GROUND:
            add('toast-and-grind', 'notice', WEIGHTS['toast-and-grind'], whole,
                self._fmt(self.f['toast-and-grind'], spices=self._jars(whole)))

        heat_value = sum(share[i] * self.p[i]['heat'] for i in ids)
        heat_id = next(h['id'] for h in self.heat_words if heat_value < h['below'])
        heat_word = next(h for h in self.heat_words if h['id'] == heat_id)
        add(f'heat:{heat_id}', 'notice' if heat_id in ('hot', 'fiery') else 'info', 0,
            [i for i in ids if self.p[i]['heat'] > 0], self._fmt(self.f['heat'][heat_id]))

        # the informational tail: the cuisine read and the nearest classic
        named = [c for c in cuisine_pct if c['pct'] >= CUISINE_LINE][:3]
        if named:
            add('cuisine', 'info', 0, [], {lang: _cap(self.f['cuisine'][lang].format(
                cuisines=', '.join(f'{self.cuisine_names[c["id"]][lang]} {c["pct"]} %' for c in named)))
                for lang in ('en', 'hu')})
        classics = self._nearest(blend, share, vol)
        if len(ids) >= 3 and classics and classics[0]['similarity'] >= CLASSIC_LINE:
            c = classics[0]
            add(f'classic:{c["id"]}', 'info', 0, [], self._classic_line(c))

        order = {'good': 0, 'warn': 0, 'notice': 1, 'info': 2}
        findings.sort(key=lambda f: (order[f['kind']] == 2, -abs(f['weight']), order[f['kind']]))
        total = sum(f['weight'] for f in findings)
        score = max(0, min(100, 50 + total))
        word = next(w for w in self.words if score >= w['min'])

        foods = self._foods(share)
        fills = [_hex_to_lin(self.p[i]['fill']) for i in ids]
        jar_fill = _lin_to_hex(tuple(sum(vol[i] * f[k] for i, f in zip(ids, fills)) for k in range(3)))  # type: ignore[arg-type]
        return {
            'score': score, 'base': 50, 'word': word['id'], 'word_text': {'en': word['en'], 'hu': word['hu']},
            'mascot': word['mascot'], 'findings': findings,
            'radar': radar, 'profile': {a: round(raw[a], 2) for a in AXES},
            'web': {'nodes': [{'id': i, 'share': round(share[i], 4)} for i in ids], 'edges': edges},
            'foods': foods,
            'timing': {**timing, 'conflict': conflict},
            'heat': {'value': round(heat_value, 2), 'word': heat_id, 'en': heat_word['en'], 'hu': heat_word['hu']},
            'classics': classics,
            'cuisines': cuisine_pct[:3],
            'salt_pct': salt_pct, 'sugar_pct': sugar_pct, 'jar_fill': jar_fill,
            'batch': self._batch(blend, batch_tbsp),
            'suggest': self._suggest(blend, share, lambda j: True, n=5),
            'shares': {i: round(share[i], 4) for i in ids}, 'volume': {i: round(vol[i], 4) for i in ids},
        }

    def _check(self, parts: list[tuple[str, float]]) -> dict[str, float]:
        if not parts:
            raise EngineInputError('a blend needs at least one spice')
        if len(parts) > MAX_SPICES:
            raise EngineInputError(f'at most {MAX_SPICES} spices in a blend')
        blend: dict[str, float] = {}
        for sid, n in parts:
            if sid not in self.p:
                raise EngineInputError(f'{sid} is not a rack jar')
            if sid in blend:
                raise EngineInputError(f'{sid} is in the blend twice')
            if not isinstance(n, (int, float)) or isinstance(n, bool) or not math.isfinite(n) or not 0 < n <= MAX_PARTS:
                raise EngineInputError(f'{sid}: parts must be more than 0 and at most {MAX_PARTS:g}')
            blend[sid] = float(n)
        return blend

    def _cuisines(self, share: dict[str, float]) -> list[dict[str, Any]]:
        # each spice's cuisines are first made to sum to 1 (black pepper, used everywhere, votes thinly everywhere; marjoram
        # votes mostly Hungarian), then share-weighted and squared, so the kitchen a blend really leans to stands out
        def vote(i: str, c: str) -> float:
            cu = self.p[i]['cuisines']
            return cu[c] / (sum(cu.values()) or 1)
        raw = {c: sum(share[i] * vote(i, c) for i in share) ** 2 for c in self.cuisine_names}
        tot = sum(raw.values()) or 1.0
        out = [{'id': c, 'pct': round(v / tot * 100)} for c, v in raw.items() if v > 0]
        return sorted(out, key=lambda c: (-c['pct'], c['id']))

    def _suggest(self, blend: dict[str, float], share: dict[str, float], ok: Any, n: int = 3) -> list[str]:
        """Jars not in the blend that the blend's spices like best (share-weighted pair scores), no clash allowed."""
        best = []
        for j in self.p:
            if j in blend or not ok(j):
                continue
            cells = [self.data.pair(i, j).score for i in blend]
            if min(cells) <= -2:
                continue
            best.append((sum(share[i] * self.data.pair(i, j).score for i in blend), j))
        best.sort(key=lambda t: (-t[0], list(self.p).index(t[1])))
        return [j for v, j in best[:n] if v > 0]

    def _foods(self, share: dict[str, float]) -> list[dict[str, Any]]:
        out = []
        for fid in self.data.foods:
            cells = {i: self.data.spice_foods[(i, fid)] for i in share}
            score = sum(share[i] * cells[i].score / 3 for i in share)
            vouch = sorted((i for i in share if cells[i].score >= 2), key=lambda i: -share[i] * cells[i].score)[:4]
            out.append({'id': fid, 'score': round(score, 3), 'vouchers': [
                {'spice': i, 'score': cells[i].score, **self._fmt(self.data.reasons[cells[i].reason],
                                                                   s=self.names[i], f=self.food_names[fid])}
                for i in vouch]})
        out.sort(key=lambda f: (-f['score'], list(self.data.foods).index(f['id'])))
        return out

    def _nearest(self, blend: dict[str, float], share: dict[str, float], vol: dict[str, float]) -> list[dict[str, Any]]:
        def shares(parts: dict[str, float]) -> dict[str, float]:
            w = {i: v * self.p[i]['intensity'] for i, v in parts.items()}
            t = sum(w.values())
            return {i: v / t for i, v in w.items()}
        out = []
        norm_a = math.sqrt(sum(v * v for v in share.values()))
        for c in self.classics:
            cs = shares(c['parts'])
            dot = sum(share.get(i, 0) * v for i, v in cs.items())
            sim = dot / (norm_a * math.sqrt(sum(v * v for v in cs.values())))
            tv = sum(c['parts'].values())
            theirs = {i: v / tv for i, v in c['parts'].items()}
            missing = sorted((i for i in c['parts'] if i not in blend), key=lambda i: -theirs[i])
            extra = sorted((i for i in blend if i not in c['parts']), key=lambda i: -vol[i])
            ratios = [{'spice': i, 'yours': round(vol[i] * 100), 'theirs': round(theirs[i] * 100)}
                      for i in c['parts'] if i in blend]
            # floored, so "100 %" means the same blend: a missing pinch reads 99 %, never a rounded-up 100
            out.append({'id': c['id'], 'en': c['en'], 'hu': c['hu'], 'similarity': math.floor(sim * 100 + 1e-9),
                        'missing': missing, 'extra': extra, 'ratios': ratios})
        out.sort(key=lambda c: (-c['similarity'], c['id']))
        return out[:3]

    def _classic_line(self, c: dict[str, Any]) -> dict[str, str]:
        d = self.f['diff']
        out = {}
        for lang in ('en', 'hu'):
            bits = []
            if c['missing']:
                bits.append(d['missing'][lang].format(spices=self._list(c['missing'][:3], lang)))
            if c['extra']:
                bits.append(d['extra'][lang].format(spices=self._list(c['extra'][:3], lang)))
            for r in c['ratios']:
                if r['theirs'] and r['yours'] / r['theirs'] >= DOUBLE:
                    bits.append(d['double'][lang].format(spice=self.names[r['spice']][lang]))
                elif r['theirs'] and r['yours'] / r['theirs'] <= HALF:
                    bits.append(d['half'][lang].format(spice=self.names[r['spice']][lang]))
            diff = (' — ' + '; '.join(bits[:4])) if bits and c['similarity'] < 100 else ''
            out[lang] = _cap(self.f['classic'][lang].format(sim=c['similarity'], classic=c[lang], diff=diff))
        return out

    def _batch(self, blend: dict[str, float], tbsp: float | None) -> dict[str, Any]:
        total = sum(blend.values())
        tbsp = total / 3 if tbsp is None else float(tbsp)
        k = tbsp * 3 / total
        grams = [{'spice': i, 'tsp': round(v * k, 2), 'g': round(v * k * self.p[i]['g_per_tsp'], 1)} for i, v in blend.items()]
        return {'tbsp': round(tbsp, 2), 'tsp': round(tbsp * 3, 2), 'grams': grams,
                'total_g': round(sum(g['g'] for g in grams), 1)}


def finding_ids(evaluation: dict[str, Any]) -> list[str]:
    """The finding ids of an evaluation, sorted — what the calibration fixtures compare."""
    return sorted(f['id'] for f in evaluation['findings'])


_ID = re.compile(r'^[a-z0-9-]+$')
