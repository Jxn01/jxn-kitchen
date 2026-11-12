#!/usr/bin/env python3
"""Check engine/spices while writing it: every rule the server applies, plus how full each block of the matrix is.

Usage: scripts/spice-check.py [--complete]
Without --complete, missing cells are counted per block instead of listed (the matrix is written block by block);
with it, the check is exactly the server's start-up check. Exit 1 on any error.
"""
from __future__ import annotations

import itertools
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))

from kitchen import catalogue, spice_data  # noqa: E402


def main() -> int:
    complete = '--complete' in sys.argv
    cat = catalogue.load(ROOT / 'catalogue')
    data = spice_data.load(ROOT / 'engine/spices')
    errors = spice_data.validate(data, cat, complete=complete)
    shelves = data.shelf_ids()
    by_shelf = {s: [p for p, v in data.profiles.items() if v.get('shelf') == s] for s in shelves}
    print(f'{len(data.profiles)} jars, {len(data.foods)} foods')
    total_need = total_have = 0
    for i, sa in enumerate(shelves):
        for sb in shelves[i:]:
            if sa == sb:
                need = list(itertools.combinations(by_shelf[sa], 2))
            else:
                need = list(itertools.product(by_shelf[sa], by_shelf[sb]))
            have = sum(1 for a, b in need if ((a, b) if a < b else (b, a)) in data.pairs)
            total_need += len(need)
            total_have += have
            mark = 'done' if have == len(need) else ('—' if have == 0 else 'PARTIAL')
            print(f'  pairs {sa}--{sb}: {have}/{len(need)} {mark}')
    print(f'pairs total {total_have}/{total_need}')
    for s in shelves:
        need = len(by_shelf[s]) * len(data.foods)
        have = sum(1 for x in by_shelf[s] for f in data.foods if (x, f) in data.spice_foods)
        print(f'  foods {s}: {have}/{need}')
    for e in errors:
        print('ERROR', e)
    print(f'{len(errors)} errors')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
