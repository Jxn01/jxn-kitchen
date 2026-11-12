"""The README is the full documentation (the owner's rule: exhaustive, every setting, field and value — "not a list
closed with 'and so on'"; spec 2026-10-19 §11 SP13: every file, field, reason code, finding, weight, endpoint, component).
This holds it to the code: every endpoint, both engines' every finding, weight, reason code and fixed vocabulary, every
sauce family, shelf and shelf item, every spice jar, and every web component, screen, lib module and script must be
named in it. A new one that is not documented fails here."""
import pathlib
import re
import unittest

from kitchen import catalogue, sauce_data, sauce_engine, spice_data, spice_engine

REPO = pathlib.Path(__file__).resolve().parents[2]
README = (REPO / 'README.md').read_text()
CAT = catalogue.load(REPO / 'catalogue')
SD = spice_data.load(REPO / 'engine/spices')
UD = sauce_data.load(REPO / 'engine/sauces')


def named(text: str, ident: str) -> bool:
    """`ident` as a whole token: not part of a longer id (`salt` is not named by `salt-lifts`)."""
    return re.search(r'(?<![\w-])' + re.escape(ident) + r'(?![\w-])', text) is not None


def endpoints() -> list[str]:
    """The API paths, their parameters written as `{…}` (the README names them by meaning: {id}, not {bid})."""
    app = (REPO / 'server/kitchen/app.py').read_text()
    return sorted({re.sub(r'\{[^}]+\}', '{}', p) for p in re.findall(r"@app\.(?:get|post|put|delete|patch)\('(/api[^']*)'", app)})


GROUPS = {
    'spice axes': spice_data.AXES, 'spice roles': spice_data.ROLES, 'spice timings': spice_data.TIMINGS,
    'spice forms': spice_data.FORMS, 'spice findings': spice_data.FINDING_KEYS, 'spice weights': tuple(spice_engine.WEIGHTS),
    'spice reasons': tuple(SD.reasons), 'spice jars': tuple(SD.profiles),
    'sauce shelves': sauce_data.SHELVES, 'sauce roles': sauce_data.ROLES, 'sauce tastes': sauce_data.TASTE,
    'sauce units': sauce_data.UNITS, 'body methods': sauce_data.BODY_METHODS, 'starches': sauce_data.STARCHES,
    'keeping classes': sauce_data.KEEPS, 'vessels': sauce_data.VESSELS, 'chips': sauce_data.CHIPS,
    'step classes': sauce_data.STEP_CLASSES, 'kinds': sauce_data.KINDS, 'sauce findings': sauce_data.FINDING_KEYS,
    'fixes': sauce_data.FIXES, 'sauce weights': tuple(sauce_engine.WEIGHTS), 'sauce reasons': tuple(UD.reasons),
    'sauce families': tuple(f['id'] for f in UD.families), 'sauce items': tuple(UD.ingredients),
    'sauce classics': tuple(c['id'] for c in UD.classics),
    'web components': tuple(p.stem for p in (REPO / 'web/src/components').rglob('*.svelte')),
    'web screens': tuple(p.stem for p in (REPO / 'web/src/screens').glob('*.svelte')),
    'web lib': tuple(p.name for p in (REPO / 'web/src/lib').glob('*.ts')),
    'scripts': tuple(p.name for p in (REPO / 'scripts').iterdir() if p.is_file()),
}


class ReadmeNamesEverything(unittest.TestCase):
    def test_positive_control(self):
        self.assertFalse(named('the salt-lifts cell', 'salt'))
        self.assertTrue(named('a `salt` line', 'salt'))
        self.assertFalse(named(README, 'no-such-finding-xyzzy'))
        self.assertGreater(len(endpoints()), 30)
        for name, ids in GROUPS.items():
            self.assertTrue(ids, f'{name}: nothing to check (the table moved?)')

    def test_every_endpoint(self):
        doc = re.sub(r'\{[^}]+\}', '{}', README)
        self.assertEqual([e for e in endpoints() if e not in doc], [])

    def test_every_value_of_every_table(self):
        missing = {name: sorted(i for i in set(ids) if not named(README, i)) for name, ids in GROUPS.items()}
        self.assertEqual({k: v for k, v in missing.items() if v}, {})


if __name__ == '__main__':
    unittest.main()
