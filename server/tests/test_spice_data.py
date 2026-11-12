"""The spice engine's knowledge (spec 2026-10-19 §4.2, §9): complete, consistent, and the guards bite.

Every check here has a positive control: a copy of the real data broken in exactly one way must fail with a message
naming the break — a guard that cannot fail proves nothing.
"""
import copy
import itertools
import pathlib
import re
import unittest

import yaml

from kitchen import catalogue, spice_data
from kitchen.spice_data import Cell

REPO = pathlib.Path(__file__).resolve().parents[2]
CAT = catalogue.load(REPO / 'catalogue')
DATA = spice_data.load(REPO / 'engine/spices')
SPRITE = set(re.findall(r'<symbol id="i-([^"]+)"', (REPO / 'web/public/sprite.svg').read_text()))


def broken(mutate):
    d = copy.deepcopy(DATA)
    mutate(d)
    return spice_data.validate(d, CAT)


class TheRealKnowledge(unittest.TestCase):
    def test_validates_completely(self):
        self.assertEqual(spice_data.validate(DATA, CAT, SPRITE), [])

    def test_every_pair_of_jars_is_judged_once(self):
        ids = list(DATA.profiles)
        self.assertEqual(len(ids), 61)
        want = {tuple(sorted(p)) for p in itertools.combinations(ids, 2)}
        self.assertEqual(set(DATA.pairs), want)
        self.assertEqual(len(DATA.pairs), 1830)

    def test_every_jar_meets_every_food(self):
        self.assertEqual(len(DATA.foods), 25)
        self.assertEqual(set(DATA.spice_foods), {(s, f) for s in DATA.profiles for f in DATA.foods})

    def test_twenty_eight_blocks_one_per_shelf_pair(self):
        files = sorted(p.stem for p in (REPO / 'engine/spices/pairs').glob('*.yaml'))
        shelves = DATA.shelf_ids()
        self.assertEqual(files, sorted(f'{a}--{b}' for i, a in enumerate(shelves) for b in shelves[i:]))

    def test_the_rack_holds_the_know_how_racks_48_with_their_colours_and_tags(self):
        """One source: a jar on the know-how rack keeps that page's colour and words."""
        lib = {s['id']: s for s in (yaml.safe_load(p.read_text()) for p in (REPO / 'knowhow').glob('*.yaml'))}
        rack = [it for p in lib['spices']['pages'] if p['id'] in ('warm', 'earthy', 'hot', 'mediterranean', 'green', 'special')
                for it in p['chart']['items']]
        self.assertEqual(len(rack), 48)
        by_label = {}
        for pid, prof in DATA.profiles.items():
            item = CAT.items[pid]
            for name in {item.en, (prof.get('say') or {}).get('en', '')}:
                by_label.setdefault(name.lower(), pid)
        alias = {'vanilla': 'vanilla-pod', 'ginger (ground)': 'ground-ginger', 'coriander seed': 'coriander-seed',
                 'fennel seed': 'fennel-seed', 'mustard seed': 'mustard-seed', 'chilli flakes': 'chili-flakes',
                 'cayenne': 'cayenne', 'garlic powder': 'garlic-powder', 'onion powder': 'onion-powder', 'sage': 'sage-dried',
                 'basil (dried)': 'basil-dried', 'bay leaf': 'bay-leaf', 'dill': 'dill-dried', 'parsley': 'parsley-dried',
                 'lovage': 'lovage-dried', 'tarragon': 'tarragon-dried', 'mint': 'mint-dried', 'chives': 'chives-dried',
                 'coriander leaf': 'coriander-leaf-dried', 'wild garlic': 'wild-garlic-dried', 'juniper': 'juniper',
                 'poppy seed': 'poppy-seeds', 'sesame': 'sesame', 'asafoetida (hing)': 'asafoetida', 'nigella': 'nigella',
                 'smoked paprika': 'smoked-paprika'}
        for it in rack:
            label = (it['label']['en'] if isinstance(it['label'], dict) else it['label']).lower()
            pid = alias.get(label) or by_label.get(label)
            self.assertIsNotNone(pid, label)
            prof = DATA.profiles[pid]
            self.assertEqual(prof['fill'].upper(), it['fill'].upper(), pid)
            self.assertEqual(prof['tag'], it['value'], pid)

    def test_the_diy_classics_are_the_know_how_page_number_for_number(self):
        """classics.yaml (source: diy) is the structured twin of knowhow/11-blends.yaml → Make your own."""
        page = next(p for p in yaml.safe_load((REPO / 'knowhow/11-blends.yaml').read_text())['pages'] if p['id'] == 'diy')
        body = page['en']['body']
        words = {'sweet paprika': 'sweet-paprika', 'paprika': 'sweet-paprika', 'ground caraway': 'caraway', 'caraway': 'caraway',
                 'marjoram': 'marjoram', 'garlic powder': 'garlic-powder', 'black pepper': 'black-pepper',
                 'oregano': 'oregano', 'onion powder': 'onion-powder', 'thyme': 'thyme', 'cumin': 'cumin', 'coriander': 'coriander-seed',
                 'smoked paprika': 'smoked-paprika', 'brown sugar': 'brown-sugar', 'salt': 'salt',
                 'mustard powder': 'mustard-powder', 'chilli': 'cayenne',
                 'turmeric': 'turmeric', 'ginger': 'ground-ginger', 'fenugreek': 'fenugreek', 'cinnamon': 'cinnamon',
                 'cardamom': 'cardamom', 'clove': 'cloves', 'nutmeg': 'nutmeg', 'mild chilli powder': 'chili-powder',
                 'rosemary': 'rosemary', 'savory': 'savory', 'allspice': 'allspice', 'star anise': 'star-anise',
                 'sumac': 'sumac', 'toasted sesame': 'sesame', 'cayenne': 'cayenne', 'fennel seed': 'fennel-seed',
                 'black pepper': 'black-pepper', 'Sichuan pepper': 'sichuan-pepper', 'basil': 'basil-dried',
                 'hot paprika': 'hot-paprika',
                 'mustard seed': 'mustard-seed', 'coriander seed': 'coriander-seed', 'black peppercorns': 'black-pepper',
                 'dill seed': 'dill-seed', 'crumbled bay': 'bay-leaf', 'broken cinnamon': 'cinnamon',
                 'dried orange peel': 'orange-peel'}
        names = {'porkolt': 'Pörkölt blend', 'gyros': 'Gyros', 'grill-rub': 'Grill rub', 'curry': 'Curry powder',
                 'garam-masala': 'Garam masala', 'taco': 'Taco seasoning', 'herbes-de-provence': 'Herbes de Provence',
                 'gingerbread': 'Gingerbread spice', 'zaatar': "Za'atar", 'ras-el-hanout': 'Ras el hanout', 'cajun': 'Cajun',
                 'five-spice': 'Chinese five-spice', 'italian-herbs': 'Italian herbs', 'kolbasz': 'Kolbász (sausage) spice',
                 'pickling': 'Pickling spice (savanyúság)', 'mulled-wine': 'Mulled wine (forralt bor)'}
        diy = [c for c in DATA.classics if c['source'] == 'diy']
        self.assertEqual(len(diy), 16)
        for c in diy:
            start = body.index(f'**{names[c["id"]]}:**') + len(names[c['id']]) + 5
            text = re.sub(r'\s+', ' ', body[start:body.index('\n-', start) if '\n-' in body[start:] else len(body)])
            text = text.replace('whole —', '')
            text = re.sub(r'\([^)]*\)', '', text).split('.')[0]          # "(+ …)" extras and "(a GF one…)" asides
            text = text.split(' — ')[0]                                     # "— ground fine", "— about 2 tablespoons…"
            text = re.sub(r'\s+', ' ', text)
            got = {}
            for m in re.finditer(r'(\d+|½)\s+([^,]+?)(?=,|$)', text):
                n = 0.5 if m.group(1) == '½' else float(m.group(1))
                got[words[m.group(2).strip()]] = n
            self.assertEqual(got, {k: float(v) for k, v in c['parts'].items()}, c['id'])

    def test_food_icons_are_in_the_sprite(self):
        for f in DATA.foods.values():
            self.assertIn(spice_data._icon_id(f['icon']), SPRITE, f['id'])


class TheGuardsBite(unittest.TestCase):
    """Positive controls: each guard, given one break, names it."""

    def assertCaught(self, errors, needle):
        self.assertTrue(any(needle in e for e in errors), f'{needle!r} not in {errors[:5]}')

    def test_a_missing_pair(self):
        self.assertCaught(broken(lambda d: d.pairs.pop(('cinnamon', 'cloves'))), 'cinnamon + cloves missing')

    def test_a_missing_food_cell(self):
        self.assertCaught(broken(lambda d: d.spice_foods.pop(('cumin', 'pork'))), 'cumin × pork missing')

    def test_a_score_whose_sign_contradicts_its_reason(self):
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('cinnamon', 'cloves'), Cell(-2, 'classic-partners', where='x'))),
                          'does not fit reason classic-partners')

    def test_a_plus_three_without_its_note(self):
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('caraway', 'marjoram'), Cell(3, 'hungarian-heart', where='x'))),
                          'needs its own note')

    def test_an_unknown_reason(self):
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('caraway', 'marjoram'), Cell(1, 'yummy', where='x'))),
                          "unknown pair reason 'yummy'")

    def test_a_food_reason_on_a_pair(self):
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('caraway', 'marjoram'), Cell(1, 'lifts', where='x'))),
                          "unknown pair reason 'lifts'")

    def test_a_negative_pair_that_three_classics_hold(self):
        # black pepper and coriander sit together in gyros, garam masala, pickling, baharat…
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('black-pepper', 'coriander-seed'), Cell(-1, 'muddy', where='x'))),
                          'sit together in')

    def test_a_minus_three_that_a_classic_holds(self):
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('caraway', 'sweet-paprika'),
                                                               Cell(-3, 'two-leads', 'x', 'y', where='x'))),
                          'but a classic blend holds both')

    def test_a_degenerate_row(self):
        def flat(d):
            for o in d.profiles:
                if o != 'saffron':
                    d.pairs[tuple(sorted(('saffron', o)))] = Cell(0, 'strangers', where='x')
        self.assertCaught(broken(flat), 'every pair of saffron scores 0')

    def test_a_food_nobody_vouches_for(self):
        def drop(d):
            for (s, f), c in list(d.spice_foods.items()):
                if f == 'game' and c.score == 3:
                    d.spice_foods[(s, f)] = Cell(2, 'warms', where='x')
        self.assertCaught(broken(drop), 'jars score 3 with game')

    def test_a_catalogue_spice_without_a_profile(self):
        self.assertCaught(broken(lambda d: d.not_on_rack.pop('sea-salt')), 'catalogue spice sea-salt has no profile')

    def test_a_profile_out_of_range(self):
        self.assertCaught(broken(lambda d: d.profiles['cumin'].__setitem__('intensity', 9)), 'cumin: intensity must be')

    def test_a_classic_with_an_unknown_jar(self):
        self.assertCaught(broken(lambda d: d.classics[0]['parts'].__setitem__('unobtainium', 1)), 'unobtainium is not a rack jar')

    def test_an_unused_reason(self):
        self.assertCaught(broken(lambda d: d.reasons.__setitem__('spare', {'kind': 'pair', 'sign': '+',
                                                                            'en': '{a} {b}', 'hu': '{a} {b}'})),
                          'spare: never used')

    def test_the_loader_rejects_a_pair_stated_twice_and_a_wrong_block(self):
        tmp = REPO / 'engine/spices'
        import shutil, tempfile
        with tempfile.TemporaryDirectory() as t:
            dst = pathlib.Path(t) / 'spices'
            shutil.copytree(tmp, dst)
            (dst / 'pairs/warm--warm.yaml').write_text((dst / 'pairs/warm--warm.yaml').read_text() +
                                                        'ground-ginger:\n  cinnamon: [3, classic-partners, "a", "b"]\n')
            (dst / 'pairs/earthy--earthy.yaml').write_text((dst / 'pairs/earthy--earthy.yaml').read_text() +
                                                            'cumin:\n  cinnamon: [1, gentle-company]\n')
            d = spice_data.load(dst)
            errs = spice_data.validate(d, CAT)
            self.assertTrue(any('already stated' in e for e in errs), errs[:5])
            self.assertTrue(any('belongs in warm--earthy.yaml' in e for e in errs), errs[:5])


if __name__ == '__main__':
    unittest.main()
