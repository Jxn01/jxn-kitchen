"""The night window. Mirrored exactly by web/src/lib/night.ts — keep the two (and their test tables) in step."""
from __future__ import annotations

from datetime import time


def is_night(t: time, start: int, end: int) -> bool:
    """True when hour-of-day `t` falls in [start, end). The window may wrap midnight; start == end means never."""
    if start == end:
        return False
    if start < end:
        return start <= t.hour < end
    return t.hour >= start or t.hour < end
