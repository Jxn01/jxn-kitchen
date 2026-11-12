"""The web tests' engine fixtures (web/tests/fixtures/engine-*.json), built from the real knowledge — one function,
used by scripts/engine-fixture.sh to write them and by test_engine_fixtures.py to prove they have not drifted."""
import pathlib

from kitchen import blends, catalogue, knowhow, sauce_data, sauce_engine, sauces, spice_data, spice_engine

REPO = pathlib.Path(__file__).resolve().parents[2]
BLENDS = {
    'porkolt': [('sweet-paprika', 4), ('caraway', 1), ('marjoram', 1), ('garlic-powder', 1), ('black-pepper', 0.5)],
    'curry': [('coriander-seed', 4), ('cumin', 2), ('turmeric', 2), ('ground-ginger', 1), ('fenugreek', 1), ('cinnamon', 0.5),
              ('cardamom', 0.5), ('cayenne', 0.5), ('black-pepper', 0.5)],
    'clash': [('lavender', 1), ('cayenne', 1), ('cumin', 1), ('cinnamon', 1)],
}


def build() -> dict:
    cat = catalogue.load(REPO / 'catalogue')
    eng = spice_engine.SpiceEngine(spice_data.load(REPO / 'engine/spices'), cat)
    lib = knowhow.load(REPO / 'knowhow')
    out = {'rack': blends.rack(eng, cat, lib)}
    empty = {'have': [], 'groups_some': [], 'staples_off': []}
    for name, parts in BLENDS.items():
        e = eng.evaluate(parts)
        e['gluten'] = blends.gluten_line(eng, cat, empty, [s for s, _ in parts])
        out[f'eval-{name}'] = e
    # the sauces: the shelves, two seeds and a sauce where everything fights (with a typed line nothing matched)
    sd = sauce_data.load(REPO / 'engine/sauces')
    se = sauce_engine.SauceEngine(sd, eng, cat)
    out['sauce-shelves'] = sauces.shelves(se, cat)
    for cid in SAUCES:
        c = next(x for x in sd.classics if x['id'] == cid)
        stored = sauces.classic_lines(sd, c)
        e = se.evaluate(sauces.engine_lines(None, stored), c['steps']['en'])
        e['gluten'] = sauces.gluten_lines(None, se, cat, empty, stored)
        out[f'sauce-{cid}'] = e
    stored = [{'shelf_id': i, 'item_id': sd.ingredients[i].get('item', i), 'spice_id': None, 'blend_id': None, 'raw': None,
               'qty': q, 'unit': u, 'name': i, 'ok_gf': False} for i, q, u in FIGHTS] + \
             [{'shelf_id': None, 'item_id': None, 'spice_id': None, 'blend_id': None, 'raw': 'egy marék titok', 'qty': None,
               'unit': None, 'name': 'egy marék titok', 'ok_gf': False}]
    e = se.evaluate(sauces.engine_lines(None, stored), ['Stir it together.'])
    e['gluten'] = sauces.gluten_lines(None, se, cat, empty, stored)
    out['sauce-fights'] = e
    return out


SAUCES = ('paprikas', 'mayonnaise')
FIGHTS = [('sour-cream', 2, 'dl'), ('fish-sauce', 2, 'tbsp'), ('balsamic', 3, 'tbsp'), ('tarragon', 3, 'tbsp'),
          ('peanut-butter', 3, 'tbsp'), ('coconut-milk', 1, 'dl')]
