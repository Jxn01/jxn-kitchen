import pathlib

import pytest
from fastapi.testclient import TestClient

from kitchen.app import create_app
from kitchen.config import Config

REAL = pathlib.Path(__file__).resolve().parents[2] / 'catalogue'

PAPRIKAS = {
    'title': 'Paprikás csirke nokedlivel', 'servings': 4, 'total_min': 55, 'tags': ['csirke', 'magyar'],
    'ingredients': ['2 közepes db Vöröshagyma', '1 gerezd Fokhagyma', 'só, bors', '1 teáskanál Fűszerpaprika',
                    '1 közepes db Paprika', '6 db Csirke alsócomb', '2 dl Tejföl', '1 ek Finomliszt',
                    '1 db Leveskocka', '50 dkg Finomliszt', '1 db Tojás', '5 dl Víz'],
    'steps': ['A hagymát olajon üvegesre pároljuk.', 'Fedő alatt kb. 40 percig főzzük.', 'A nokedlit 2-3 percig főzzük.'],
}


@pytest.fixture
def c(tmp_path):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL)
    with TestClient(create_app(cfg, shopping_sync_every=None)) as client:
        client.put('/api/settings', json={'language': 'hu'})
        yield client


def create(c, body=PAPRIKAS):
    r = c.post('/api/recipes', json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_create_and_read_with_gluten_verdict(c):
    r = create(c)
    d = c.get(f"/api/recipes/{r['id']}").json()
    assert d['title'] == 'Paprikás csirke nokedlivel' and d['servings'] == 4
    names = [l['item_id'] for l in d['lines']]
    assert names[:4] == ['onion', 'garlic', 'salt', 'black-pepper']        # "só, bors" -> two lines
    assert 'hungarian-pepper' in names and 'chicken-drumsticks' in names and 'water' in names
    flour = [l for l in d['lines'] if l['item_id'] == 'wheat-flour']
    assert len(flour) == 2 and all(l['gluten'] == 'swap' for l in flour)
    assert flour[0]['gf_text'] == '1 ek GM lisztkeverék' and flour[0]['tip']
    cube = next(l for l in d['lines'] if l['item_id'] == 'stock-cube')
    assert cube['gluten'] == 'check'
    assert d['verdict'] == {'state': 'swaps', 'swaps': 2, 'check': 1, 'unknown': 0}
    assert [s['timers'][0]['seconds'] for s in d['steps'][1:]] == [2400, 180]


def test_label_item_in_the_pantry_becomes_yours(c):
    r = create(c)
    c.put('/api/pantry/stock-cube', json={'have': True})
    cube = next(l for l in c.get(f"/api/recipes/{r['id']}").json()['lines'] if l['item_id'] == 'stock-cube')
    assert cube['gluten'] == 'yours'


def test_an_unmatched_line_blocks_gf_until_matched_or_marked_ok(c):
    body = {'title': 'Teszt', 'ingredients': ['2 db Vöröshagyma', '1 csipet xyzzy-por'], 'steps': []}
    r = create(c, body)
    d = c.get(f"/api/recipes/{r['id']}").json()
    assert d['verdict']['state'] == 'unknown' and d['lines'][1]['gluten'] == 'unknown'
    c.put(f"/api/recipes/{r['id']}/lines/1", json={'item_id': None, 'ok_gf': True})
    assert c.get(f"/api/recipes/{r['id']}").json()['verdict']['state'] == 'gf'
    c.put(f"/api/recipes/{r['id']}/lines/1", json={'item_id': 'black-pepper', 'ok_gf': False})
    d = c.get(f"/api/recipes/{r['id']}").json()
    assert d['lines'][1]['item_id'] == 'black-pepper' and d['lines'][1]['how'] == 'user' and d['verdict']['state'] == 'gf'
    assert c.put(f"/api/recipes/{r['id']}/lines/9", json={'item_id': None, 'ok_gf': True}).status_code == 404
    assert c.put(f"/api/recipes/{r['id']}/lines/1", json={'item_id': 'nope', 'ok_gf': False}).status_code == 404


def test_have_total_missing_and_scaling(c):
    r = create(c)
    for node in ('onion', 'garlic', 'chicken-drumsticks', 'sour-cream', 'eggs', 'sweet-paprika'):
        c.put(f'/api/pantry/{node}', json={'have': True})
    d = c.get(f"/api/recipes/{r['id']}?servings=8").json()
    missing = {m['item_id'] for m in d['missing']}
    assert missing == {'hungarian-pepper', 'stock-cube'}            # flour -> GF flour mix is a staple: in
    assert d['have'] == d['total'] - 2
    onion = next(l for l in d['lines'] if l['item_id'] == 'onion')
    assert onion['qty_text'] == '4 db'                                 # 2 -> 4 at double servings
    assert d['servings'] == 8 and d['base_servings'] == 4


def test_missing_to_shopping(c):
    r = create(c)
    items = c.post(f"/api/recipes/{r['id']}/missing-to-shopping").json()
    texts = {i['text'] for i in items}
    assert 'TV paprika' in texts and 'GM Leveskocka' in texts and 'Vöröshagyma' in texts
    assert not any('liszt' in t.lower() and 'GM' not in t for t in texts)   # never wheat on the list


def test_list_update_delete_and_cookable(c):
    a = create(c)
    b = create(c, {'title': 'Rántotta', 'servings': 1, 'ingredients': ['3 db Tojás', '1 ek Vaj', 'só'], 'steps': []})
    c.put('/api/pantry/eggs', json={'have': True}); c.put('/api/pantry/butter', json={'have': True})
    lst = c.get('/api/recipes').json()
    assert {x['title'] for x in lst} == {'Paprikás csirke nokedlivel', 'Rántotta'}
    assert c.get('/api/cookable').json()[0]['id'] == b['id']           # everything in stock
    assert [x['title'] for x in c.get('/api/recipes?q=paprik').json()] == ['Paprikás csirke nokedlivel']
    assert [x['title'] for x in c.get('/api/recipes?tag=magyar').json()] == ['Paprikás csirke nokedlivel']
    upd = dict(PAPRIKAS, title='Paprikás csirke', ingredients=PAPRIKAS['ingredients'][:3])
    assert c.put(f"/api/recipes/{a['id']}", json=upd).json()['title'] == 'Paprikás csirke'
    assert len(c.get(f"/api/recipes/{a['id']}").json()['lines']) == 4
    assert c.delete(f"/api/recipes/{a['id']}").status_code == 204
    assert c.get(f"/api/recipes/{a['id']}").status_code == 404


def test_validation(c):
    assert c.post('/api/recipes', json={'title': '', 'ingredients': [], 'steps': []}).status_code == 422
    assert c.post('/api/recipes', json={'title': 'x', 'servings': 0, 'ingredients': [], 'steps': []}).status_code == 422


def test_parse_preview(c):
    p = c.post('/api/parse', json={'lines': ['50 dkg Finomliszt', 'só, bors', 'xyzzy']}).json()
    assert [x['item_id'] for x in p] == ['wheat-flour', 'salt', 'black-pepper', None]
    assert p[0]['gluten'] == 'swap' and p[3]['gluten'] == 'unknown'


def test_recipe_events(c):
    q = c.app.state.events.subscribe()
    r = create(c)
    assert q.get_nowait() == ('recipes', {'id': r['id']})


def test_photo_upload_resize_serve_and_replace(c):
    import io
    from PIL import Image
    r = create(c)
    buf = io.BytesIO(); Image.new('RGB', (3000, 2000), (200, 80, 40)).save(buf, 'PNG')
    up = c.put(f"/api/recipes/{r['id']}/image", content=buf.getvalue(), headers={'Content-Type': 'image/png'})
    assert up.status_code == 200
    url = up.json()['image']
    got = c.get(url)
    assert got.status_code == 200 and got.headers['content-type'] == 'image/jpeg'
    im = Image.open(io.BytesIO(got.content))
    assert max(im.size) == 1024                                       # shrunk for the kiosk
    assert c.get(f"/api/recipes/{r['id']}").json()['image'] == url
    assert c.put(f"/api/recipes/{r['id']}/image", content=b'not an image').status_code == 422
    assert c.put('/api/recipes/999/image', content=buf.getvalue()).status_code == 404
    for bad in ('../kitchen.db', '..%2Fkitchen.db', 'x.jpg', '1-2.png'):
        assert c.get(f'/api/images/{bad}').status_code == 404


def test_image_bombs_and_odd_formats_are_refused(c):
    import io, struct, zlib
    from PIL import Image
    r = create(c)
    # a PNG header claiming 20000x20000 (decompression bomb) — refused before decoding
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    bomb = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 20000, 20000, 8, 2, 0, 0, 0)) + chunk(b'IEND', b'')
    assert c.put(f"/api/recipes/{r['id']}/image", content=bomb).status_code == 422
    buf = io.BytesIO(); Image.new('RGB', (50, 50)).save(buf, 'BMP')          # BMP: not an accepted format
    assert c.put(f"/api/recipes/{r['id']}/image", content=buf.getvalue()).status_code == 422


def test_oversized_upload_is_refused_without_reading_it_all(c):
    r = create(c)
    big = b'\xff' * (15 * 1024 * 1024 + 1)
    assert c.put(f"/api/recipes/{r['id']}/image", content=big).status_code == 413
    assert c.post('/api/parse', json={'lines': ['x' * 401]}).status_code == 422
    assert c.post('/api/shopping', json={'text': 'x' * 201}).status_code == 422


def test_startup_rematches_old_lines_but_never_hand_corrections(tmp_path):
    """A line matched under an older catalogue (here: soup noodles -> the GF tile) is re-pointed
    at start-up, so an old recipe loses a wrong ✓ GF; a line the user corrected by hand is left alone."""
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL)
    with TestClient(create_app(cfg, shopping_sync_every=None)) as c:
        rid = c.post('/api/recipes', json={'title': 'Leves', 'servings': 4,
                                            'ingredients': ['10 dkg soup noodles', '1 db sárgarépa'], 'steps': []}).json()['id']
        c.put(f'/api/recipes/{rid}/lines/1', json={'item_id': 'parsnip', 'ok_gf': False})      # a hand correction
        async def corrupt():                                 # what an older catalogue had stored
            c.app.state.db.execute("UPDATE recipe_ingredient SET item_id = 'gf-soup-noodles', match_how = 'exact' "
                                   'WHERE recipe_id = ? AND pos = 0', (rid,))
        c.portal.call(corrupt)
        assert c.get(f'/api/recipes/{rid}').json()['verdict']['state'] == 'gf'                # the wrong ✓ GF
    with TestClient(create_app(cfg, shopping_sync_every=None)) as c:                          # restart
        d = c.get(f'/api/recipes/{rid}').json()
        assert d['lines'][0]['item_id'] == 'soup-noodles' and d['verdict']['state'] == 'swaps'
        assert d['lines'][1]['item_id'] == 'parsnip'


def test_summaries_list_the_first_missing_items(c):
    create(c)
    s = c.get('/api/recipes').json()[0]
    assert s['missing'] >= 1 and 1 <= len(s['missing_names']) <= 4 and all(isinstance(n, str) for n in s['missing_names'])


def test_each_line_names_its_pantry_tile(c):
    """Cook mode's 'Used up anything?' takes items out of the pantry: a line must say WHICH tile — for a wheat line
    that is its GF version (the only tile there is), for a tile-less staple (water) nothing."""
    rid = c.post('/api/recipes', json={'title': 'T', 'servings': 2, 'steps': [],
                                       'ingredients': ['20 dkg liszt', '2 db vöröshagyma', '1 l víz']}).json()['id']
    lines = {l['raw']: l for l in c.get(f'/api/recipes/{rid}').json()['lines']}
    assert lines['20 dkg liszt']['item_id'] == 'wheat-flour' and lines['20 dkg liszt']['pantry_id'] == 'gf-flour-mix'
    assert lines['2 db vöröshagyma']['pantry_id'] == lines['2 db vöröshagyma']['item_id']
    assert lines['1 l víz']['pantry_id'] is None



def test_a_recipe_without_lines_never_reads_gluten_free(c):
    # A list page imported as an empty draft read "Gluten-free as it is ✓" in the list and on the page. An empty recipe has nothing checked: 'empty', in the summary and in the full recipe.
    r = c.post('/api/recipes', json={'title': 'Üres piszkozat', 'ingredients': [], 'steps': []})
    assert r.status_code == 200, r.text
    rid = r.json()['id']
    assert c.get(f'/api/recipes/{rid}').json()['verdict']['state'] == 'empty'
    assert {x['id']: x['verdict']['state'] for x in c.get('/api/recipes').json()}[rid] == 'empty'


def test_rematch_reparses_old_lines(c, tmp_path):
    # A row stored by an older parser kept the purpose phrase in its name, which now trips the gluten safety net. The
    # start-up rematch re-parses the raw line, so the old recipe gets the fixed name and the right item.
    import sqlite3
    from kitchen import recipes as R
    rid = c.post('/api/recipes', json={'title': 'Régi', 'ingredients': ['2 ek porcukor a tészta szórásához',
                                                                        'só, bors'], 'steps': []}).json()['id']
    db = sqlite3.connect(tmp_path / 'kitchen.db'); db.row_factory = sqlite3.Row; db.isolation_level = None
    db.execute("UPDATE recipe_ingredient SET name = 'porcukor a tészta szórásához', note = NULL, item_id = NULL "
               "WHERE recipe_id = ? AND pos = 0", (rid,))
    assert R.rematch_all(db, c.app.state.matcher) >= 1
    row = db.execute('SELECT name, note, item_id FROM recipe_ingredient WHERE recipe_id = ? AND pos = 0', (rid,)).fetchone()
    assert (row['name'], row['note'], row['item_id']) == ('porcukor', 'a tészta szórásához', 'powdered-sugar')
    names = [r['name'] for r in db.execute('SELECT name FROM recipe_ingredient WHERE recipe_id = ? AND pos > 0', (rid,))]
    assert names == ['só', 'bors']                       # a multi-ingredient raw line is left as stored


def _db(tmp_path):
    import sqlite3
    db = sqlite3.connect(tmp_path / 'kitchen.db'); db.row_factory = sqlite3.Row; db.isolation_level = None
    return db


def test_a_gluten_item_in_the_note_keeps_the_line_from_reading_ok(c):
    # purpose phrases moved to the note must not take their gluten out of the check.
    rid = c.post('/api/recipes', json={'title': 'Vajas', 'ingredients': ['2 db tojás', '1 ek vaj a kenyérhez'],
                                       'steps': []}).json()['id']
    r = c.get(f'/api/recipes/{rid}?lang=hu').json()
    vaj = next(l for l in r['lines'] if l['name'] == 'vaj')
    assert vaj['gluten'] == 'check' and 'kenyér' in vaj['tip'].lower()
    assert r['verdict']['state'] == 'check'                              # never ✓ GF
    assert {x['id']: x['verdict']['state'] for x in c.get('/api/recipes').json()}[rid] == 'check'
    # counter-case: a note with no gluten in it changes nothing
    rid2 = c.post('/api/recipes', json={'title': 'Forma', 'ingredients': ['1 ek Vaj a forma kikenéséhez'],
                                        'steps': []}).json()['id']
    assert c.get(f'/api/recipes/{rid2}').json()['verdict']['state'] == 'gf'


def test_rematch_never_downgrades_a_gluten_line_on_its_own(c, tmp_path):
    from kitchen import recipes as R
    rid = c.post('/api/recipes', json={'title': 'Régi', 'ingredients': ['1 ek vaj a tészta kenéséhez',
                                                                        '1 ek liszt a tejföl behabarásához',
                                                                        '1 csokor zellerzöld'], 'steps': []}).json()['id']
    db = _db(tmp_path)
    # as an older build stored them: the butter line flagged as wheat pasta (safe side), the flour line matched to
    # SOUR CREAM (the hazard), the herb unmatched
    db.execute("UPDATE recipe_ingredient SET name = 'vaj a tészta kenéséhez', note = NULL, item_id = 'wheat-pasta-short' "
               "WHERE recipe_id = ? AND pos = 0", (rid,))
    db.execute("UPDATE recipe_ingredient SET name = 'liszt a tejföl behabarásához', note = NULL, item_id = 'sour-cream' "
               "WHERE recipe_id = ? AND pos = 1", (rid,))
    db.execute("UPDATE recipe_ingredient SET item_id = NULL WHERE recipe_id = ? AND pos = 2", (rid,))
    R.rematch_all(db, c.app.state.matcher)
    got = {r['pos']: (r['name'], r['item_id']) for r in db.execute(
        'SELECT pos, name, item_id FROM recipe_ingredient WHERE recipe_id = ?', (rid,))}
    assert got[0] == ('vaj a tészta kenéséhez', 'wheat-pasta-short')      # contains -> butter: held for the user
    assert got[1] == ('liszt', 'wheat-flour')                            # free -> contains: applied at once
    assert got[2][1] == 'celery'                                         # unmatched -> matched: applied, as at import
