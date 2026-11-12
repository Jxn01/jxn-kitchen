"""Both engines' sentences, as text (spec 2026-10-19 §6.1: everything bilingual): a number in a Hungarian sentence takes
the Hungarian decimal mark. The béchamel's ledger read "Jól sózva — kb. 0.6 % só." (2026-10-20) — a float formatted the
English way into a Hungarian template; the class is every number either engine puts into either language."""
import pathlib
import random
import re
import unittest

import yaml

from kitchen import catalogue, sauce_data, spice_data
from kitchen.sauce_engine import SauceEngine, SauceInputError
from kitchen.spice_engine import SpiceEngine

REPO = pathlib.Path(__file__).resolve().parents[2]
CAT = catalogue.load(REPO / 'catalogue')
SPICES = SpiceEngine(spice_data.load(REPO / 'engine/spices'), CAT)
DATA = sauce_data.load(REPO / 'engine/sauces')
SAUCES = SauceEngine(DATA, SPICES, CAT)
BAD_SAUCES = yaml.safe_load((pathlib.Path(__file__).parent / 'fixtures/bad_sauces.yaml').read_text())['bad']
BAD_BLENDS = yaml.safe_load((pathlib.Path(__file__).parent / 'fixtures/bad_blends.yaml').read_text())
HU_POINT = re.compile(r'\d\.\d')          # 0.6 — in Hungarian it is 0,6
EN_COMMA = re.compile(r'\d,\d(?!\d\d)')    # 0,6 — in English it is 0.6 (1,000 would be a thousands mark: not flagged)


def sentences(x, lang: str) -> list[str]:
    """Every string under a `lang` key, anywhere in an answer."""
    if isinstance(x, dict):
        return [v for k, v in x.items() if k == lang and isinstance(v, str)] + [s for v in x.values() for s in sentences(v, lang)]
    if isinstance(x, list):
        return [s for v in x for s in sentences(v, lang)]
    return []


def answers():
    for c in DATA.classics:
        for lang in ('en', 'hu'):
            yield f"sauce {c['id']}", SAUCES.evaluate(SAUCES.seed_lines(c), c['steps'][lang])
    for b in BAD_SAUCES:
        yield f"bad sauce {b['id']}", SAUCES.evaluate(b['lines'], b['steps'])
    rng = random.Random(11)
    ids = list(DATA.ingredients)
    for n in range(300):
        lines = []
        for iid in rng.sample(ids, rng.randint(2, 12)):
            e = DATA.ingredients[iid]
            lines.append({'id': iid, 'qty': round(e['default'] * rng.choice([0.25, 0.5, 1, 3]), 2), 'unit': rng.choice([e['unit'], *(e.get('alt') or [])])})
        try:
            yield f'random sauce {n}', SAUCES.evaluate(lines, rng.sample(['Simmer 10 minutes.', 'Whisk in the oil.', 'Serve cold.'], rng.randint(0, 2)))
        except SauceInputError:
            continue
    for c in SPICES.data.classics:
        yield f"blend {c['id']}", SPICES.evaluate(list(c['parts'].items()))
    for b in BAD_BLENDS:
        yield f"bad blend {b['id']}", SPICES.evaluate(list(b['parts'].items()))


class DecimalMarks(unittest.TestCase):
    def test_positive_control_the_walk_finds_a_point_in_a_hungarian_sentence(self):
        found = sentences({'findings': [{'en': 'about 0.6 % salt', 'hu': 'kb. 0.6 % só'}]}, 'hu')
        self.assertEqual([s for s in found if HU_POINT.search(s)], ['kb. 0.6 % só'])
        self.assertTrue(EN_COMMA.search('about 0,6 % salt'))
        self.assertFalse(EN_COMMA.search('1,000 ml'))

    def test_every_number_takes_its_languages_decimal_mark(self):
        bad = []
        for what, a in answers():
            bad += [f'{what} hu: {s}' for s in sentences(a, 'hu') if HU_POINT.search(s)]
            bad += [f'{what} en: {s}' for s in sentences(a, 'en') if EN_COMMA.search(s)]
        self.assertEqual(sorted(set(bad))[:20], [])


if __name__ == '__main__':
    unittest.main()
