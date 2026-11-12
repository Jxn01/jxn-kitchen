"""Match a parsed ingredient name to a catalogue item (spec §7.5).

1. exact: the whole folded name is a catalogue key (aliases outrank display names — catalogue.match_index);
2. stem: the LONGEST key whose tokens appear as a contiguous run in the name, where a name token matches a key token
   if equal, or if it starts with it and adds ≤ 3 letters (Hungarian suffixes: hagymá-t, csirkemell-et, tojás-ok,
   liszt-tel); ties prefer more exactly-equal tokens, then the longer key;
3. fuzzy: a typo — rapidfuzz ratio ≥ 90 against keys of ≥ 5 letters;
4. compound: Hungarian puts the head noun last (csusza|tészta, kocka|tészta, lebbencs|tészta). An otherwise unmatched
   word that ENDS in the one-word key (≥ 5 letters) of a gluten-CONTAINING item, after a ≥ 3-letter prefix and with
   ≤ 3 suffix letters, means that item. Only `contains` heads: this stage can turn '?' into "contains gluten" (the
   safe direction), never into OK — "búzakeményítő" must not become starch. (Live gap 2026-10-11: csuszatészta.)
Below that the line stays unmatched — and an unmatched line is never assumed gluten-free (gluten.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from .catalogue import Catalogue, fold, match_index

# words that describe the preparation, never the ingredient
_IGNORE = set('''friss apróra apro vágott vagott felvágott kockázott kockazva kockazott reszelt főtt fott sült sult
darabolt hámozott hamozott tisztított tisztitott kimagozott szeletelt zúzott zuzott finomra nagy kis közepes kozepes
fresh chopped diced minced grated sliced peeled large small medium finely roughly cooked'''.split())
_IGNORE = {fold(w) for w in _IGNORE}

# Hungarian words whose meaning depends on how they are counted
_COUNTABLE = {'pcs', 'head', 'slice', 'stalk', None}
_AMBIGUOUS = {
    'paprika': lambda unit, counted: 'hungarian-pepper' if counted else 'sweet-paprika',   # 1 db paprika = fresh
    'zeller': lambda unit, counted: 'celery' if unit == 'stalk' else 'celeriac',          # 1 szál zeller = celery
}


@dataclass(frozen=True)
class Match:
    item_id: str | None
    how: str | None = None        # exact | stem | fuzzy
    key: str | None = None


def _tokens(s: str) -> list[str]:
    return [t for t in re.split(r'[^0-9a-z]+', fold(s)) if t]


def _tok_match(name_tok: str, key_tok: str) -> int:
    """2 = equal, 1 = a suffixed form of the key token, 0 = no."""
    if name_tok == key_tok:
        return 2
    if len(key_tok) >= 3 and name_tok.startswith(key_tok) and len(name_tok) - len(key_tok) <= 3:
        return 1
    return 0


class Matcher:
    def __init__(self, cat: Catalogue) -> None:
        self.cat = cat
        self.index = match_index(cat)
        self.keys: list[tuple[tuple[str, ...], str, str]] = []      # (tokens, key, item)
        for key, item in self.index.items():
            toks = tuple(_tokens(key))
            if toks:
                self.keys.append((toks, key, item))
        self.fuzzy_keys = [k for _, k, _ in self.keys if len(k) >= 5]
        self.compound_heads = sorted(((k, item) for toks, k, item in self.keys
                                      if len(toks) == 1 and len(k) >= 5 and cat.items[item].gluten == 'contains'),
                                     key=lambda x: -len(x[0]))

    def match(self, name: str, unit: str | None = None, qty: float | None = None) -> Match:
        folded = ' '.join(_tokens(name))
        if not folded:
            return Match(None)
        counted = unit in _COUNTABLE and (unit is not None or qty is not None)
        if folded in _AMBIGUOUS:
            return Match(_AMBIGUOUS[folded](unit, counted), 'exact', folded)
        if folded in self.index:
            return Match(self.index[folded], 'exact', folded)
        full = folded.split()
        toks = [t for t in full if t not in _IGNORE]
        stripped = ' '.join(toks)
        if stripped in _AMBIGUOUS:
            return Match(_AMBIGUOUS[stripped](unit, counted), 'exact', stripped)
        if stripped in self.index:
            return Match(self.index[stripped], 'exact', stripped)
        found = self._longest(full)          # on ALL words: keys like "chopped tomatoes", "darált dió" need them
        if found is not None:
            if found.key in _AMBIGUOUS:
                return Match(_AMBIGUOUS[found.key](unit, counted), 'stem', found.key)
            return found
        if not toks:
            return Match(None)
        hit = process.extractOne(stripped, self.fuzzy_keys, scorer=fuzz.ratio, score_cutoff=90)
        if hit:
            return Match(self.index[hit[0]], 'fuzzy', hit[0])
        return self._compound(toks) or Match(None)

    def gluten_in(self, text: str | None) -> str | None:
        """The gluten-CONTAINING item a free text mentions (a line's note: "a kenyérhez", "a tészta kenéséhez"), else
        None. Used so a purpose phrase moved out of the name still keeps the line from reading OK."""
        toks = _tokens(text or '')
        if not toks:
            return None
        m = self._longest(toks) or self._compound(toks)
        return m.item_id if m and m.item_id and self.cat.items[m.item_id].gluten == 'contains' else None

    def _compound(self, toks: list[str]) -> Match | None:
        for tok in reversed(toks):
            for key, item in self.compound_heads:
                pos = tok.rfind(key)
                if pos >= 3 and len(tok) - (pos + len(key)) <= 3:
                    return Match(item, 'compound', key)
        return None

    def _longest(self, toks: list[str]) -> Match | None:
        """Safety net (spec §7): when a gluten-CONTAINING key appears anywhere in the name, the answer is that item even
        if a longer free key also appears — "liszt … tejföl …" must never resolve to sour cream and read OK. Erring
        towards "contains" is the safe side; the owner can mark a line OK by hand."""
        best: tuple[int, int, int] | None = None
        best_match: Match | None = None
        best_g: tuple[int, int, int] | None = None
        best_g_match: Match | None = None
        for ktoks, key, item in self.keys:
            n = len(ktoks)
            for i in range(len(toks) - n + 1):
                scores = [_tok_match(toks[i + j], ktoks[j]) for j in range(n)]
                if all(scores):
                    rank = (n, sum(1 for s in scores if s == 2), len(key))
                    if best is None or rank > best:
                        best, best_match = rank, Match(item, 'stem', key)
                    if self.cat.items[item].gluten == 'contains' and (best_g is None or rank > best_g):
                        best_g, best_g_match = rank, Match(item, 'stem', key)
        if best_g_match is not None and best_match is not None and self.cat.items[best_match.item_id].gluten != 'contains':
            return best_g_match
        return best_match
