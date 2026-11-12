"""The spice engine: calibration against the classics, the bad blends, and its properties."""
import pathlib
import random
import unittest

import yaml

from kitchen import catalogue, spice_data, spice_engine
from kitchen.spice_engine import EngineInputError, SpiceEngine, finding_ids

REPO = pathlib.Path(__file__).resolve().parents[2]
CAT = catalogue.load(REPO / 'catalogue')
DATA = spice_data.load(REPO / 'engine/spices')
ENG = SpiceEngine(DATA, CAT)
BAD = yaml.safe_load((pathlib.Path(__file__).parent / 'fixtures/bad_blends.yaml').read_text())


def ev(parts, **kw):
    return ENG.evaluate(list(parts.items()), **kw)


class Calibration(unittest.TestCase):
    def test_every_classic_reads_its_expected_word_and_exactly_its_findings(self):
        for c in DATA.classics:
            e = ev(c['parts'])
            with self.subTest(c['id']):
                self.assertIn(e['word'], ('sings', 'good'))
                self.assertEqual(e['word'], c['expected']['word'])
                self.assertEqual(finding_ids(e), sorted(c['expected']['findings']))

    def test_the_bad_blends_read_under_40_with_their_findings(self):
        for b in BAD:
            e = ev(b['parts'])
            with self.subTest(b['id']):
                self.assertLess(e['score'], 40)
                self.assertTrue(set(b['findings']) <= set(finding_ids(e)), finding_ids(e))

    def test_each_classic_is_its_own_nearest_at_100(self):
        for c in DATA.classics:
            e = ev(c['parts'])
            self.assertEqual((e['classics'][0]['id'], e['classics'][0]['similarity']), (c['id'], 100), c['id'])

    def test_a_classic_minus_its_smallest_spice_still_finds_itself_and_names_the_gap(self):
        for c in DATA.classics:
            if len(c['parts']) < 4:
                continue
            gone = min(c['parts'], key=lambda i: (c['parts'][i], list(c['parts']).index(i) * -1))
            parts = {k: v for k, v in c['parts'].items() if k != gone}
            near = ev(parts)['classics'][0]
            with self.subTest(c['id']):
                self.assertEqual(near['id'], c['id'])
                self.assertEqual(near['missing'], [gone])
                self.assertLess(near['similarity'], 100)

    def test_the_known_clashes_and_partnerships_show(self):
        self.assertIn('pair:cayenne+lavender', finding_ids(ev({'lavender': 1, 'cayenne': 1, 'thyme': 1})))
        self.assertIn('backbone:hungarian-base', finding_ids(ev({'sweet-paprika': 3, 'caraway': 1, 'marjoram': 1})))
        line = next(f for f in ev({'coriander-seed': 2, 'cumin': 1})['findings'] if f['id'] == 'pair:coriander-seed+cumin')
        self.assertEqual(line['kind'], 'good')
        self.assertIn('backbone of every curry', line['en'])
        self.assertIn('curry gerince', line['hu'])


class Properties(unittest.TestCase):
    def test_the_ledger_adds_up_to_the_score(self):
        rng = random.Random(7)
        jars = list(DATA.profiles)
        for _ in range(300):
            parts = {j: rng.choice((0.5, 1, 1, 2, 3, 4)) for j in rng.sample(jars, rng.randint(1, 16))}
            e = ev(parts)
            raw = 50 + sum(f['weight'] for f in e['findings'])
            self.assertEqual(e['score'], max(0, min(100, raw)), parts)
            self.assertTrue(0 <= e['score'] <= 100)
            for f in e['findings']:
                self.assertTrue(f['en'].strip() and f['hu'].strip(), f)
                self.assertTrue(set(f['about']) <= set(parts), f)
                self.assertIn(f['kind'], ('good', 'notice', 'warn', 'info'))

    def test_order_and_scale_change_nothing(self):
        c = next(c for c in DATA.classics if c['id'] == 'curry')
        a = ev(c['parts'])
        b = ENG.evaluate(list(reversed(list(c['parts'].items()))))
        x3 = ev({k: v * 3 for k, v in c['parts'].items()})
        for other in (b, x3):
            self.assertEqual((a['score'], finding_ids(a)), (other['score'], finding_ids(other)))
            self.assertEqual(a['radar'], other['radar'])
            self.assertEqual(a['jar_fill'], other['jar_fill'])

    def test_bad_input_is_refused(self):
        for parts in ([], [('cumin', 0)], [('cumin', -1)], [('cumin', float('nan'))], [('unobtainium', 1)],
                      [('cumin', 1), ('cumin', 2)], [(j, 1) for j in list(DATA.profiles)[:17]], [('cumin', True)]):
            with self.assertRaises(EngineInputError, msg=parts):
                ENG.evaluate(parts)

    def test_a_single_spice_evaluates(self):
        e = ev({'cumin': 1})
        self.assertIn('single-spice', finding_ids(e))
        self.assertEqual(e['web']['edges'], [])

    def test_the_shape_of_an_evaluation(self):
        e = ev({'sweet-paprika': 4, 'caraway': 1, 'marjoram': 1, 'garlic-powder': 1, 'black-pepper': 0.5})
        self.assertRegex(e['jar_fill'], r'^#[0-9A-F]{6}$')
        self.assertEqual(max(e['radar'].values()), 1.0)
        self.assertEqual(set(e['radar']), set(spice_data.AXES))
        self.assertEqual(len(e['web']['edges']), 10)
        self.assertEqual(e['foods'][0]['id'], 'pork')
        self.assertTrue(all(v['en'] and v['hu'] for f in e['foods'] for v in f['vouchers']))
        self.assertEqual([f['score'] for f in e['foods']], sorted((f['score'] for f in e['foods']), reverse=True))
        self.assertEqual(e['cuisines'][0]['id'], 'hungarian')
        self.assertEqual(e['batch']['tbsp'], 2.5)
        self.assertAlmostEqual(sum(g['tsp'] for g in e['batch']['grams']), 7.5)
        self.assertEqual(ev({'cumin': 1, 'coriander-seed': 2}, batch_tbsp=6)['batch']['tsp'], 18)
        self.assertIn(e['mascot'], ('proud', 'happy', 'think', 'worried'))

    def test_heat_words_climb_with_the_chilli(self):
        words = [ev({'sweet-paprika': 4, 'cayenne': n})['heat']['word'] for n in (0.05, 0.2, 0.5, 2)]
        self.assertEqual(words, ['mild', 'warm', 'hot', 'fiery'])

    def test_suggestions_never_clash_with_the_blend(self):
        e = ev({'lavender': 1, 'thyme': 1})
        for j in e['suggest']:
            self.assertGreater(min(DATA.pair(j, i).score for i in ('lavender', 'thyme')), -2, j)
            self.assertNotIn(j, ('lavender', 'thyme'))


if __name__ == '__main__':
    unittest.main()
