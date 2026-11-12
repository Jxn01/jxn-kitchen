"""The know-how library (spec §6.8): the real content must validate — both languages on every page — and keep the
sections the spec lists, the celiac chapter included."""
import pathlib
import re

from kitchen import knowhow

REPO = pathlib.Path(__file__).resolve().parents[2]
LIB = knowhow.load(REPO / 'knowhow')
SPRITE = set(re.findall(r'<symbol id="i-([^"]+)"', (REPO / 'web/public/sprite.svg').read_text()))


def test_the_real_library_validates():
    assert knowhow.validate(LIB, SPRITE) == []


def test_every_section_the_spec_lists():
    # the spec's ten, plus the owner's spice blends (2026-10-11), placed right after spices
    # 2026-10-11: + the owner's know-how expansion (coffee, appliances, storage, eggs, grains, sauces, times, cheese),
    # ordered for the 5 x 4 home grid
    assert [s['id'] for s in LIB] == ['temperatures', 'times', 'methods', 'appliances', 'knife', 'cuts', 'eggs', 'grains', 'sauces', 'cheese', 'spices', 'blends', 'hungarian',
                                      'baking', 'coffee', 'storage', 'conversions', 'substitutions', 'celiac']
    for s in LIB:
        assert len(s['pages']) >= 2, s['id']


def test_the_celiac_chapter_covers_what_the_spec_names():
    celiac = {p['id'] for p in next(s for s in LIB if s['id'] == 'celiac')['pages']}
    assert {'hidden-gluten', 'labels', 'gf-flours', 'guests'} <= celiac


def test_food_safety_numbers_are_the_standard_ones():
    temps = next(s for s in LIB if s['id'] == 'temperatures')
    safety = next(p for p in temps['pages'] if p['id'] == 'food-safety')
    for lang in ('en', 'hu'):
        body = safety[lang]['body']
        for must in ('74 °C', '71 °C', '63 °C', '5', '60 °C'):
            assert must in body, (lang, must)


def test_may_contain_is_never_a_warning():
    """§7: 'may contain traces' is a faint note, never a gluten warning. The library says so, in both languages."""
    labels = next(p for p in next(s for s in LIB if s['id'] == 'celiac')['pages'] if p['id'] == 'labels')
    assert 'may contain' in labels['en']['body'].lower() and 'nyomokban' in labels['hu']['body'].lower()


def test_the_validator_bites():
    bad = [{'id': 'x', 'order': 1, 'icon': 'om:1F4D6', 'color': 'tomato', 'en': {'title': 'X', 'sub': 'x'},
            'hu': {'title': 'X', 'sub': 'x'}, 'pages': [{'id': 'p', 'illustration': 'nope',
                                                         'en': {'title': 'T', 'body': 'b' * 50}, 'hu': {'title': '', 'body': ''}}]}]
    errs = knowhow.validate(bad)
    assert any('illustration' in e for e in errs) and any('hu title or body' in e for e in errs)
    bad[0]['pages'][0]['open'] = 'cocktails'                     # a page may open only a real engine
    assert any('open must be one of' in e for e in knowhow.validate(bad))



def test_the_api_serves_the_library_with_an_etag(tmp_path):
    from fastapi.testclient import TestClient
    from kitchen.app import create_app
    from kitchen.config import Config
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REPO / 'catalogue')
    with TestClient(create_app(cfg, shopping_sync_every=None, timers_autorun=False, scans_autorun=False)) as c:
        r = c.get('/api/knowhow')
        assert r.status_code == 200 and [x['id'] for x in r.json()] == [x['id'] for x in LIB] and r.json()[-1]['id'] == 'celiac'
        assert c.get('/api/knowhow', headers={'If-None-Match': r.headers['etag']}).status_code == 304


def test_the_web_fixture_is_the_current_library():
    """web/tests/md.test.ts renders every real page from this fixture; it must not drift from knowhow/*.yaml.
    Regenerate with scripts/knowhow-fixture.sh."""
    import json
    fixture = json.loads((REPO / 'web/tests/fixtures/knowhow.json').read_text())
    assert fixture == knowhow.to_json(LIB), 'run scripts/knowhow-fixture.sh'


def test_section_colours_are_exactly_the_web_palette():
    # the server's list was a hand-copied subset and drifted (rust was missing, 2026-10-11)
    src = (REPO / 'web/src/lib/palette.ts').read_text()
    block = src[src.index('export const P = {'):src.index('} as const')]
    keys = set(re.findall(r"([a-z]+): '#", block)) - {'ink', 'cream'}
    assert set(knowhow.COLORS) == keys


# --- charts (server/kitchen/charts.py): one valid example per type, and each must bite on a broken copy ---
import copy  # noqa: E402

from kitchen import charts  # noqa: E402

GOOD = {
    'vessel': {'type': 'vessel', 'shape': 'jug', 'max': 500, 'unit': 'ml', 'ticks': [{'value': 100, 'label': '1 dl'}],
               'items': [{'value': 100, 'label': '1 dl', 'note': {'en': 'a decilitre', 'hu': 'egy deciliter'}},
                         {'value': 250, 'label': {'en': 'mug', 'hu': 'bögre'}, 'note': {'en': 'about 2.5 dl', 'hu': 'kb. 2,5 dl'},
                          'fill': '#E14B3B', 'icons': ['om:1F969']}]},
    'scale': {'type': 'scale', 'unit': '°C', 'min': -20, 'max': 100,
              'bands': [{'from': -20, 'to': 5, 'fill': 'sky', 'label': {'en': 'Cold', 'hu': 'Hideg'}, 'note': {'en': 'safe', 'hu': 'biztonságos'}, 'range': {'en': '5 °C or colder', 'hu': '5 °C vagy hidegebb'}},
                        {'from': 5, 'to': 60, 'fill': '#E14B3B', 'label': {'en': 'Danger', 'hu': 'Veszély'}, 'note': {'en': 'bacteria', 'hu': 'baktériumok'}}],
              'marks': [{'value': 74, 'label': '74'}]},
    'board': {'type': 'board', 'groups': [{'color': 'herb', 'icon': 'om:1F35A', 'label': {'en': 'Safe', 'hu': 'Biztonságos'}, 'items': [{'label': {'en': 'Rice', 'hu': 'Rizs'}, 'icon': 'om:1F35A'}]},
                                          {'color': 'tomato', 'label': {'en': 'Never', 'hu': 'Soha'}, 'note': {'en': 'gluten', 'hu': 'glutén'}, 'items': [{'label': {'en': 'Wheat', 'hu': 'Búza'}}]}]},
    'steps': {'type': 'steps', 'items': [{'label': {'en': f'S{i}', 'hu': f'L{i}'}, 'note': {'en': 'n', 'hu': 'm'}, 'time': '5 min'} for i in range(3)]},
    'bars': {'type': 'bars', 'unit': 'g', 'max': 200, 'items': [{'value': 55, 'label': {'en': 'Flour', 'hu': 'Liszt'}},
                                                               {'value': 90, 'to': 95, 'label': {'en': 'Sugar', 'hu': 'Cukor'}, 'fill': 'butter'}],
             'marker': {'value': 100, 'label': '100 g'}},
    'layers': {'type': 'layers', 'shape': 'cup', 'items': [
        {'label': 'Espresso', 'note': {'en': 'a shot', 'hu': 'egy adag'}, 'layers': [{'fill': '#5A3A22', 'part': 1, 'label': {'en': 'espresso', 'hu': 'eszpresszó'}}]},
        {'label': 'Cappuccino', 'note': {'en': 'thirds', 'hu': 'harmadok'}, 'value': '180 ml', 'layers': [
            {'fill': '#5A3A22', 'part': 1, 'label': {'en': 'espresso', 'hu': 'eszpresszó'}},
            {'fill': '#E9D8C0', 'part': 1, 'label': {'en': 'milk', 'hu': 'tej'}}, {'fill': '#FFFFFF', 'part': 1, 'label': {'en': 'foam', 'hu': 'hab'}}]}]},
    'matrix': {'type': 'matrix', 'levels': [{'en': 'no', 'hu': 'nem'}, {'en': 'works', 'hu': 'megy'}, {'en': 'best', 'hu': 'legjobb'}],
               'cols': [{'label': {'en': 'Kettle', 'hu': 'Vízforraló'}, 'icon': 'c:kettle', 'note': {'en': 'water', 'hu': 'víz'}},
                        {'label': {'en': 'Stove', 'hu': 'Tűzhely'}, 'note': {'en': 'everything', 'hu': 'minden'}}],
               'rows': [{'label': {'en': 'Tea', 'hu': 'Tea'}, 'cells': [2, 1]}, {'label': {'en': 'Soup', 'hu': 'Leves'}, 'cells': [0, 2]}]},
    'picker': {'type': 'picker', 'items': [{'label': {'en': 'Rice', 'hu': 'Rizs'}, 'icon': 'om:1F35A', 'note': {'en': 'n', 'hu': 'm'}},
                                           {'label': 'Quinoa', 'note': {'en': 'n', 'hu': 'm'}, 'value': '1 : 2'}]},
    'swatches': {'type': 'swatches', 'shape': 'jars', 'items': [{'fill': '#D6402E', 'label': 'Különleges', 'note': {'en': 'finest', 'hu': 'legfinomabb'}, 'heat': 0},
                                               {'fill': '#E0552F', 'label': 'Erős', 'note': {'en': 'hot', 'hu': 'csípős'}, 'heat': 4}]},
}
SPRITE_PLUS = SPRITE | {'om-1f969', 'om-1f35a', 'c-kettle'}


def test_every_chart_type_has_a_valid_example():
    assert set(GOOD) == set(charts.TYPES)
    for t, ch in GOOD.items():
        assert charts.validate('x/p', ch, knowhow.COLORS, SPRITE_PLUS) == [], t


def test_the_chart_validator_bites():
    """Positive controls: each breakage of a valid chart must be reported."""
    def broken(t, f):
        ch = copy.deepcopy(GOOD[t]); f(ch); return charts.validate('x/p', ch, knowhow.COLORS, SPRITE_PLUS)
    assert broken('vessel', lambda c: c['items'][1]['note'].pop('hu'))                      # a language missing
    assert broken('vessel', lambda c: c['items'][0].update(value=900))                      # beyond the vessel
    assert broken('vessel', lambda c: c.update(shape='bucket'))
    assert broken('vessel', lambda c: c['items'][1].update(icons=['om:ZZZZ']))              # not in the sprite
    assert broken('scale', lambda c: c['bands'][1].update(to=200))
    assert broken('scale', lambda c: c['bands'][0].update(fill='red'))                     # not palette, not hex
    assert broken('board', lambda c: c['groups'][0].update(color='#00FF00'))               # text sits on it: palette only
    assert broken('board', lambda c: c['groups'].pop())                                    # one group is not a board
    assert broken('steps', lambda c: c['items'].pop())                                     # fewer than three steps
    assert broken('bars', lambda c: c['items'][1].update(to=50))                           # to below value
    assert broken('swatches', lambda c: c['items'][0].update(heat=9))
    assert broken('swatches', lambda c: c.update(extra=1))                                 # unknown key
    assert broken('swatches', lambda c: c.update(shape='bowls'))
    assert broken('layers', lambda c: c['items'][1]['layers'][0].update(part=0))           # a layer of nothing
    assert broken('layers', lambda c: c['items'][0]['layers'].clear())                     # an item with no layers
    assert broken('layers', lambda c: c.update(shape='bucket'))
    assert broken('vessel', lambda c: c.update(shape='vase'))
    assert broken('matrix', lambda c: c['rows'][0]['cells'].append(1))                     # more cells than columns
    assert broken('matrix', lambda c: c['rows'][1].update(cells=[0, 3]))                    # no level 3
    assert broken('matrix', lambda c: c['levels'].pop())                                    # a level unnamed
    assert broken('matrix', lambda c: c['cols'][0].update(icon='c:nope'))                   # a drawing that is not in the sprite
    assert broken('picker', lambda c: c['items'][0].pop('note'))
    assert charts.validate('x/p', {'type': 'pie'}, knowhow.COLORS) != []


def test_a_page_has_an_illustration_or_a_chart_not_both():
    lib = copy.deepcopy(LIB)
    lib[0]['pages'][0]['chart'] = GOOD['steps']
    assert any('not both' in e for e in knowhow.validate(lib, SPRITE)) == bool(lib[0]['pages'][0].get('illustration'))


def test_chart_icons_reach_the_web_as_sprite_ids():
    out = charts.to_json(GOOD['vessel'])
    assert out['items'][1]['icons'] == ['om-1f969'] and out['items'][0]['label'] == '1 dl'
    assert charts.to_json(GOOD['matrix'])['cols'][0]['icon'] == 'c-kettle'
