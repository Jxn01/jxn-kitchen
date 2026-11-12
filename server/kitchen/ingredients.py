"""Ingredient-line parser: "50 dkg Finomliszt", "2–3 gerezd fokhagyma", "só, bors ízlés szerint",
"1 (400 g) can chopped tomatoes" -> quantity (+ range), canonical unit, name, note. Hungarian and English.

Units are normalised to a small canonical set (mass to g, volume to ml, spoons to tbsp/tsp, countables as they are);
format_qty() turns them back into kitchen words per language (dkg-style values print as g/kg, ml as dl/l in HU).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .catalogue import fold


@dataclass(frozen=True)
class Parsed:
    raw: str
    qty: float | None
    qty_max: float | None
    unit: str | None
    name: str
    note: str | None = None


# input word (folded) -> (canonical unit, factor)
_UNITS: dict[str, tuple[str, float]] = {}
for words, unit, factor in [
    ('g gr gramm gram grams', 'g', 1), ('dkg dag deka', 'g', 10), ('kg kilo kilogramm kilogram', 'g', 1000),
    ('mg', 'g', 0.001),
    ('ml milliliter millilitre', 'ml', 1), ('cl', 'ml', 10), ('dl deciliter', 'ml', 100),
    ('l liter litre liters litres', 'ml', 1000),
    ('ek evokanal evokanalnyi tbsp tbs tbl tablespoon tablespoons', 'tbsp', 1),
    ('tk teaskanal teaskanalnyi tsp teaspoon teaspoons', 'tsp', 1),
    ('kk kaveskanal kaveskanalnyi mk mokkaskanal mokkaskanalnyi', 'tsp', 0.5),
    ('csipet csipetnyi pinch pinches', 'pinch', 1), ('gerezd clove cloves', 'clove', 1),
    ('fej head heads', 'head', 1), ('szal stalk stalks', 'stalk', 1), ('csokor bunch bunches', 'bunch', 1),
    ('db darab pcs pc piece pieces', 'pcs', 1), ('szelet slice slices', 'slice', 1),
    ('bogre cup cups csesze', 'cup', 1), ('pohar glass glasses', 'glass', 1),
    ('csomag tasak package packages pack packs packet packets sachet', 'pack', 1),
    ('doboz konzerv can cans tin tins', 'can', 1), ('uveg jar jars', 'jar', 1), ('marek handful handfuls', 'handful', 1),
    ('oz ounce ounces', 'oz', 1), ('lb lbs pound pounds', 'lb', 1),
]:
    for w in words.split():
        _UNITS[w] = (unit, factor)

_NUM_WORDS = {'fel': 0.5, 'masfel': 1.5, 'negyed': 0.25, 'haromnegyed': 0.75, 'egy': 1, 'ket': 2, 'ketto': 2,
              'harom': 3, 'negy': 4, 'ot': 5, 'hat': 6, 'het': 7, 'nyolc': 8, 'kilenc': 9, 'tiz': 10,
              'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'half': 0.5}
_UNICODE_FRAC = {'½': 0.5, '¼': 0.25, '¾': 0.75, '⅓': 1 / 3, '⅔': 2 / 3, '⅛': 0.125}
_DESCRIPTORS = {'kozepes', 'nagy', 'nagyobb', 'kis', 'kisebb', 'kicsi', 'pupozott', 'csapott', 'bo', 'keves',
                'small', 'medium', 'large', 'heaped', 'level', 'heaping'}
_TASTE = re.compile(r'\b(ízlés és igény szerint|ízlés szerint|igény szerint|tetszés szerint|to taste|as needed|'
                    r'optional|elhagyható)\b', re.I)
_NUMBER = r'\d+(?:[.,]\d+)?'
_QTY = re.compile(rf'^(?:(?P<mixw>\d+)\s+(?P<mixn>\d+)/(?P<mixd>\d+)'
                  rf'|(?P<uw>\d+)?\s*(?P<uf>[½¼¾⅓⅔⅛])'
                  rf'|(?P<fn>\d+)/(?P<fd>\d+)'
                  rf'|(?P<dec>{_NUMBER}))'
                  rf'(?:\s*[-–]\s*(?P<max>{_NUMBER}))?(?=\s|$|[a-zA-ZÀ-ž])')


def _num(s: str) -> float:
    return float(s.replace(',', '.'))


def _take_qty(text: str) -> tuple[float | None, float | None, str]:
    m = _QTY.match(text)
    if m:
        if m['mixw']:
            q = int(m['mixw']) + int(m['mixn']) / int(m['mixd'])
        elif m['uf']:
            q = (int(m['uw']) if m['uw'] else 0) + _UNICODE_FRAC[m['uf']]
        elif m['fn']:
            q = int(m['fn']) / int(m['fd'])
        else:
            q = _num(m['dec'])
        qmax = _num(m['max']) if m['max'] else None
        return q, qmax, text[m.end():].strip()
    first, _, rest = text.partition(' ')
    if fold(first) in _NUM_WORDS:
        return _NUM_WORDS[fold(first)], None, rest.strip()
    return None, None, text


# What an ingredient is FOR goes to the note: "liszt a tejföl behabarásához", "vaj a forma kikenéséhez", "olaj
# sütéshez", "flour for dusting". Left in the name, its nouns compete with the ingredient — "a tejföl" made a flour line
# match sour cream and read OK (a gluten hazard). Hungarian: a standalone "a/az" followed by a purpose word
# (…hoz/hez/höz or a postposition), or such a word with no article; English: "for …".
_PURPOSE_WORD = re.compile(r'(hoz|hez)$')   # folded: höz -> hoz
_POSTPOSITIONS = {'melle', 'ala', 'fole', 'tetejere', 'helyett', 'utan', 'koze', 'koré', 'kore'}


def _purpose_at(words: list[str]) -> int | None:
    """Index where a purpose phrase starts (never 0), or None."""
    folded = [fold(w).strip(',.;') for w in words]
    is_purpose = [bool(_PURPOSE_WORD.search(w)) or w in _POSTPOSITIONS for w in folded]
    for i in range(1, len(words)):
        if folded[i] == 'for':
            return i
        if folded[i] in ('a', 'az') and any(is_purpose[i + 1:]):
            return i
        if is_purpose[i]:
            return i
    return None


def _clean(name: str) -> str:
    return re.sub(r'\s+', ' ', name).strip(' ,.;:-–')


def _one(raw: str, text: str, notes: list[str]) -> Parsed | None:
    qty, qty_max, rest = _take_qty(text)
    words = rest.split()
    unit, factor = None, 1.0
    # descriptors may sit before the unit ("2 közepes db", "1 púpozott ek") or start a no-quantity line ("bő olaj")
    while words and fold(words[0]) in _DESCRIPTORS:
        notes.append(words.pop(0))
    if words and fold(words[0]).rstrip('.') in _UNITS and (qty is not None or len(words) > 1):
        unit, factor = _UNITS[fold(words[0]).rstrip('.')]
        words.pop(0)
    while words and fold(words[0]) in _DESCRIPTORS:
        notes.append(words.pop(0))
    cut = _purpose_at(words)
    if cut is not None:
        notes.append(' '.join(words[cut:]))
        words = words[:cut]
    name = _clean(' '.join(words))
    if not name:
        return None
    if qty is not None and qty == 0:            # Nosalty writes "0 dl Olaj" / "0 ízlés szerint Bors" for "some"
        qty, qty_max = None, None
    if qty is None:
        unit = None
    else:
        qty = round(qty * factor, 6)
        qty_max = round(qty_max * factor, 6) if qty_max is not None else None
    return Parsed(raw=raw, qty=qty, qty_max=qty_max, unit=unit, name=name, note=', '.join(notes) or None)


def parse_line(raw: str) -> list[Parsed]:
    raw = (raw or '').strip()
    if not raw or (raw.endswith(':') and not re.search(r'\d', raw)):
        return []                               # blank, or a section header ("A tésztához:")
    notes: list[str] = []
    text = raw
    for m in re.finditer(r'\(([^)]*)\)', text):
        notes.append(m.group(1).strip())
    text = re.sub(r'\([^)]*\)', ' ', text)
    taste = _TASTE.search(text)
    if taste:
        notes.append(taste.group(1).lower())
        text = _TASTE.sub(' ', text)
    text = re.sub(r'\s+', ' ', text).strip(' ,')
    qty, _, _ = _take_qty(text)
    if qty is None:
        # "só, bors" / "salt and pepper": several short ingredients on one line
        parts = [p.strip() for p in re.split(r'(?<!\d),(?!\d)|\s+(?:és|and|&)\s+', text) if p.strip()]
        if len(parts) > 1 and all(len(p.split()) <= 3 for p in parts):
            out = [_one(raw, p, list(notes)) for p in parts]
            return [p for p in out if p]
    else:
        head, *tail = re.split(r'(?<!\d),(?!\d)', text, maxsplit=1)   # "7,5 dkg" is a number, not a separator
        if tail and tail[0].strip():
            text = head
            notes.append(tail[0].strip())
    parsed = _one(raw, text, notes)
    return [parsed] if parsed else []


def scale(p: Parsed, factor: float) -> Parsed:
    return replace(p, qty=None if p.qty is None else round(p.qty * factor, 6),
                   qty_max=None if p.qty_max is None else round(p.qty_max * factor, 6))


_LABELS = {  # unit -> (hu, en singular, en plural)
    'tbsp': ('ek', 'tbsp', 'tbsp'), 'tsp': ('tk', 'tsp', 'tsp'), 'pinch': ('csipet', 'pinch', 'pinches'),
    'clove': ('gerezd', 'clove', 'cloves'), 'head': ('fej', 'head', 'heads'), 'stalk': ('szál', 'stalk', 'stalks'),
    'bunch': ('csokor', 'bunch', 'bunches'), 'pcs': ('db', 'pcs', 'pcs'), 'slice': ('szelet', 'slice', 'slices'),
    'cup': ('bögre', 'cup', 'cups'), 'glass': ('pohár', 'glass', 'glasses'), 'pack': ('csomag', 'pack', 'packs'),
    'can': ('doboz', 'can', 'cans'), 'jar': ('üveg', 'jar', 'jars'), 'handful': ('marék', 'handful', 'handfuls'),
    'oz': ('oz', 'oz', 'oz'), 'lb': ('lb', 'lb', 'lb'),
}
_FRAC_OUT = [(0.5, '½'), (0.25, '¼'), (0.75, '¾'), (1 / 3, '⅓'), (2 / 3, '⅔'), (0.125, '⅛')]


def _dec(x: float, lang: str) -> str:
    s = f'{x:.2f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',') if lang == 'hu' else s


def _frac(x: float, lang: str) -> str:
    whole, part = int(x), x - int(x)
    if part < 0.02:
        return str(whole)
    for val, sym in _FRAC_OUT:
        if abs(part - val) < 0.02:
            return f'{whole or ""}{sym}'
    return _dec(x, lang)


def format_qty(qty: float | None, unit: str | None, lang: str, qty_max: float | None = None) -> str:
    if qty is None:
        return ''
    def one(q: float) -> tuple[str, str]:
        if unit == 'g':
            return (_dec(q / 1000, lang), 'kg') if q >= 1000 else (_dec(q, lang), 'g')
        if unit == 'ml':
            if q >= 1000:
                return _dec(q / 1000, lang), 'l'
            if lang == 'hu' and q >= 50 and q % 10 == 0:
                return _dec(q / 100, lang), 'dl'
            return _dec(q, lang), 'ml'
        if unit is None:
            return _frac(q, lang), ''
        hu, en1, en2 = _LABELS[unit]
        return _frac(q, lang), (hu if lang == 'hu' else (en2 if (qty_max or q) > 1 else en1))
    n, u = one(qty)
    if qty_max is not None:
        n = f'{n}–{one(qty_max)[0]}'
    return f'{n} {u}'.strip()
