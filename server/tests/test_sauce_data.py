"""The sauce engine's knowledge: the loader and the validator, and the guards bite.

First against a tiny fixture shelf written here (three drivers, two structural items, two foods) — every rule with a
positive control: a copy broken in exactly one way must fail with a message naming the break. The real knowledge is
checked by TheRealKnowledge.
"""
import copy
import itertools
import pathlib
import tempfile
import types
import unittest

import yaml

from kitchen import catalogue, sauce_data, spice_data
from kitchen.spice_data import Cell

REPO = pathlib.Path(__file__).resolve().parents[2]
CAT = catalogue.load(REPO / 'catalogue')
SPICES = spice_data.load(REPO / 'engine/spices')

BI = {'en': 'x', 'hu': 'x'}


def _meta():
    lab = lambda ids: [{'id': i, 'en': i, 'hu': i} for i in ids]
    keeps = [{'id': k, 'en': k, 'hu': k, 'days': d} for k, d in zip(sauce_data.KEEPS, (2, 3, 4, 4, 5, 14, 30))]
    return {'shelves': lab(sauce_data.SHELVES), 'roles': lab(sauce_data.ROLES), 'taste': lab(sauce_data.TASTE),
            'units': lab(sauce_data.UNITS), 'keeps': keeps, 'chips': lab(sauce_data.CHIPS),
            'body': lab(('thin', 'coats', 'thick', 'stiff')), 'stability': lab(('emulsion', 'curdle', 'starch', 'raw-egg', 'garlic-in-oil')),
            'words': [{'id': w, 'min': m, 'mascot': 'happy', 'en': w, 'hu': w} for w, m in (('sings', 80), ('good', 60), ('muddled', 40), ('fighting', 0))],
            'heat': [{'id': h, 'below': b, 'en': h, 'hu': h} for h, b in (('mild', .4), ('warm', 1), ('hot', 1.8), ('fiery', 99))]}


def _ing(iid, role, shelf, driver, **kw):
    e = {'id': iid, 'role': role, 'driver': driver, 'shelf': shelf, 'unit': 'tbsp', 'default': 1, 'step': 1, 'alt': ['ml'],
         'g_per_ml': 1.0, 'per100': {a: 0 for a in sauce_data.TASTE}, 'body': {'method': 'none', 'power': 0},
         'stability': {'emulsifier_ml': 0, 'curdles': False, 'starch': 'none'}, 'keeps': 'dry-stable', 'fill': '#EEEEEE'}
    e['per100']['acid'] = 5
    e.update(kw)
    return e


def tiny():
    return {
        'meta.yaml': _meta(),
        'ingredients.yaml': {'ingredients': [
            _ing('olive-oil', 'fat', 'fats', False, keeps='dry-stable'),
            _ing('lemon-juice', 'acid', 'acids', True, keeps='acid-preserved'),
            _ing('vinegar', 'acid', 'acids', True, keeps='acid-preserved'),
            _ing('egg-yolk', 'egg', 'dairy-eggs', False, item='eggs', unit='pcs', alt=[], g_per_pc=18, default=1,
                 body={'method': 'liaison', 'power': 216}, stability={'emulsifier_ml': 250, 'curdles': False, 'starch': 'none'},
                 keeps='raw-egg'),
            _ing('garlic', 'allium', 'alliums', True, unit='pcs', alt=[], g_per_pc=4, keeps='fresh'),
            _ing('wheat-flour', 'thickener', 'thickeners', False, offer=False, body={'method': 'roux', 'power': 28},
                 stability={'emulsifier_ml': 0, 'curdles': False, 'starch': 'wheat'}),
        ]},
        'reasons.yaml': {
            'classic-partners': {'kind': 'pair', 'sign': '+', 'en': '{a} and {b}.', 'hu': '{a} és {b}.'},
            'strangers': {'kind': 'pair', 'sign': '0', 'en': '{a}, {b}.', 'hu': '{a}, {b}.'},
            'dresses': {'kind': 'food', 'sign': '+', 'en': '{s} dresses {f}.', 'hu': '{s}: {f}.'},
            'not-for': {'kind': 'food', 'sign': '0', 'en': '{s} not {f}.', 'hu': '{s} nem {f}.'},
        },
        'pairs/acids--acids.yaml': {'lemon-juice': {'vinegar': [0, 'strangers']}},
        'pairs/acids--alliums.yaml': {'lemon-juice': {'garlic': [3, 'classic-partners', 'Bright and bold.', 'Élénk.']},
                                      'vinegar': {'garlic': [2, 'classic-partners']}},
        'driver_foods/acids.yaml': {'lemon-juice': {'fish': [3, 'dresses'], 'pork': [1, 'dresses']},
                                    'vinegar': {'fish': [2, 'dresses'], 'pork': [0, 'not-for']}},
        'driver_foods/alliums.yaml': {'garlic': {'fish': [2, 'dresses'], 'pork': [3, 'dresses']}},
        'foods.yaml': {'foods': [{'id': 'fish', 'icon': 'om:1F41F', 'en': 'Fish', 'hu': 'Hal', 'say': BI},
                                 {'id': 'pork', 'icon': 'om:1F416', 'en': 'Pork', 'hu': 'Sertés', 'say': BI}]},
        'families.yaml': {'families': [
            {'id': 'dressings', 'en': 'Dressings', 'hu': 'Öntetek', 'parent': None, 'vessel': 'bottle', 'chip': 'dressings',
             'detect': {'any_child': True}},
            {'id': 'vinaigrette', 'en': 'Vinaigrette', 'hu': 'Vinaigrette', 'parent': 'dressings', 'vessel': 'bottle',
             'chip': 'dressings', 'body': 'thin', 'detect': {'all': ['role:fat', 'role:acid'], 'none': ['emulsion']}},
        ]},
        'classics.yaml': {'classics': [
            {'id': 'vinaigrette', 'en': 'Vinaigrette', 'hu': 'Vinaigrette', 'family': 'vinaigrette', 'yield_ml': 120,
             'ingredients': [{'id': 'olive-oil', 'qty': 6, 'unit': 'tbsp'}, {'id': 'vinegar', 'qty': 2, 'unit': 'tbsp'},
                             {'spice': 'black-pepper', 'qty': 0.25, 'unit': 'tsp'}],
             'steps': {'en': ['Shake.'], 'hu': ['Rázd össze.']},
             'expected': {'word': 'good', 'body': 'thin', 'keeps': 'acid-preserved', 'gluten': 'gf', 'findings': []}},
        ]},
        'findings.yaml': {**{k: BI for k in sauce_data.FINDING_KEYS},
                          'fixes': {k: {**BI, 'label': BI} for k in sauce_data.FIXES},
                          'heat': {k: BI for k in ('mild', 'warm', 'hot', 'fiery')},
                          'body': {k: BI for k in ('thin', 'coats', 'thick', 'stiff')}},
    }


def write(files, root):
    for name, doc in files.items():
        p = pathlib.Path(root) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))


def load_tiny(files=None):
    tmp = tempfile.mkdtemp(prefix='sauces-')
    write(files or tiny(), tmp)
    return sauce_data.load(tmp, pathlib.Path(tmp) / 'foods.yaml')


TINY = load_tiny()
NO_DUALS = types.SimpleNamespace(profiles={**{d: {} for d in sauce_data.DUALS}, 'cumin': {}, 'black-pepper': {}})


def problems(data, spices=None):
    return sauce_data.validate(data, CAT, spices)


def broken(mutate, spices=None):
    d = copy.deepcopy(TINY)
    mutate(d)
    return problems(d, spices)


def broken_files(mutate):
    files = tiny()
    mutate(files)
    return problems(load_tiny(files))


class TheTinyShelfValidates(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(problems(TINY), [])

    def test_loaded_shapes(self):
        self.assertEqual(TINY.drivers(), ['lemon-juice', 'vinegar', 'garlic'])
        self.assertEqual(len(TINY.pairs), 3)
        self.assertEqual(TINY.pair('garlic', 'lemon-juice').score, 3)
        self.assertEqual(len(TINY.driver_foods), 6)
        self.assertEqual(sauce_data.say(TINY, CAT, 'egg-yolk', 'en'), 'eggs')


class TheGuardsBite(unittest.TestCase):
    def assertCaught(self, errors, *needles):
        joined = '\n'.join(errors)
        for n in needles:
            self.assertIn(n, joined)

    def test_a_missing_pair(self):
        self.assertCaught(broken(lambda d: d.pairs.pop(('garlic', 'vinegar'))), 'vinegar + garlic missing', 'acids--alliums.yaml')

    def test_a_missing_food_cell(self):
        self.assertCaught(broken(lambda d: d.driver_foods.pop(('garlic', 'pork'))), 'garlic × pork missing')

    def test_a_structural_item_in_the_pairs(self):
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('lemon-juice', 'olive-oil'), Cell(1, 'classic-partners', where='x'))),
                          'olive-oil is not a driver')

    def test_a_structural_item_meeting_the_foods(self):
        self.assertCaught(broken(lambda d: d.driver_foods.__setitem__(('olive-oil', 'fish'), Cell(1, 'dresses', where='x'))),
                          'olive-oil is not a driver')

    def test_unknown_reason_and_wrong_sign(self):
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('garlic', 'vinegar'), Cell(2, 'nope', where='w'))), 'unknown pair reason')
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('garlic', 'vinegar'), Cell(-2, 'classic-partners', where='w'))),
                          'does not fit reason')

    def test_a_plus_three_without_its_note(self):
        self.assertCaught(broken(lambda d: d.pairs.__setitem__(('garlic', 'lemon-juice'), Cell(3, 'classic-partners', where='w'))),
                          'needs its own note')

    def test_a_negative_food_score(self):
        self.assertCaught(broken(lambda d: d.driver_foods.__setitem__(('garlic', 'fish'), Cell(-1, 'not-for', where='w'))),
                          'food score must be 0..3')

    def test_a_flat_row(self):
        def flat(d):
            for f in d.foods:
                d.driver_foods[('garlic', f)] = Cell(2, 'dresses', where='w')
        self.assertCaught(broken(flat), 'every food of garlic scores 2')

    def test_a_gluten_item_offered_on_a_shelf(self):
        self.assertCaught(broken(lambda d: d.ingredients['wheat-flour'].pop('offer')), 'contains gluten — it may be typed')

    def test_offer_false_on_a_gf_item(self):
        self.assertCaught(broken(lambda d: d.ingredients['vinegar'].__setitem__('offer', False)), 'only a gluten-containing item')

    def test_per100_body_stability_keeps_fill(self):
        self.assertCaught(broken(lambda d: d.ingredients['vinegar']['per100'].pop('umami')), 'per100 must give each')
        self.assertCaught(broken(lambda d: d.ingredients['vinegar'].__setitem__('body', {'method': 'roux', 'power': 0})),
                          'body method roux with power 0')
        self.assertCaught(broken(lambda d: d.ingredients['vinegar']['stability'].__setitem__('starch', 'glue')), 'stability must be')
        self.assertCaught(broken(lambda d: d.ingredients['vinegar'].__setitem__('keeps', 'forever')), 'keeps must be one of')
        self.assertCaught(broken(lambda d: d.ingredients['vinegar'].__setitem__('fill', 'red')), 'fill must be #RRGGBB')

    def test_units(self):
        self.assertCaught(broken(lambda d: d.ingredients['vinegar'].__setitem__('unit', 'cup')), 'unit must be one of')
        self.assertCaught(broken(lambda d: d.ingredients['garlic'].pop('g_per_pc')), 'a pcs item needs g_per_pc')

    def test_not_a_catalogue_id(self):
        self.assertCaught(broken(lambda d: d.ingredients['egg-yolk'].__setitem__('item', 'dragon-egg')), 'dragon-egg is not a catalogue id')

    def test_pairs_as_only_the_three_and_only_onto_a_driver(self):
        def bad(d):
            d.ingredients['wine-vinegar'] = {**copy.deepcopy(d.ingredients['vinegar']), 'id': 'wine-vinegar', 'pairs_as': 'vinegar'}
        self.assertCaught(broken(bad), 'pairs_as is reserved')
        def onto_structural(d):
            d.ingredients['greek-yogurt'] = {**copy.deepcopy(d.ingredients['vinegar']), 'id': 'greek-yogurt', 'pairs_as': 'yogurt'}
        self.assertCaught(broken(onto_structural), 'pairs_as yogurt must be a driver of the same role')

    def test_a_rack_spice_that_is_not_dual(self):
        def cumin(d):
            d.ingredients['cumin'] = {**copy.deepcopy(d.ingredients['vinegar']), 'id': 'cumin', 'role': 'heat', 'shelf': 'heat'}
        self.assertCaught(broken(cumin, NO_DUALS), 'cumin is a rack spice — it enters a sauce through the spice engine')

    def test_the_dual_spices(self):
        errors = problems(TINY, NO_DUALS)
        self.assertIn('ingredients.yaml: the dual spice sweet-paprika is missing', errors)
        def aromatic(d):
            d.ingredients['black-pepper'] = {**copy.deepcopy(d.ingredients['vinegar']), 'id': 'black-pepper', 'role': 'heat',
                                             'shelf': 'heat'}
            d.ingredients['black-pepper']['per100']['aromatic'] = 4
        self.assertCaught(broken(aromatic, NO_DUALS), 'black-pepper: a dual spice is a driver with aromatic 0')

    def test_reasons(self):
        self.assertCaught(broken(lambda d: d.reasons.__setitem__('extra', {'kind': 'pair', 'sign': '+', 'en': '{a} {b}', 'hu': '{a} {b}'})),
                          'extra: never used')
        self.assertCaught(broken(lambda d: d.reasons['dresses'].__setitem__('hu', 'nincs jelölő')), 'must contain {s} and {f}')
        self.assertCaught(broken(lambda d: d.reasons['not-for'].__setitem__('sign', '-')), 'cannot be negative')

    def test_families(self):
        self.assertCaught(broken(lambda d: d.families[1]['detect']['all'].append('colour:red')), "predicate 'colour:red'")
        self.assertCaught(broken(lambda d: d.families[1]['detect']['all'].append('item:unicorn')), 'item:unicorn is not')
        self.assertCaught(broken(lambda d: d.families[1].__setitem__('vessel', 'cup')), 'vessel must be one of')
        self.assertCaught(broken(lambda d: d.families[1].__setitem__('parent', 'nobody')), 'parent nobody is not a family')
        self.assertCaught(broken(lambda d: d.families[1]['detect'].__setitem__('all', ['step:dance'])), 'step:dance is not')

    def test_classics(self):
        self.assertCaught(broken(lambda d: d.classics[0]['ingredients'].append({'id': 'wheat-flour', 'qty': 1, 'unit': 'tbsp'})),
                          'wheat-flour is not offered')
        self.assertCaught(broken(lambda d: d.classics[0]['ingredients'][1].__setitem__('unit', 'g')), "vinegar in 'g'")
        self.assertCaught(broken(lambda d: d.classics[0].pop('expected')), 'expected must be')
        self.assertCaught(broken(lambda d: d.classics[0]['steps']['hu'].append('Még egy.')), 'steps need the same number')
        self.assertCaught(broken(lambda d: d.classics[0].__setitem__('family', 'soup')), 'family soup is not')
        self.assertCaught(broken(lambda d: d.classics[0]['ingredients'].append({'spice': 'unobtainium', 'qty': 1, 'unit': 'tsp'}),
                                 NO_DUALS), 'unobtainium is not a rack jar')

    def test_findings(self):
        self.assertCaught(broken(lambda d: d.findings.pop('emulsion-split')), 'findings.yaml: emulsion-split needs en and hu')
        self.assertCaught(broken(lambda d: d.findings['fixes'].pop('lumpy')), 'fixes.lumpy needs a label')

    def test_meta(self):
        self.assertCaught(broken(lambda d: d.meta['shelves'].pop()), 'meta.yaml: shelves must be exactly')
        self.assertCaught(broken(lambda d: d.meta['keeps'][0].__setitem__('days', 0)), 'keeps raw-egg needs whole days')

    def test_files(self):
        """What only the loader sees: a block named after the wrong shelves, a cell in the wrong block, a pair twice."""
        def misnamed(f):
            f['pairs/alliums--acids.yaml'] = f.pop('pairs/acids--alliums.yaml')
        self.assertIn('name the earlier shelf first', '\n'.join(broken_files(misnamed)))
        def wrong_block(f):
            f['pairs/acids--acids.yaml']['lemon-juice']['garlic'] = [1, 'classic-partners']
        self.assertIn('belongs in acids--alliums.yaml', '\n'.join(broken_files(wrong_block)))
        def twice(f):
            f['pairs/acids--alliums.yaml']['garlic'] = {'vinegar': [2, 'classic-partners']}
        self.assertIn('this pair is already stated', '\n'.join(broken_files(twice)))
        def bad_cell(f):
            f['driver_foods/alliums.yaml']['garlic']['fish'] = [2]
        self.assertIn('a cell is [score, reason]', '\n'.join(broken_files(bad_cell)))


REAL = sauce_data.load(REPO / 'engine/sauces')
KNOWHOW = yaml.safe_load((REPO / 'knowhow/17-sauces.yaml').read_text())
PAGE = {pg['id']: pg for pg in KNOWHOW['pages']}


class TheRealKnowledge(unittest.TestCase):
    def test_validates_completely(self):
        self.assertEqual(sauce_data.validate(REAL, CAT, SPICES, complete=True), [])

    def test_every_pair_of_drivers_is_judged_once_and_every_driver_meets_every_food(self):
        drivers = REAL.drivers()
        self.assertEqual(len(REAL.pairs), 60 * 59 // 2)
        self.assertEqual(set(REAL.pairs), {tuple(sorted(p)) for p in itertools.combinations(drivers, 2)})
        self.assertEqual(set(REAL.driver_foods), {(d, f) for d in drivers if d not in sauce_data.NO_FOODS for f in REAL.foods})
        self.assertEqual(len(REAL.driver_foods), 59 * 25)

    def test_fifty_four_blocks_one_per_pair_of_driver_shelves(self):
        shelves = [s for s in sauce_data.SHELVES if any(REAL.ingredients[d]['shelf'] == s for d in REAL.drivers())]
        want = sorted(f'{a}--{b}' for i, a in enumerate(shelves) for b in shelves[i:]
                      if a != b or sum(REAL.ingredients[d]['shelf'] == a for d in REAL.drivers()) > 1)
        self.assertEqual(sorted(p.stem for p in (REPO / 'engine/sauces/pairs').glob('*.yaml')), want)
        self.assertEqual(len(want), 54)

    def test_sixty_drivers_and_the_three_pairs_as(self):
        self.assertEqual(len(REAL.drivers()), 60)
        self.assertEqual({i: e['pairs_as'] for i, e in REAL.ingredients.items() if e.get('pairs_as')}, sauce_data.PAIRS_AS)

    def test_the_dual_spices_are_the_specs_list(self):
        """Sweet, hot and smoked paprika, chilli flakes, cayenne, black and white pepper, mustard powder, salt,
        sugar, brown sugar, garlic powder, onion powder — and no other rack jar is a sauce ingredient."""
        self.assertEqual(set(sauce_data.DUALS), set(REAL.ingredients) & set(SPICES.profiles))

    def test_the_thickeners_are_the_know_how_table(self):
        """One source: each starch's power (grams per litre for a medium sauce) is the know-how table's tablespoons per
        litre (the middle of its range) times the entry's grams per tablespoon."""
        ids = {'Cornstarch': 'cornstarch', 'Potato starch': 'potato-starch', 'Tapioca starch': 'tapioca-starch',
               'Arrowroot': 'arrowroot', 'Rice flour': 'rice-flour', 'GF flour mix': 'gf-flour-mix'}
        items = PAGE['thickeners']['chart']['items']
        self.assertEqual(sorted(it['label']['en'] for it in items), sorted(ids))
        for it in items:
            e = REAL.ingredients[ids[it['label']['en']]]
            mid = (it['value'] + it.get('to', it['value'])) / 2
            self.assertAlmostEqual(e['body']['power'], mid * e['g_per_ml'] * 15, delta=1, msg=it['label']['en'])
        # xanthan: a quarter to half a teaspoon per litre (the table's footnote)
        self.assertIn('¼–½ teaspoon per litre', PAGE['thickeners']['en']['body'])
        x = REAL.ingredients['xanthan']
        self.assertAlmostEqual(x['body']['power'], 0.375 * x['g_per_ml'] * 5, delta=0.05)

    def test_the_fix_rows_are_the_know_how_picker_word_for_word(self):
        rows = PAGE['fixes']['chart']['items']
        fixes = REAL.findings['fixes']
        self.assertEqual(len(rows), 9)
        self.assertEqual(list(fixes), list(sauce_data.FIXES))
        for key, row in zip(sauce_data.FIXES, rows):
            self.assertEqual(fixes[key]['label'], row['label'], key)
            self.assertEqual({'en': fixes[key]['en'], 'hu': fixes[key]['hu']}, row['note'], key)

    def test_the_emulsion_constants_are_the_know_how(self):
        self.assertIn('200–250 ml oil per yolk', PAGE['emulsions']['en']['body'])
        self.assertEqual(REAL.ingredients['egg-yolk']['stability']['emulsifier_ml'], 250)
        self.assertIn('about 65 °C', PAGE['emulsions']['en']['body'])
        self.assertIn('65 °C', REAL.findings['yolk-heat']['en'])
        self.assertIn('65 °C', REAL.findings['yolk-heat']['hu'])

    def test_the_bechamel_seed_is_the_know_how_30_30_500(self):
        page = PAGE['bechamel']['en']['body']
        for want in ('30 g butter', '30 g rice flour (about 3 tablespoons)', '500 ml warm milk'):
            self.assertIn(want, page)
        seed = {ln.get('id'): ln for ln in next(c for c in REAL.classics if c['id'] == 'bechamel')['ingredients']}
        self.assertEqual((seed['butter']['qty'], seed['butter']['unit']), (30, 'g'))
        rf = REAL.ingredients['rice-flour']
        self.assertAlmostEqual(seed['rice-flour']['qty'] * 15 * rf['g_per_ml'], 30, delta=0.5)
        self.assertEqual((seed['milk']['qty'], seed['milk']['unit']), (5, 'dl'))

    def test_the_seeds_need_no_swap(self):
        for c in REAL.classics:
            for ln in c['ingredients']:
                e = REAL.ingredients.get(ln.get('id'), {})
                item = CAT.items.get(e.get('item', ln.get('id')) or ln.get('spice'))
                self.assertIsNotNone(item, f"{c['id']}: {ln}")
                self.assertNotEqual(item.gluten, 'contains', f"{c['id']}: {ln}")

    def test_every_family_seed_lands_in_a_family_of_the_tree(self):
        fids = {f['id'] for f in REAL.families}
        self.assertEqual({c['family'] for c in REAL.classics} - fids, set())
        self.assertEqual(len(REAL.classics), 12)


if __name__ == '__main__':
    unittest.main()
