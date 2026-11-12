"""Sauces: seeds, the shelves, typed lines, CRUD, riff, the gluten lines, events."""
import pathlib
import re
import time

import pytest
from fastapi.testclient import TestClient

from kitchen.app import create_app
from kitchen.config import Config

REAL = pathlib.Path(__file__).resolve().parents[2] / 'catalogue'
SERVER = pathlib.Path(__file__).resolve().parents[1] / 'kitchen'


def make(tmp_path):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL)
    return TestClient(create_app(cfg, shopping_sync_every=None, timers_autorun=False, scans_autorun=False))


@pytest.fixture
def c(tmp_path):
    with make(tmp_path) as client:
        yield client


VINAIGRETTE = [{'shelf': 'olive-oil', 'qty': 6, 'unit': 'tbsp'}, {'shelf': 'wine-vinegar', 'qty': 2, 'unit': 'tbsp'},
               {'shelf': 'salt', 'qty': 0.25, 'unit': 'tsp'}]


def by_classic(c, cid):
    return next(s for s in c.get('/api/sauces').json() if s['classic_id'] == cid)


def test_the_twelve_classics_are_seeded_once_in_a_lifetime(tmp_path):
    with make(tmp_path) as c:
        ss = c.get('/api/sauces').json()
        assert len(ss) == 12 and {s['origin'] for s in ss} == {'seed'}
        for s in ss:
            assert c.delete(f'/api/sauces/{s["id"]}').status_code == 204
        assert c.get('/api/sauces').json() == []
    with make(tmp_path) as c:
        assert c.get('/api/sauces').json() == []


def test_every_seed_reads_as_its_classic_and_its_gluten_line_is_honest(c):
    """The seeds need no swap; mayonnaise, vinaigrette and vadas carry mustard and read `check` until the user's own GF
    mustard is in the pantry (then `gf`, through `yours`) — exactly like a recipe."""
    data = c.app.state.sauces.data
    for cl in data.classics:
        s = by_classic(c, cl['id'])
        assert s['word'] == cl['expected']['word'], cl['id']
        assert s['family']['id'] == cl['family'], cl['id']
        assert s['gluten']['state'] == cl['expected']['gluten'], (cl['id'], s['gluten'])
    assert c.put('/api/pantry/mustard', json={'have': True}).status_code == 200
    assert by_classic(c, 'mayonnaise')['gluten']['state'] == 'gf'


def test_a_seed_speaks_both_languages_until_it_is_renamed(c):
    s = by_classic(c, 'paprikas')
    assert s['names'] == {'en': 'Paprikás sauce', 'hu': 'Paprikás mártás'}
    d = c.get(f'/api/sauces/{s["id"]}').json()
    assert d['steps']['hu'][1].startswith('A tűzről lehúzva') and len(d['steps']['en']) == len(d['steps']['hu'])
    assert d['method']['hu'].startswith('A tejföl előtt')
    assert d['evaluation']['family']['id'] == 'paprikas' and d['evaluation']['score'] == s['score']
    assert any(t for t in d['timers']['en'][0]), 'the 8–10 minutes of the first step is a timer chip'
    lines = [{k: ln[k] for k in ('qty', 'unit')} | {ln['kind']: ln[f'{ln["kind"]}_id']} for ln in d['lines']]
    renamed = c.put(f'/api/sauces/{s["id"]}', json={'name': 'Nagyi paprikása', 'lines': lines, 'steps': d['steps']['hu']}).json()
    assert renamed['names'] == {'en': 'Nagyi paprikása', 'hu': 'Nagyi paprikása'}
    assert renamed['steps']['en'] == renamed['steps']['hu']


def test_the_shelves(c):
    r = c.get('/api/sauces/shelves')
    sh = r.json()
    assert [s['id'] for s in sh['shelves']] == ['fats', 'acids', 'dairy-eggs', 'alliums', 'herbs', 'umami', 'sweet', 'heat',
                                                 'thickeners', 'liquids', 'veg']
    items = {i['id']: i for s in sh['shelves'] for i in s['items']}
    assert 'wheat-flour' not in items and 'soy-sauce' not in items          # typed only: the kitchen is GF
    assert items['egg-yolk']['name'] == {'en': 'Egg yolk', 'hu': 'Tojássárgája'}
    assert items['mustard']['gluten'] == 'label'
    assert len(sh['families']) == 40 and len(sh['foods']) == 25 and sh['max_lines'] == 24
    # the body gauge's bands come from the engine's own limits (a copy on the web would drift); the last one open-ended
    from kitchen.sauce_engine import BODY_CLASSES
    assert [(b['id'], b['below']) for b in sh['body']] == [(c_, min(lim, 99)) for lim, c_ in BODY_CLASSES]
    assert c.get('/api/sauces/shelves', headers={'If-None-Match': r.headers['etag']}).status_code == 304


def test_evaluate_answers_with_the_gluten_lines_and_the_sequence(c):
    e = c.post('/api/sauces/evaluate', json={'lines': VINAIGRETTE, 'steps': [], 'seq': 7}).json()
    assert e['seq'] == 7 and e['family']['id'] == 'vinaigrette'
    assert [ln['status'] for ln in e['gluten']['lines']] == ['ok', 'ok', 'ok'] and e['gluten']['verdict']['state'] == 'gf'


@pytest.mark.parametrize('lines', [
    [{'shelf': 'unicorn-milk', 'qty': 1, 'unit': 'dl'}],
    [{'shelf': 'milk', 'qty': 1, 'unit': 'tsp'}],
    [{'shelf': 'milk', 'qty': 1, 'unit': 'dl'}] * 25,
    [{'spice': 'unobtainium', 'qty': 1, 'unit': 'tsp'}],
    [{'blend': 99999, 'qty': 1, 'unit': 'tsp'}],
    [{'shelf': 'milk', 'spice': 'cumin', 'qty': 1, 'unit': 'dl'}],
    [{'item': 'dragon-egg', 'raw': 'egy sárkánytojás'}],
    [{'qty': 1, 'unit': 'dl'}],
])
def test_bad_lines_are_refused(c, lines):
    assert c.post('/api/sauces/evaluate', json={'lines': lines}).status_code == 422


def test_an_unknown_family_is_refused(c):
    assert c.post('/api/sauces/evaluate', json={'lines': VINAIGRETTE, 'family': 'soup'}).status_code == 422
    e = c.post('/api/sauces/evaluate', json={'lines': VINAIGRETTE, 'family': 'marinade'}).json()
    assert e['family']['id'] == 'marinade' and e['family']['user'] is True


@pytest.mark.parametrize('text, want', [
    ('2 ek búzaliszt', {'shelf': 'wheat-flour', 'qty': 2, 'unit': 'tbsp'}),
    ('3 ek szójaszósz', {'shelf': 'soy-sauce', 'qty': 3, 'unit': 'tbsp'}),
    ('1 dl tamari', {'shelf': 'tamari', 'qty': 100, 'unit': 'ml'}),
    ('2 tk kömény', {'spice': 'caraway', 'qty': 2, 'unit': 'tsp'}),
    ('2 gerezd fokhagyma', {'shelf': 'garlic', 'qty': 2, 'unit': 'pcs'}),
    ('1 db ponty', {'item': 'carp'}),
    ('egy marék titok', {'raw': 'egy marék titok'}),
])
def test_a_typed_line_is_read_like_a_recipe_line(c, text, want):
    got = c.post('/api/sauces/line', json={'text': text}).json()
    assert {k: got.get(k) for k in want} == want, got


def test_wheat_and_soy_read_swap_tamari_reads_ok_and_unknown_fails_closed(c):
    """Through gluten.check_line: a wheat roux and soy sauce need their swap; tamari is GF; a typed line nothing
    matched can never read GF until it is matched or the user marks it."""
    lines = [c.post('/api/sauces/line', json={'text': t}).json() for t in
             ('3 ek búzaliszt', '3 ek szójaszósz', '2 ek tamari', 'egy marék titok')]
    lines = [{**ln, 'qty': ln.get('qty'), 'unit': ln.get('unit')} for ln in lines]
    lines.insert(0, {'shelf': 'milk', 'qty': 5, 'unit': 'dl'})
    g = c.post('/api/sauces/evaluate', json={'lines': lines, 'steps': ['Simmer it.']}).json()['gluten']
    st = [ln['status'] for ln in g['lines']]
    assert st == ['ok', 'swap', 'swap', 'ok', 'unknown']
    assert g['lines'][2]['swap_id'] == 'tamari'
    assert g['verdict']['state'] == 'unknown'
    lines[-1]['ok_gf'] = True                                        # the user looked: it is fine
    assert c.post('/api/sauces/evaluate', json={'lines': lines}).json()['gluten']['lines'][-1]['status'] == 'ok'


def test_a_blend_line_reads_its_most_cautious_jar_and_never_a_manual_ok(c):
    gf = c.post('/api/blends', json={'name': 'Plain', 'parts': [{'spice': 'cumin', 'parts': 2}, {'spice': 'coriander-seed', 'parts': 1}]}).json()['id']
    hing = c.post('/api/blends', json={'name': 'Hing mix', 'parts': [{'spice': 'cumin', 'parts': 2}, {'spice': 'asafoetida', 'parts': 0.5}]}).json()['id']
    base = [{'shelf': 'yogurt', 'qty': 200, 'unit': 'g'}]
    ok = c.post('/api/sauces/evaluate', json={'lines': base + [{'blend': gf, 'qty': 1, 'unit': 'tsp'}]}).json()['gluten']['lines'][1]
    assert ok['status'] == 'ok'
    # positive control for the guard: the user's "OK" on a blend line holding asafoetida changes nothing
    chk = c.post('/api/sauces/evaluate', json={'lines': base + [{'blend': hing, 'qty': 1, 'unit': 'tsp', 'ok_gf': True}]}).json()
    line = chk['gluten']['lines'][1]
    assert line['status'] == 'check' and line['about'] == ['asafoetida']
    assert 'asafoetida' in line['tip_en'] and 'Hing mix' in line['tip_en']
    assert c.put('/api/pantry/asafoetida', json={'have': True}).status_code == 200
    assert c.post('/api/sauces/evaluate', json={'lines': base + [{'blend': hing, 'qty': 1, 'unit': 'tsp'}]}).json()['gluten']['lines'][1]['status'] == 'yours'


def test_the_gluten_state_is_only_ever_the_gluten_engines():
    """Guard: sauces.py and sauce_engine.py never decide a gluten state themselves."""
    rules = [re.compile(r'\.gluten\s*(==|!=|in\b)'), re.compile(r"\[['\"]gluten['\"]\]\s*(==|!=)"),
             re.compile(r"status\W{0,4}[:=]\s*['\"](ok|yours|check|swap|unknown)['\"]"), re.compile(r"['\"]contains['\"]")]

    def breaches(src: str) -> list[str]:
        return [ln.strip() for ln in src.splitlines() for rx in rules if rx.search(ln)]
    # positive control: a line deciding GF from the catalogue flag is caught
    assert breaches("    if item.gluten == 'free':\n        status = 'ok'") != []
    for name in ('sauces.py', 'sauce_engine.py'):
        assert breaches((SERVER / name).read_text()) == [], name
    assert 'gluten.check_line(' in (SERVER / 'sauces.py').read_text() and 'gluten.verdict(' in (SERVER / 'sauces.py').read_text()


def test_crud_family_override_and_riff(c):
    sid = c.post('/api/sauces', json={'name': 'My dressing', 'lines': VINAIGRETTE, 'steps': ['Shake it.'], 'tags': ['Salad', 'salad']}).json()['id']
    d = c.get(f'/api/sauces/{sid}').json()
    assert d['tags'] == ['salad'] and d['family']['id'] == 'vinaigrette' and d['family_user'] is False
    put = c.put(f'/api/sauces/{sid}', json={'name': 'My marinade', 'lines': VINAIGRETTE, 'steps': ['Marinate the meat in it.'],
                                            'family': 'marinade'}).json()
    assert put['family']['id'] == 'marinade' and put['family_user'] is True
    new = c.post(f'/api/sauces/{sid}/riff').json()['id']
    assert c.get(f'/api/sauces/{new}').json()['name'] == 'My marinade (2)'
    assert c.delete(f'/api/sauces/{sid}').status_code == 204
    assert c.get(f'/api/sauces/{sid}').status_code == 404
    assert c.put('/api/sauces/99999', json={'name': 'x', 'lines': VINAIGRETTE}).status_code == 404


def test_a_saved_line_gives_back_everything_the_editor_sent(c):
    """The editor reloads a sauce from its line views: a typed line's text and how it was matched, the user's GF
    override and the amounts must all come back, or an edit silently drops them (an override lost = a line that reads
    "check" again; a typed shelf line that lost its text shows only the item)."""
    lines = [{'shelf': 'olive-oil', 'qty': 6, 'unit': 'tbsp', 'raw': '6 tbsp olive oil', 'match_how': 'exact'},
             {'spice': 'cumin', 'qty': 1, 'unit': 'tsp', 'ok_gf': True},
             {'item': 'ketchup', 'raw': 'a squirt of ketchup', 'match_how': 'stem', 'ok_gf': True},
             {'raw': 'a splash of something'}]
    sid = c.post('/api/sauces', json={'name': 'Round trip', 'lines': lines}).json()['id']
    got = c.get(f'/api/sauces/{sid}').json()['lines']
    keep = ('kind', 'shelf_id', 'spice_id', 'item_id', 'raw', 'qty', 'unit', 'ok_gf', 'match_how')
    assert [{k: ln[k] for k in keep} for ln in got] == [
        {'kind': 'shelf', 'shelf_id': 'olive-oil', 'spice_id': None, 'item_id': 'olive-oil', 'raw': '6 tbsp olive oil', 'qty': 6,
         'unit': 'tbsp', 'ok_gf': False, 'match_how': 'exact'},
        {'kind': 'spice', 'shelf_id': None, 'spice_id': 'cumin', 'item_id': 'cumin', 'raw': None, 'qty': 1, 'unit': 'tsp',
         'ok_gf': True, 'match_how': None},
        {'kind': 'off-shelf', 'shelf_id': None, 'spice_id': None, 'item_id': 'ketchup', 'raw': 'a squirt of ketchup', 'qty': None,
         'unit': None, 'ok_gf': True, 'match_how': 'stem'},
        {'kind': 'raw', 'shelf_id': None, 'spice_id': None, 'item_id': None, 'raw': 'a splash of something', 'qty': None,
         'unit': None, 'ok_gf': False, 'match_how': None}]


def test_a_sauce_of_typed_lines_only_still_opens(c):
    sid = c.post('/api/sauces', json={'name': 'Mystery', 'lines': [{'raw': 'valami'}]}).json()['id']
    d = c.get(f'/api/sauces/{sid}').json()
    assert d['evaluation'] is None and d['score'] is None and d['gluten']['state'] == 'unknown'


def test_a_blend_a_sauce_uses_cannot_be_deleted(c):
    bid = c.post('/api/blends', json={'name': 'House', 'parts': [{'spice': 'cumin', 'parts': 1}, {'spice': 'sweet-paprika', 'parts': 2}]}).json()['id']
    sid = c.post('/api/sauces', json={'name': 'Spiced yoghurt', 'lines': [{'shelf': 'yogurt', 'qty': 200, 'unit': 'g'},
                                                                           {'blend': bid, 'qty': 1, 'unit': 'tsp'}]}).json()['id']
    r = c.delete(f'/api/blends/{bid}')
    assert r.status_code == 409 and r.json()['detail']['sauces'] == [{'id': sid, 'name': 'Spiced yoghurt'}]
    assert c.delete(f'/api/sauces/{sid}').status_code == 204
    assert c.delete(f'/api/blends/{bid}').status_code == 204


def test_every_change_is_announced(c):
    q = c.app.state.events.subscribe()
    sid = c.post('/api/sauces', json={'name': 'x', 'lines': VINAIGRETTE}).json()['id']
    c.put(f'/api/sauces/{sid}', json={'name': 'y', 'lines': VINAIGRETTE})
    c.post(f'/api/sauces/{sid}/riff')
    c.delete(f'/api/sauces/{sid}')
    seen = []
    while not q.empty():
        seen.append(q.get_nowait())
    assert sum(1 for m in seen if 'sauces' in str(m)) == 4


def test_the_engine_is_quick_enough_to_answer_every_tap(c):
    data = c.app.state.sauces.data
    lines = [{'shelf': i, 'qty': e['default'], 'unit': e['unit']} for i, e in list(data.ingredients.items())[:20]
             if e.get('offer') is not False][:20]
    lines += [{'spice': s, 'qty': 1, 'unit': 'tsp'} for s in ('cumin', 'coriander-seed', 'cinnamon', 'cloves')]
    t = time.perf_counter()
    for _ in range(20):
        assert c.post('/api/sauces/evaluate', json={'lines': lines, 'steps': ['Simmer 10 minutes.']}).status_code == 200
    assert (time.perf_counter() - t) / 20 < 0.08


def test_the_engines_switch(tmp_path):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL, spices=False)
    with TestClient(create_app(cfg, shopping_sync_every=None)) as c:
        assert c.get('/api/sauces').status_code == 503
        assert c.get('/api/sauces/shelves').status_code == 503
