"""Find durations in recipe step text so cook mode can turn them into tappable timer chips.
Hungarian and English; ranges take the upper bound; "1 hour 30 minutes" is one timer."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Found:
    start: int
    end: int
    seconds: int


_NUM = r'(\d+(?:[.,]\d+)?)'
_WORD_HOURS = {'negyed': 0.25, 'fél': 0.5, 'háromnegyed': 0.75, 'másfél': 1.5, 'két': 2, 'egy': 1}
_H = r'(?:óra|órá[a-z]*|hours?|hrs?)'
_M = r'(?:perc[a-z]*|minutes?|mins?\b|min\b)'
_S = r'(?:másodperc[a-z]*|seconds?|secs?\b)'
_PATTERN = re.compile(
    rf'(?P<wh>\b(?:{"|".join(_WORD_HOURS)})\s+{_H})'
    rf'|(?P<n>{_NUM})(?:\s*[-–]\s*(?P<nmax>{_NUM}))?\s*(?P<u>{_S}|{_M}|{_H})'
    rf'(?:\s+(?:and\s+|és\s+)?(?P<n2>{_NUM})\s*(?P<u2>{_M}))?',
    re.I)


def _f(s: str) -> float:
    return float(s.replace(',', '.'))


def _unit_seconds(u: str) -> int:
    u = u.lower()
    if re.fullmatch(_S, u):
        return 1
    if re.fullmatch(_M, u):
        return 60
    return 3600


MAX_TEXT = 2000   # a recipe step; longer text is scanned only this far (bounded work on hostile input)


def detect(text: str) -> list[Found]:
    out: list[Found] = []
    for m in _PATTERN.finditer((text or '')[:MAX_TEXT]):
        if m['wh']:
            word = m['wh'].split()[0].lower()
            secs = _WORD_HOURS[word] * 3600
        else:
            value = _f(m['nmax'] or m['n'])
            secs = value * _unit_seconds(m['u'])
            if m['n2']:
                secs += _f(m['n2']) * 60
        if secs > 0:
            out.append(Found(m.start(), m.end(), int(round(secs))))
    return out
