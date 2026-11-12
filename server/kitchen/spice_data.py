"""The spice engine's knowledge (spec 2026-10-19 §4.2): engine/spices/*.yaml, every cell hand-judged.

Loaded and validated at start — like the catalogue and the know-how, the server refuses to start on one bad cell.
`load()` never raises on bad content: it records what it could not read in `errors`, and `validate()` adds every rule
breach, so one run lists everything that is wrong.

Files: meta.yaml (labels), profiles.yaml (one per rack jar + not_on_rack), reasons.yaml (reason code -> bilingual
sentence), foods.yaml, pairs/<shelfA>--<shelfB>.yaml (every pair of jars once; row form
`<jar of shelf A>: {<jar of shelf B>: [score, reason] | [score, reason, "EN note", "HU note"]}`),
spice_foods/<shelf>.yaml (`<jar>: {<food>: [score, reason]}` for all foods), backbones.yaml, classics.yaml.
"""
from __future__ import annotations

import itertools
import pathlib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import yaml

AXES = ('warm', 'earthy', 'hot', 'bright', 'herbal', 'floral', 'bitter', 'savoury')
ROLES = ('base', 'body', 'accent', 'finisher')
TIMINGS = ('bloom', 'during', 'finish')
FORMS = ('whole', 'ground', 'both')
PROFILE_KEYS = {'id', 'say', 'shelf', 'fill', 'tag', 'axes', 'intensity', 'heat', 'role', 'timing', 'fragile', 'form',
                'cuisines', 'g_per_tsp'}
CLASSIC_KEYS = {'id', 'source', 'en', 'hu', 'parts', 'method', 'expected'}
BACKBONE_KEYS = {'id', 'spices', 'need', 'en', 'hu', 'note'}
FOOD_KEYS = {'id', 'icon', 'en', 'hu', 'say'}
_HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')
FINDING_KEYS = ('backbone', 'one-note', 'shouting', 'no-lift', 'no-backbone', 'seasoning-salt', 'sugar-burns',
                'timing-conflict', 'toast-and-grind', 'single-spice', 'cuisine', 'classic', 'gluten-label', 'gluten-yours',
                'gluten-ok', 'and', 'pairs-rest-good', 'pairs-rest-bad')


@dataclass(frozen=True)
class Cell:
    score: int
    reason: str
    en: str | None = None
    hu: str | None = None
    where: str = ''                  # the file it came from, for error messages


@dataclass
class SpiceData:
    meta: dict[str, Any]
    profiles: dict[str, dict[str, Any]]           # id -> profile, in file order (= shelf order on screen)
    not_on_rack: dict[str, str]
    reasons: dict[str, dict[str, Any]]
    foods: dict[str, dict[str, Any]]
    pairs: dict[tuple[str, str], Cell]            # key: the two ids sorted
    spice_foods: dict[tuple[str, str], Cell]      # key: (spice, food)
    backbones: list[dict[str, Any]]
    classics: list[dict[str, Any]]
    findings: dict[str, Any] = field(default_factory=dict)    # findings.yaml: the structure findings' sentences
    errors: list[str] = field(default_factory=list)

    def pair(self, a: str, b: str) -> Cell:
        return self.pairs[(a, b) if a < b else (b, a)]

    def shelf_ids(self) -> list[str]:
        return [s['id'] for s in self.meta.get('shelves', [])]


def _yaml(path: pathlib.Path, errors: list[str]) -> Any:
    try:
        return yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as e:
        errors.append(f'{path.name}: cannot read ({type(e).__name__}: {e})')
        return None


def _cell(raw: Any, where: str, errors: list[str]) -> Cell | None:
    if not isinstance(raw, list) or len(raw) not in (2, 4):
        errors.append(f'{where}: a cell is [score, reason] or [score, reason, "EN note", "HU note"], got {raw!r}')
        return None
    score, reason = raw[0], raw[1]
    if not isinstance(score, int) or isinstance(score, bool):
        errors.append(f'{where}: score must be a whole number, got {score!r}')
        return None
    if not isinstance(reason, str):
        errors.append(f'{where}: reason must be a code, got {reason!r}')
        return None
    en = hu = None
    if len(raw) == 4:
        en, hu = raw[2], raw[3]
        if not (isinstance(en, str) and en.strip() and isinstance(hu, str) and hu.strip()):
            errors.append(f'{where}: a note needs non-empty English and Hungarian text')
            return None
    return Cell(score, reason, en, hu, where)


def load(directory: pathlib.Path | str) -> SpiceData:
    d = pathlib.Path(directory)
    errors: list[str] = []
    meta = _yaml(d / 'meta.yaml', errors) or {}
    prof_doc = _yaml(d / 'profiles.yaml', errors) or {}
    profiles: dict[str, dict[str, Any]] = {}
    for p in prof_doc.get('profiles') or []:
        pid = p.get('id') if isinstance(p, dict) else None
        if not isinstance(pid, str):
            errors.append(f'profiles.yaml: an entry without an id: {p!r}')
            continue
        if pid in profiles:
            errors.append(f'profiles.yaml: duplicate profile {pid}')
        profiles.setdefault(pid, p)
    not_on_rack = {str(k): v for k, v in (prof_doc.get('not_on_rack') or {}).items()}
    reasons = _yaml(d / 'reasons.yaml', errors) or {}
    foods: dict[str, dict[str, Any]] = {}
    for f in (_yaml(d / 'foods.yaml', errors) or {}).get('foods') or []:
        fid = f.get('id') if isinstance(f, dict) else None
        if not isinstance(fid, str):
            errors.append(f'foods.yaml: an entry without an id: {f!r}')
            continue
        if fid in foods:
            errors.append(f'foods.yaml: duplicate food {fid}')
        foods.setdefault(fid, f)

    shelves = [s.get('id') for s in meta.get('shelves') or []]
    shelf_of = {pid: p.get('shelf') for pid, p in profiles.items()}
    pairs: dict[tuple[str, str], Cell] = {}
    pair_dir = d / 'pairs'
    for path in sorted(pair_dir.glob('*.yaml')) if pair_dir.is_dir() else []:
        m = re.fullmatch(r'([a-z-]+?)--([a-z-]+)', path.stem)
        if not m or m.group(1) not in shelves or m.group(2) not in shelves:
            errors.append(f'pairs/{path.name}: name it <shelf>--<shelf>.yaml after two shelves of meta.yaml')
            continue
        sa, sb = m.group(1), m.group(2)
        if shelves.index(sa) > shelves.index(sb):
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
                unknown = [x for x in (a, b) if x not in profiles]
                for x in unknown:
                    errors.append(f'{where}: {x} is not a rack jar')
                if unknown:
                    continue
                pair_shelves = [shelf_of[a], shelf_of[b]]
                if all(s in shelves for s in pair_shelves) and sorted(pair_shelves, key=shelves.index) != [sa, sb]:
                    first, second = sorted(pair_shelves, key=shelves.index)
                    errors.append(f'{where}: {a} ({shelf_of[a]}) + {b} ({shelf_of[b]}) belongs in {first}--{second}.yaml')
                if a == b:
                    errors.append(f'{where}: a jar is not paired with itself')
                    continue
                cell = _cell(raw, where, errors)
                if cell is None:
                    continue
                key = (a, b) if a < b else (b, a)
                if key in pairs:
                    errors.append(f'{where}: this pair is already stated in {pairs[key].where.split(":")[0]}')
                    continue
                pairs[key] = cell

    spice_foods: dict[tuple[str, str], Cell] = {}
    sf_dir = d / 'spice_foods'
    for path in sorted(sf_dir.glob('*.yaml')) if sf_dir.is_dir() else []:
        if path.stem not in shelves:
            errors.append(f'spice_foods/{path.name}: name it after a shelf of meta.yaml')
            continue
        rows = _yaml(path, errors) or {}
        for s, row in (rows.items() if isinstance(rows, dict) else []):
            if s not in profiles:
                errors.append(f'spice_foods/{path.name}: {s} is not a rack jar')
                continue
            if shelf_of[s] != path.stem:
                errors.append(f'spice_foods/{path.name}: {s} is on the {shelf_of[s]} shelf — move its row')
            for f, raw in (row.items() if isinstance(row, dict) else []):
                where = f'spice_foods/{path.name}: {s} × {f}'
                if f not in foods:
                    errors.append(f'{where}: {f} is not a food of foods.yaml')
                    continue
                cell = _cell(raw, where, errors)
                if cell is None:
                    continue
                if (s, f) in spice_foods:
                    errors.append(f'{where}: stated twice')
                    continue
                spice_foods[(s, f)] = cell

    backbones = (_yaml(d / 'backbones.yaml', errors) or {}).get('backbones') or []
    classics = (_yaml(d / 'classics.yaml', errors) or {}).get('classics') or []
    findings = _yaml(d / 'findings.yaml', errors) or {}
    return SpiceData(meta=meta, profiles=profiles, not_on_rack=not_on_rack, reasons=reasons, foods=foods, pairs=pairs,
                     spice_foods=spice_foods, backbones=backbones, classics=classics, findings=findings, errors=errors)


def _bilingual(d: Any) -> bool:
    return isinstance(d, dict) and all(isinstance(d.get(k), str) and d[k].strip() for k in ('en', 'hu'))


def _sign_ok(sign: str, score: int) -> bool:
    return (sign == '+' and score > 0) or (sign == '-' and score < 0) or (sign == '0' and score == 0)


def slot_ids(slot: Any) -> list[str]:
    return list(slot) if isinstance(slot, list) else [slot]


def validate(data: SpiceData, cat: Any | None = None, icon_ids: set[str] | None = None,
             complete: bool = True) -> list[str]:
    """Every problem, as readable lines. `cat` (a Catalogue) checks ids and coverage; `complete=False` skips the
    missing-cell checks (for writing the matrix block by block — the server always validates complete)."""
    errors = list(data.errors)
    meta = data.meta
    for key in ('shelves', 'axes', 'cuisines', 'roles', 'timings', 'words', 'heat'):
        items = meta.get(key) or []
        if not items:
            errors.append(f'meta.yaml: {key} missing')
        for it in items:
            if not isinstance(it, dict) or not isinstance(it.get('id'), str) or not _bilingual(it):
                errors.append(f'meta.yaml: {key} entry needs id, en and hu: {it!r}')
    if [a.get('id') for a in meta.get('axes') or []] != list(AXES):
        errors.append(f'meta.yaml: axes must be exactly {list(AXES)} in this order')
    if [r.get('id') for r in meta.get('roles') or []] != list(ROLES):
        errors.append(f'meta.yaml: roles must be {list(ROLES)}')
    if [t.get('id') for t in meta.get('timings') or []] != list(TIMINGS):
        errors.append(f'meta.yaml: timings must be {list(TIMINGS)}')
    shelves = data.shelf_ids()
    cuisines = [c.get('id') for c in meta.get('cuisines') or []]
    words = {w.get('id') for w in meta.get('words') or []}

    # --- profiles --------------------------------------------------------------------------------------------------
    for pid, p in data.profiles.items():
        w = f'profiles.yaml: {pid}'
        for k in sorted(set(p) - PROFILE_KEYS):
            errors.append(f'{w}: unknown key {k!r}')
        for k in sorted(PROFILE_KEYS - set(p) - {'say'}):
            errors.append(f'{w}: {k} missing')
        if cat is not None and pid not in cat.items:
            errors.append(f'{w}: not a catalogue id')
        if 'say' in p and not _bilingual(p['say']):
            errors.append(f'{w}: say needs en and hu')
        if p.get('shelf') not in shelves:
            errors.append(f'{w}: unknown shelf {p.get("shelf")!r}')
        if not isinstance(p.get('fill'), str) or not _HEX.match(p['fill']):
            errors.append(f'{w}: fill must be #RRGGBB')
        if not _bilingual(p.get('tag')):
            errors.append(f'{w}: tag needs en and hu')
        axes = p.get('axes') or {}
        if set(axes) != set(AXES) or not all(isinstance(axes[a], int) and 0 <= axes[a] <= 5 for a in AXES):
            errors.append(f'{w}: axes must give each of {list(AXES)} a whole number 0-5')
        elif sum(axes.values()) == 0:
            errors.append(f'{w}: axes are all zero')
        for k, lo, hi in (('intensity', 1, 5), ('heat', 0, 5)):
            v = p.get(k)
            if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
                errors.append(f'{w}: {k} must be a whole number {lo}-{hi}')
        for k, allowed in (('role', ROLES), ('timing', TIMINGS), ('form', FORMS)):
            if p.get(k) not in allowed:
                errors.append(f'{w}: {k} must be one of {list(allowed)}')
        if not isinstance(p.get('fragile'), bool):
            errors.append(f'{w}: fragile must be true or false')
        cu = p.get('cuisines') or {}
        if set(cu) != set(cuisines) or not all(isinstance(cu[c], int) and 0 <= cu[c] <= 3 for c in cuisines):
            errors.append(f'{w}: cuisines must give each of {cuisines} a whole number 0-3')
        g = p.get('g_per_tsp')
        if not isinstance(g, (int, float)) or isinstance(g, bool) or not 0.1 <= g <= 10:
            errors.append(f'{w}: g_per_tsp must be 0.1-10')
    for nid, why in data.not_on_rack.items():
        if not isinstance(why, str) or not why.strip():
            errors.append(f'profiles.yaml: not_on_rack {nid} needs its reason')
        if nid in data.profiles:
            errors.append(f'profiles.yaml: {nid} is both a profile and not_on_rack')
        if cat is not None and nid not in cat.items:
            errors.append(f'profiles.yaml: not_on_rack {nid} is not a catalogue id')
    if cat is not None:
        for iid, it in cat.items.items():
            if it.category == 'spices' and iid not in data.profiles and iid not in data.not_on_rack:
                errors.append(f'profiles.yaml: catalogue spice {iid} has no profile and no not_on_rack reason')
        for pid in data.profiles:
            it = cat.items.get(pid)
            if it is not None and it.gluten == 'contains':
                errors.append(f'profiles.yaml: {pid} contains gluten — it cannot be a rack jar')

    # --- reasons ---------------------------------------------------------------------------------------------------
    used = Counter(c.reason for c in data.pairs.values()) + Counter(c.reason for c in data.spice_foods.values())
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

    # --- foods -----------------------------------------------------------------------------------------------------
    for fid, f in data.foods.items():
        for k in sorted(set(f) - FOOD_KEYS):
            errors.append(f'foods.yaml: {fid}: unknown key {k!r}')
        if not _bilingual(f) or not _bilingual(f.get('say')):
            errors.append(f'foods.yaml: {fid}: needs en, hu and say')
        icon = f.get('icon') or ''
        if not re.fullmatch(r'om:[0-9A-F-]+|c:[a-z0-9-]+', icon):
            errors.append(f'foods.yaml: {fid}: icon must be om:CODE or c:name')
        elif icon_ids is not None and _icon_id(icon) not in icon_ids:
            errors.append(f'foods.yaml: {fid}: icon {icon} is not in the sprite')

    # --- pairs -----------------------------------------------------------------------------------------------------
    ids = list(data.profiles)
    for key, c in data.pairs.items():
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
        for a, b in itertools.combinations(ids, 2):
            if ((a, b) if a < b else (b, a)) not in data.pairs:
                errors.append(f'pairs: {a} + {b} missing (block {_block(data, a, b)})')

    # --- spice x food ----------------------------------------------------------------------------------------------
    for key, c in data.spice_foods.items():
        r = data.reasons.get(c.reason)
        if r is None or r.get('kind') != 'food':
            errors.append(f'{c.where}: unknown food reason {c.reason!r}')
        elif not _sign_ok(r['sign'], c.score):
            errors.append(f'{c.where}: score {c.score} does not fit reason {c.reason} (sign {r["sign"]})')
        if not 0 <= c.score <= 3:
            errors.append(f'{c.where}: food score must be 0..3')
    if complete:
        for s in ids:
            for f in data.foods:
                if (s, f) not in data.spice_foods:
                    errors.append(f'spice_foods: {s} × {f} missing ({data.profiles[s].get("shelf")}.yaml)')

    # --- backbones -------------------------------------------------------------------------------------------------
    bids: set[str] = set()
    for b in data.backbones:
        bid = b.get('id', '?')
        w = f'backbones.yaml: {bid}'
        if bid in bids:
            errors.append(f'{w}: duplicate')
        bids.add(bid)
        for k in sorted(set(b) - BACKBONE_KEYS):
            errors.append(f'{w}: unknown key {k!r}')
        slots = b.get('spices') or []
        for slot in slots:
            for sid in slot_ids(slot):
                if sid not in data.profiles:
                    errors.append(f'{w}: {sid} is not a rack jar')
        need = b.get('need')
        if not isinstance(need, int) or not 2 <= need <= len(slots):
            errors.append(f'{w}: need must be 2..{len(slots)}')
        if not _bilingual(b) or not _bilingual(b.get('note')):
            errors.append(f'{w}: needs en, hu and a note in both')

    # --- classics --------------------------------------------------------------------------------------------------
    cids: set[str] = set()
    for c in data.classics:
        cid = c.get('id', '?')
        w = f'classics.yaml: {cid}'
        if cid in cids:
            errors.append(f'{w}: duplicate')
        cids.add(cid)
        for k in sorted(set(c) - CLASSIC_KEYS):
            errors.append(f'{w}: unknown key {k!r}')
        if c.get('source') not in ('diy', 'world'):
            errors.append(f'{w}: source must be diy or world')
        if not _bilingual(c):
            errors.append(f'{w}: needs en and hu')
        if c.get('source') == 'diy' and not _bilingual(c.get('method')):
            errors.append(f'{w}: a diy blend needs its method in both languages')
        parts = c.get('parts') or {}
        if len(parts) < 2:
            errors.append(f'{w}: a blend has at least two spices')
        for sid, v in parts.items():
            if sid not in data.profiles:
                errors.append(f'{w}: {sid} is not a rack jar')
            if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
                errors.append(f'{w}: {sid} needs a positive number of parts')
        exp = c.get('expected')
        if complete:
            if not isinstance(exp, dict) or exp.get('word') not in words or not isinstance(exp.get('findings'), list):
                errors.append(f'{w}: expected must be {{word: <meta word>, findings: [ids]}}')

    # --- findings.yaml: every structure finding the engine can write, in both languages -----------------------------
    fd = data.findings
    for key in FINDING_KEYS:
        if not _bilingual(fd.get(key)):
            errors.append(f'findings.yaml: {key} needs en and hu')
    for key in ('mild', 'warm', 'hot', 'fiery'):
        if not _bilingual((fd.get('heat') or {}).get(key)):
            errors.append(f'findings.yaml: heat.{key} needs en and hu')
    for key in ('missing', 'extra', 'double', 'half'):
        if not _bilingual((fd.get('diff') or {}).get(key)):
            errors.append(f'findings.yaml: diff.{key} needs en and hu')
    if [h.get('id') for h in meta.get('heat') or []] != ['mild', 'warm', 'hot', 'fiery']:
        errors.append('meta.yaml: heat must be mild, warm, hot, fiery')
    if [w.get('id') for w in meta.get('words') or []] != ['sings', 'good', 'muddled', 'fighting']:
        errors.append('meta.yaml: words must be sings, good, muddled, fighting')

    # --- consistency (spec §9): what the classics prove about the pairs ---------------------------------------------
    together = Counter()
    for c in data.classics:
        for a, b in itertools.combinations(sorted(c.get('parts') or {}), 2):
            together[(a, b)] += 1
    for key, n in together.items():
        cell = data.pairs.get(key)
        if cell is None:
            continue
        if n >= 3 and cell.score < 0:
            errors.append(f'{cell.where}: scored {cell.score}, but these two sit together in {n} classic blends')
        if cell.score == -3:
            errors.append(f'{cell.where}: scored -3, but a classic blend holds both')
    if complete:
        for s in ids:
            row = [data.pairs[(s, o) if s < o else (o, s)].score for o in ids if o != s
                   if ((s, o) if s < o else (o, s)) in data.pairs]
            if row and len(set(row)) == 1:
                errors.append(f'pairs: every pair of {s} scores {row[0]} — judge them one by one')
            frow = [data.spice_foods[(s, f)].score for f in data.foods if (s, f) in data.spice_foods]
            if frow and len(set(frow)) == 1:
                errors.append(f'spice_foods: every food of {s} scores {frow[0]} — judge them one by one')
        for f in data.foods:
            threes = sum(1 for s in ids if (s, f) in data.spice_foods and data.spice_foods[(s, f)].score == 3)
            if threes < 3:
                errors.append(f'spice_foods: only {threes} jars score 3 with {f} — its board would be empty')
    return errors


def _block(data: SpiceData, a: str, b: str) -> str:
    shelves = data.shelf_ids()
    sa, sb = data.profiles[a].get('shelf'), data.profiles[b].get('shelf')
    if sa in shelves and sb in shelves and shelves.index(sa) > shelves.index(sb):
        sa, sb = sb, sa
    return f'{sa}--{sb}.yaml'


def _icon_id(ref: str) -> str:
    return 'om-' + ref[3:].lower() if ref.startswith('om:') else ('c-' + ref[2:] if ref.startswith('c:') else ref)


def say(data: SpiceData, cat: Any, sid: str, lang: str) -> str:
    """The name of a jar inside a sentence: its `say` name, else the catalogue name, in lower case, no parentheses."""
    p = data.profiles.get(sid) or {}
    if p.get('say'):
        return p['say'][lang]
    it = cat.items.get(sid) if cat is not None else None
    name = (it.hu if lang == 'hu' else it.en) if it else sid
    return re.sub(r'\s*\(.*?\)', '', name).strip().lower()
