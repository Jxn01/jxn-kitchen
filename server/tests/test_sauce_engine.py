"""The sauce engine (spec 2026-10-19 §5.2, §9): the physics, the virtual blend, the typed fallback, the seeds.

Phase 1 (physics — needs no pair cell): emulsions against the know-how's 250 ml per yolk, curdling, the starches, raw egg,
garlic in oil, the body classes of the know-how's béchamel, keeps, family detection; and every seed lands in its family,
body class and keeps class.
"""
import pathlib
import unittest

import yaml

from kitchen import catalogue, sauce_data, spice_data
from kitchen.sauce_engine import SauceEngine, SauceInputError, finding_ids
from kitchen.spice_engine import SpiceEngine

REPO = pathlib.Path(__file__).resolve().parents[2]
CAT = catalogue.load(REPO / 'catalogue')
SPICES = SpiceEngine(spice_data.load(REPO / 'engine/spices'), CAT)
DATA = sauce_data.load(REPO / 'engine/sauces')
ENG = SauceEngine(DATA, SPICES, CAT)
HEAT = ['Simmer it for 5 minutes, stirring.']


def L(iid, qty, unit):
    return {'id': iid, 'qty': qty, 'unit': unit}


def ids(e):
    return [f['id'] for f in e['findings']]


def stab(e, kind):
    return [s for s in e['stability'] if s['kind'] == kind]


class Units(unittest.TestCase):
    def test_grams_from_every_unit(self):
        e = ENG.evaluate([L('sunflower-oil', 1, 'tbsp'), L('sunflower-oil', 0, 'ml')][:1], [])
        self.assertAlmostEqual(e['lines'][0]['g'], 15 * 0.92, places=2)
        e = ENG.evaluate([L('milk', 2, 'dl'), L('butter', 30, 'g'), L('egg-yolk', 2, 'pcs'), L('salt', 1, 'tsp')], [])
        g = [ln['g'] for ln in e['lines']]
        self.assertAlmostEqual(g[0], 200 * 1.03, places=2)
        self.assertAlmostEqual(g[1], 30)
        self.assertAlmostEqual(g[2], 36)
        self.assertAlmostEqual(g[3], 5 * 1.14, places=2)

    def test_a_spice_line_weighs_its_teaspoons(self):
        e = ENG.evaluate([L('water', 1, 'dl'), {'spice': 'cumin', 'qty': 2, 'unit': 'tsp'}], [])
        self.assertAlmostEqual(e['lines'][1]['g'], 2 * SPICES.p['cumin']['g_per_tsp'])

    def test_bad_input_is_refused(self):
        for lines in ([L('unicorn-milk', 1, 'dl')], [L('milk', 1, 'cup')], [L('milk', 0, 'dl')], [L('milk', -1, 'dl')],
                      [L('milk', 1, 'dl')] * 25, [{'raw': 7}], [{'blend': 3, 'qty': 1, 'unit': 'tsp'}],
                      [{'spice': 'unobtainium', 'qty': 1, 'unit': 'tsp'}], [{'spice': 'cumin', 'qty': 1, 'unit': 'dl'}], []):
            with self.assertRaises(SauceInputError, msg=str(lines)[:80]):
                ENG.evaluate(lines, [])


class Emulsions(unittest.TestCase):
    def mayo(self, oil_ml):
        return ENG.evaluate([L('egg-yolk', 1, 'pcs'), L('sunflower-oil', oil_ml, 'ml'), L('lemon-juice', 1, 'tbsp'),
                             L('salt', 0.25, 'tsp')], [])

    def test_250_ml_on_a_yolk_holds_400_splits(self):
        """The know-how: about 200–250 ml of oil per yolk."""
        ok, over = self.mayo(250), self.mayo(400)
        self.assertEqual([s['level'] for s in stab(ok, 'emulsion')], ['ok'])
        self.assertIn('emulsion-ok', ids(ok))
        self.assertEqual([s['level'] for s in stab(over, 'emulsion')], ['warn'])
        self.assertIn('emulsion-split', ids(over))
        self.assertLess(over['score'], ok['score'])

    def test_a_second_yolk_or_mustard_makes_room(self):
        two = ENG.evaluate([L('egg-yolk', 2, 'pcs'), L('sunflower-oil', 400, 'ml'), L('lemon-juice', 1, 'tbsp')], [])
        self.assertEqual([s['level'] for s in stab(two, 'emulsion')], ['ok'])

    def test_raw_yolk_keeps_two_days(self):
        e = self.mayo(200)
        self.assertIn('raw-egg', ids(e))
        self.assertEqual(e['keeps']['class'], 'raw-egg')
        self.assertEqual(e['keeps']['days'], 2)
        self.assertEqual(e['family']['id'], 'mayonnaise')
        self.assertEqual(e['body']['class'], 'stiff')

    def test_hollandaise_warns_of_65_degrees_and_is_cooked(self):
        e = ENG.evaluate([L('egg-yolk', 2, 'pcs'), L('water', 2, 'tbsp'), L('butter', 150, 'g'), L('lemon-juice', 1, 'tbsp')],
                         ['Whisk the yolks over barely simmering water until thick.', 'Off the heat, whisk in the butter.'])
        self.assertIn('yolk-heat', ids(e))
        self.assertNotIn('raw-egg', ids(e))
        self.assertEqual(e['family']['id'], 'hollandaise')

    def test_a_vinaigrette_is_shaken_not_split(self):
        e = ENG.evaluate([L('olive-oil', 6, 'tbsp'), L('wine-vinegar', 2, 'tbsp'), L('mustard', 1, 'tsp'), L('salt', 0.25, 'tsp')], [])
        self.assertIn('vinaigrette', ids(e))
        self.assertNotIn('emulsion-split', ids(e))
        self.assertEqual(e['family']['id'], 'vinaigrette')
        self.assertEqual(e['body']['class'], 'thin')


class Curdling(unittest.TestCase):
    def test_yoghurt_lemon_and_a_boil_curdles(self):
        e = ENG.evaluate([L('yogurt', 200, 'g'), L('lemon-juice', 2, 'tbsp')], ['Bring it to the boil.'])
        self.assertEqual([s['level'] for s in stab(e, 'curdle')], ['warn'])
        self.assertIn('curdle-warn', ids(e))

    def test_cream_of_30_percent_never_curdles(self):
        e = ENG.evaluate([L('cream-whipping', 2, 'dl'), L('lemon-juice', 2, 'tbsp')], ['Bring it to the boil.'])
        self.assertEqual(stab(e, 'curdle'), [])

    def test_a_starch_halves_the_risk(self):
        e = ENG.evaluate([L('yogurt', 200, 'g'), L('lemon-juice', 2, 'tbsp'), L('rice-flour', 1, 'tbsp')], ['Bring it to the boil.'])
        self.assertEqual([s['level'] for s in stab(e, 'curdle')], ['at-limit'])
        self.assertIn('curdle-notice', ids(e))

    def test_no_heat_no_curdling(self):
        e = ENG.evaluate([L('yogurt', 200, 'g'), L('lemon-juice', 2, 'tbsp')], ['Stir and chill.'])
        self.assertEqual(stab(e, 'curdle'), [])

    def test_hungarian_heat_words_count(self):
        e = ENG.evaluate([L('yogurt', 200, 'g'), L('lemon-juice', 2, 'tbsp')], ['Forrald fel.'])
        self.assertIn('curdle-warn', ids(e))


class Starches(unittest.TestCase):
    def test_potato_starch_and_a_long_simmer(self):
        e = ENG.evaluate([L('water', 5, 'dl'), L('potato-starch', 1, 'tbsp')], ['Simmer it for 20 minutes.'])
        self.assertIn('starch-long-boil', ids(e))
        short = ENG.evaluate([L('water', 5, 'dl'), L('potato-starch', 1, 'tbsp')], ['Simmer it for 2 minutes.'])
        self.assertNotIn('starch-long-boil', ids(short))

    def test_arrowroot_with_dairy(self):
        e = ENG.evaluate([L('milk', 5, 'dl'), L('arrowroot', 1, 'tbsp')], HEAT)
        self.assertIn('starch-arrowroot-dairy', ids(e))

    def test_cornstarch_in_acid(self):
        e = ENG.evaluate([L('water', 1, 'dl'), L('vinegar', 4, 'tbsp'), L('cornstarch', 1, 'tbsp')], HEAT)
        self.assertIn('starch-corn-acid', ids(e))

    def test_a_starch_that_never_cooks(self):
        e = ENG.evaluate([L('milk', 5, 'dl'), L('cornstarch', 2, 'tbsp')], ['Stir it in.'])
        self.assertIn('starch-raw', ids(e))
        self.assertEqual(e['body']['class'], 'thin')
        self.assertNotIn('starch-raw', ids(ENG.evaluate([L('milk', 5, 'dl'), L('xanthan', 0.25, 'tsp')], [])))   # xanthan works cold

    def test_wheat_flour_thickens_but_gets_no_starch_tip(self):
        e = ENG.evaluate([L('butter', 30, 'g'), L('wheat-flour', 3, 'tbsp'), L('milk', 5, 'dl')], HEAT)
        self.assertEqual(e['body']['class'], 'coats')
        self.assertFalse([f for f in ids(e) if f.startswith('starch-')])


class Body(unittest.TestCase):
    def bechamel(self, g):
        return ENG.evaluate([L('butter', g, 'g'), L('rice-flour', g / 10, 'tbsp'), L('milk', 5, 'dl')], HEAT)

    def test_the_know_how_bechamel(self):
        """30 g + 30 g + 500 ml coats a spoon; 40 + 40 is the thicker one (croquettes); 20 + 20 the thinner (lasagne)."""
        self.assertEqual(self.bechamel(30)['body']['class'], 'coats')
        self.assertEqual(self.bechamel(40)['body']['class'], 'thick')
        self.assertEqual(self.bechamel(20)['body']['class'], 'coats')
        self.assertLess(self.bechamel(20)['body']['index'], self.bechamel(30)['body']['index'])

    def test_a_reduction_says_it_depends(self):
        e = ENG.evaluate([L('red-wine', 2, 'dl'), L('shallot', 1, 'pcs')], ['Reduce it by half.'])
        self.assertIn('body-reduce', ids(e))
        self.assertTrue(e['body']['reduce'])


class GarlicInOil(unittest.TestCase):
    def test_fresh_garlic_in_oil_is_a_safety_warning(self):
        e = ENG.evaluate([L('olive-oil', 1, 'dl'), L('garlic', 3, 'pcs')], [])
        self.assertIn('garlic-in-oil', ids(e))
        self.assertEqual([s['level'] for s in stab(e, 'garlic-in-oil')], ['warn'])
        self.assertEqual(e['keeps']['class'], 'oil-infusion')

    def test_acid_or_cooking_makes_it_safe(self):
        self.assertNotIn('garlic-in-oil', ids(ENG.evaluate([L('olive-oil', 1, 'dl'), L('garlic', 3, 'pcs'),
                                                            L('lemon-juice', 3, 'tbsp')], [])))
        self.assertNotIn('garlic-in-oil', ids(ENG.evaluate([L('olive-oil', 1, 'dl'), L('garlic', 3, 'pcs')], HEAT)))


class Keeps(unittest.TestCase):
    def test_the_shortest_class_wins_and_acid_lifts_fresh_things(self):
        sharp = ENG.evaluate([L('wine-vinegar', 4, 'tbsp'), L('olive-oil', 4, 'tbsp'), L('shallot', 1, 'pcs')], [])
        self.assertEqual(sharp['keeps']['class'], 'acid-preserved')
        dairy = ENG.evaluate([L('wine-vinegar', 4, 'tbsp'), L('sour-cream', 2, 'dl'), L('shallot', 1, 'pcs')], [])
        self.assertEqual(dairy['keeps']['class'], 'fresh-dairy')


class TheTypedFallback(unittest.TestCase):
    def test_an_unmatched_line_counts_for_nothing_and_says_so(self):
        base = [L('milk', 5, 'dl'), L('butter', 30, 'g')]
        with_raw = ENG.evaluate(base + [{'raw': 'egy marék titok'}], [])
        without = ENG.evaluate(base, [])
        self.assertEqual(with_raw['taste'], without['taste'])
        self.assertEqual(with_raw['body'], without['body'])
        self.assertIn('unknown-line', ids(with_raw))
        line = next(f for f in with_raw['findings'] if f['id'] == 'unknown-line')
        self.assertIn('egy marék titok', line['hu'])

    def test_a_catalogue_item_off_the_shelves_counts_for_gluten_only(self):
        e = ENG.evaluate([L('milk', 5, 'dl'), {'item': 'carp', 'name': 'ponty', 'qty': 1, 'unit': 'pcs'}], [])
        self.assertIn('off-shelf', ids(e))


class TheSpicesInASauce(unittest.TestCase):
    def test_spices_raise_the_aromatic_axis_by_their_share(self):
        base = [L('yogurt', 300, 'g')]
        plain = ENG.evaluate(base, [])
        spiced = ENG.evaluate(base + [{'spice': 'cumin', 'qty': 1, 'unit': 'tsp'}, {'spice': 'coriander-seed', 'qty': 2, 'unit': 'tsp'}], [])
        self.assertGreater(spiced['taste']['aromatic'], plain['taste']['aromatic'])

    def test_a_dual_spice_brings_its_heat_once(self):
        """Hot paprika on the heat shelf: its per100 heat counts; the virtual blend adds aroma only (never heat again)."""
        e = ENG.evaluate([L('water', 5, 'dl'), L('hot-paprika', 1, 'tsp')], [])
        g = 5 * 0.46
        want = (4 * g / (500 + g)) / sauce_data_full('heat')
        self.assertAlmostEqual(e['taste']['heat'], round(min(1, want), 3), places=3)

    def test_a_blend_line_is_its_parts(self):
        blend = {'blend': 7, 'name': 'Pörkölt', 'parts': [['sweet-paprika', 4], ['caraway', 1]], 'qty': 1, 'unit': 'tbsp'}
        e = ENG.evaluate([L('water', 3, 'dl'), blend], [])
        self.assertAlmostEqual(e['lines'][1]['g'], 3 * (0.8 * 2.3 + 0.2 * SPICES.p['caraway']['g_per_tsp']), places=1)


def sauce_data_full(axis):
    from kitchen.sauce_engine import FULL
    return FULL[axis]


class TheSeedsPhysics(unittest.TestCase):
    """Calibration, phase 1: each seed lands in its family, body class and keeps class (spec §9)."""

    def test_every_seed(self):
        for c in DATA.classics:
            with self.subTest(c['id']):
                e = ENG.evaluate(ENG.seed_lines(c), c['steps']['en'])
                self.assertEqual(e['family']['id'], c['family'])
                self.assertEqual(e['body']['class'], c['expected']['body'])
                self.assertEqual(e['keeps']['class'], c['expected']['keeps'])

    def test_every_seed_in_hungarian_steps_too(self):
        for c in DATA.classics:
            with self.subTest(c['id']):
                e = ENG.evaluate(ENG.seed_lines(c), c['steps']['hu'])
                self.assertEqual(e['family']['id'], c['family'])
                self.assertEqual(e['body']['class'], c['expected']['body'])


class TheSeedsLedger(unittest.TestCase):
    """Calibration, phase 2: each seed reads its word with exactly its findings — from English and Hungarian steps alike."""

    def test_every_seed_reads_its_word_with_exactly_its_findings(self):
        for c in DATA.classics:
            for lang in ('en', 'hu'):
                with self.subTest(f"{c['id']} ({lang})"):
                    e = ENG.evaluate(ENG.seed_lines(c), c['steps'][lang])
                    self.assertEqual(e['word'], c['expected']['word'])
                    self.assertEqual(finding_ids(e), sorted(c['expected']['findings']))

    def test_every_seed_is_good_or_sings(self):
        for c in DATA.classics:
            self.assertGreaterEqual(ENG.evaluate(ENG.seed_lines(c), c['steps']['en'])['score'], 60, c['id'])


BAD = yaml.safe_load((pathlib.Path(__file__).parent / 'fixtures/bad_sauces.yaml').read_text())['bad']


class BadSauces(unittest.TestCase):
    def test_each_fails_for_its_reason(self):
        self.assertGreaterEqual(len(BAD), 6)
        for b in BAD:
            with self.subTest(b['id']):
                e = ENG.evaluate(b['lines'], b['steps'])
                self.assertLess(e['score'], 40, b['why'])
                for fid in b['findings']:
                    self.assertIn(fid, ids(e))

    def test_too_salty_grows_with_the_salt(self):
        def bech(tsp):
            return ENG.evaluate([L('butter', 30, 'g'), L('rice-flour', 3, 'tbsp'), L('milk', 5, 'dl'), L('salt', tsp, 'tsp')], HEAT)
        w = [next((f['weight'] for f in bech(t)['findings'] if f['id'] == 'too-salty'), 0) for t in (0.5, 2, 4, 9)]
        self.assertEqual(w[0], 0)
        self.assertTrue(w[1] > w[2] > w[3] >= -40, w)


class TheLedger(unittest.TestCase):
    CASES = [(ENG.seed_lines(c), c['steps']['en']) for c in DATA.classics] + [(b['lines'], b['steps']) for b in BAD]

    def test_the_ledger_is_the_score(self):
        for lines, steps in self.CASES:
            e = ENG.evaluate(lines, steps)
            self.assertEqual(e['score'], max(0, min(100, e['base'] + sum(f['weight'] for f in e['findings']))))

    def test_every_line_in_both_languages(self):
        for lines, steps in self.CASES:
            e = ENG.evaluate(lines, steps)
            for f in [*e['findings'], *e['stability'], *e['fixes'], e['keeps'], e['body']]:
                self.assertTrue(f['en'].strip() and f['hu'].strip(), f)
                self.assertNotIn('{', f['en'] + f['hu'])
            for food in e['foods']:
                for v in food['vouchers']:
                    self.assertTrue(v['en'] and v['hu'])

    def test_scale_and_order_do_not_change_the_verdict(self):
        for c in DATA.classics:
            lines = ENG.seed_lines(c)
            base = ENG.evaluate(lines, c['steps']['en'])
            double = ENG.evaluate([dict(ln, qty=ln['qty'] * 2) for ln in lines], c['steps']['en'])
            backwards = ENG.evaluate(list(reversed(lines)), c['steps']['en'])
            self.assertEqual(finding_ids(double), finding_ids(base), c['id'])
            self.assertEqual(double['body']['class'], base['body']['class'], c['id'])
            self.assertEqual(finding_ids(backwards), finding_ids(base), c['id'])
            self.assertEqual(backwards['score'], base['score'], c['id'])


class ThePairs(unittest.TestCase):
    def test_cumin_and_coriander_in_a_sauce_earn_their_line(self):
        """Spec §9: the spices of a sauce evaluate as one virtual blend; its pair lines join at half weight."""
        e = ENG.evaluate([L('yogurt', 300, 'g'), {'spice': 'cumin', 'qty': 1, 'unit': 'tsp'},
                          {'spice': 'coriander-seed', 'qty': 2, 'unit': 'tsp'}], [])
        self.assertIn('pair:coriander-seed+cumin', ids(e))

    def test_two_drivers_are_judged_once_by_the_sauce_matrix(self):
        """Sweet paprika and black pepper are both rack jars and drivers: one line, from the sauce matrix."""
        # positive control: on their own, the spice engine gives this pair a line of its own…
        spice = SPICES.evaluate([('sweet-paprika', 2), ('black-pepper', 1)])
        self.assertIn('pair:black-pepper+sweet-paprika', [f['id'] for f in spice['findings']])
        # …in a sauce where the sour cream leads, the sauce matrix's weight for it is under a line, so the only way it
        # could appear is the spice engine's copy — which is dropped
        e = ENG.evaluate([L('sour-cream', 2, 'dl'), L('sweet-paprika', 2, 'tsp'), L('black-pepper', 1, 'tsp')], [])
        self.assertNotIn('pair:black-pepper+sweet-paprika', ids(e))
        edges = [x for x in e['web']['edges'] if {x['a'], x['b']} == {'sweet-paprika', 'black-pepper'}]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['reason'], DATA.pair('black-pepper', 'sweet-paprika').reason)

    def test_a_pairs_as_line_is_named_as_itself(self):
        """Greek yoghurt pairs as yoghurt, but the sentence names Greek yoghurt."""
        e = ENG.evaluate([L('greek-yogurt', 300, 'g'), L('chives', 4, 'tbsp'), L('salt', 0.5, 'tsp')], [])
        edge = next(x for x in e['web']['edges'] if {x['a'], x['b']} == {'greek-yogurt', 'chives'})
        self.assertIn('greek', edge['en'].lower())
        self.assertIn('görög', edge['hu'].lower())
        self.assertIn('greek-yogurt', [n['id'] for n in e['web']['nodes']])

    def test_foods_are_led_by_the_drivers(self):
        teriyaki = next(c for c in DATA.classics if c['id'] == 'teriyaki')
        top = [f['id'] for f in ENG.evaluate(ENG.seed_lines(teriyaki), teriyaki['steps']['en'])['foods'][:3]]
        self.assertTrue(set(top) <= {'pork', 'chicken', 'fish', 'beef', 'rice'}, top)
        bech = next(c for c in DATA.classics if c['id'] == 'bechamel')
        self.assertNotIn('pickles', [f['id'] for f in ENG.evaluate(ENG.seed_lines(bech), bech['steps']['en'])['foods'][:3]])


if __name__ == '__main__':
    unittest.main()
