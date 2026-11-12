"""The gluten engine (spec §7) — safety-critical: the kitchen it serves is fully gluten-free.

Per ingredient line:
  ok      — a gluten-free item, or an unmatched line the owner marked OK by hand
  swap    — a `contains` item (wheat flour, nokedli, soy sauce…): shown struck through with its GF swap (+ a tip)
  yours   — a `label` item that is in the pantry: the kitchen is fully GF, so it is the owner's GF one
  check   — a `label` item not in the pantry: check the label (and buy it as "GF …")
  unknown — not matched: NEVER assumed gluten-free; the recipe can't be ✓ GF until it is matched or marked OK
"May contain traces" is not a gluten state at all.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from . import pantry
from .catalogue import Catalogue, Item


@dataclass(frozen=True)
class LineGluten:
    status: str
    swap_id: str | None = None
    tip_en: str | None = None
    tip_hu: str | None = None


def check_line(cat: Catalogue, state: dict[str, Any], item_id: str | None, ok_override: bool,
               note_gluten: str | None = None) -> LineGluten:
    """`note_gluten`: a gluten-containing item the line's note mentions ("vaj a kenyérhez"). It never lets the line read
    OK by itself — 'check', with a tip naming it (fail closed). A line the owner marked OK by hand stays OK."""
    if item_id is None or item_id not in cat.items:
        return LineGluten('ok' if ok_override else 'unknown')
    item = cat.items[item_id]
    if item.gluten == 'contains':
        return LineGluten('swap', item.swap, item.tip_en, item.tip_hu)
    if item.gluten == 'label' and not pantry.has(cat, state, item_id):
        return LineGluten('check')
    mention = cat.items.get(note_gluten or '')
    if mention is not None and not ok_override:
        return LineGluten('check', None,
                          f'Its note mentions {mention.en.lower()}. Make sure that part is gluten-free too.',
                          f'A megjegyzésében ez áll: {mention.hu.lower()}. Nézd meg, hogy az a rész is gluténmentes legyen.')
    return LineGluten('yours' if item.gluten == 'label' else 'ok')


def verdict(statuses: Iterable[str]) -> dict[str, Any]:
    """The recipe's gluten verdict. ✓ GF ('gf') needs at least one line and every line OK or your GF one: a recipe with
    NO lines (a failed import, an empty scan draft) is 'empty', never 'gf' — nothing has been checked (spec §7.2; it
    read 'gf' until 2026-10-11, found on a live import of a list page)."""
    c = Counter(statuses)
    state = ('empty' if not sum(c.values()) else 'unknown' if c['unknown'] else 'swaps' if c['swap']
             else 'check' if c['check'] else 'gf')
    return {'state': state, 'swaps': c['swap'], 'check': c['check'], 'unknown': c['unknown']}


GF_PREFIX = {'en': 'GF ', 'hu': 'GM '}
_MARKED = re.compile(r'(^|[\s(])(gf|gm)\b|glut[eé]n', re.I)


def needs_marker(cat: Catalogue, item: Item) -> bool:
    """A `label` item, or the GF version of a wheat product — whose plain name ("Hosszú tészta", "Zsemlemorzsa")
    would otherwise read as the wheat one. Used wherever such an item is written out: recipe swaps, shopping list."""
    return item.gluten == 'label' or any(i.swap == item.id for i in cat.items.values() if i.gluten == 'contains')


def marked(text: str, lang: str) -> str:
    """`text` with the GF marker in front, unless it already says GF/GM/gluten-free."""
    return text if _MARKED.search(text) else GF_PREFIX[lang] + text


def gf_name(cat: Catalogue, item_id: str | None, lang: str) -> str | None:
    """The GF item's name for a `contains` line (the GF version's text), always visibly GF; None when no swap
    applies. A swap to a different, naturally GF product (couscous -> quinoa) is marked too: in a recipe's GF
    version every swapped line says so."""
    item = cat.items.get(item_id or '')
    if item is None or item.gluten != 'contains' or not item.swap:
        return None
    swap = cat.items[item.swap]
    return marked(swap.hu if lang == 'hu' else swap.en, lang)
