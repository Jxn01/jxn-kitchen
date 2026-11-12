"""Blends (spec 2026-10-19 §4.4, §6.2, §8): seeds, the rack, CRUD, riff, the GF line, stored ids, events."""
import pathlib
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from kitchen import db, references
from kitchen.app import create_app
from kitchen.config import Config

REAL = pathlib.Path(__file__).resolve().parents[2] / 'catalogue'


def make(tmp_path):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL)
    return TestClient(create_app(cfg, shopping_sync_every=None, timers_autorun=False, scans_autorun=False))


@pytest.fixture
def c(tmp_path):
    with make(tmp_path) as client:
        yield client


PORKOLT = [{'spice': 'sweet-paprika', 'parts': 4}, {'spice': 'caraway', 'parts': 1}, {'spice': 'marjoram', 'parts': 1}]


def test_the_sixteen_classics_are_seeded_once_in_a_lifetime(tmp_path):
    with make(tmp_path) as c:
        bs = c.get('/api/blends').json()
        assert len(bs) == 16 and {b['origin'] for b in bs} == {'seed'}
        for b in bs:
            assert c.delete(f'/api/blends/{b["id"]}').status_code == 204
        assert c.get('/api/blends').json() == []
    with make(tmp_path) as c:                     # a restart does not bring them back
        assert c.get('/api/blends').json() == []


def test_a_seed_speaks_both_languages_until_it_is_renamed(c):
    b = next(b for b in c.get('/api/blends').json() if b['classic_id'] == 'porkolt')
    assert b['names'] == {'en': 'Pörkölt blend', 'hu': 'Pörköltfűszer'}
    d = c.get(f'/api/blends/{b["id"]}').json()
    assert d['method']['hu'] == 'A hagymához add, lehúzva a tűzről.'
    assert d['evaluation']['word'] in ('sings', 'good') and d['evaluation']['score'] == b['score']
    body = {'name': 'Nagyi pörköltje', 'notes': d['notes'], 'parts': d['parts']}
    renamed = c.put(f'/api/blends/{b["id"]}', json=body).json()
    assert renamed['names'] == {'en': 'Nagyi pörköltje', 'hu': 'Nagyi pörköltje'}


def test_the_rack(c):
    r = c.get('/api/spices')
    rack = r.json()
    assert [s['id'] for s in rack['shelves']] == ['warm', 'earthy', 'hot', 'mediterranean', 'green', 'special', 'alliums']
    jars = [j for s in rack['shelves'] for j in s['jars']]
    assert len(jars) == 61 and len(rack['foods']) == 25
    cumin = next(j for j in jars if j['id'] == 'cumin')
    assert cumin['label'] == {'en': 'cumin', 'hu': 'római kömény'} and cumin['page'] == 'spices/earthy'
    assert cumin['note']['en'].startswith('Goes with')
    assert sum(1 for j in jars if j['note']) == 48           # the know-how rack's jars carry its note
    assert next(j for j in jars if j['id'] == 'asafoetida')['gluten'] == 'label'
    assert c.get('/api/spices', headers={'if-none-match': r.headers['etag']}).status_code == 304


def test_create_read_update_delete(c):
    bid = c.post('/api/blends', json={'name': 'My paprika mix', 'parts': PORKOLT, 'tags': ['Pork ', 'pork']}).json()['id']
    d = c.get(f'/api/blends/{bid}').json()
    assert d['names']['en'] == 'My paprika mix' and d['tags'] == ['pork'] and d['origin'] == 'typed'
    assert [p['spice'] for p in d['parts']] == ['sweet-paprika', 'caraway', 'marjoram']
    assert 'backbone:hungarian-base' in [f['id'] for f in d['evaluation']['findings']]
    upd = c.put(f'/api/blends/{bid}', json={'name': 'My paprika mix', 'parts': PORKOLT[:2]}).json()
    assert len(upd['parts']) == 2 and upd['tags'] == []
    assert c.get('/api/blends', params={'q': 'PAPRIKA'}).json()[0]['id'] == bid
    assert c.delete(f'/api/blends/{bid}').status_code == 204
    assert c.get(f'/api/blends/{bid}').status_code == 404
    assert c.put(f'/api/blends/{bid}', json={'name': 'x', 'parts': PORKOLT}).status_code == 404
    assert c.delete(f'/api/blends/{bid}').status_code == 404


@pytest.mark.parametrize('body', [
    {'name': '', 'parts': PORKOLT},
    {'name': 'x', 'parts': []},
    {'name': 'x', 'parts': [{'spice': 'unobtainium', 'parts': 1}]},
    {'name': 'x', 'parts': [{'spice': 'cumin', 'parts': 0}]},
    {'name': 'x', 'parts': [{'spice': 'cumin', 'parts': 1}, {'spice': 'cumin', 'parts': 2}]},
    {'name': 'x', 'parts': [{'spice': 'cumin', 'parts': 1}] * 17},
    {'name': 'a\nb', 'parts': PORKOLT},
])
def test_bad_blends_are_refused(c, body):
    assert c.post('/api/blends', json=body).status_code == 422


def test_riff_copies_with_a_fresh_name(c):
    seed = next(b for b in c.get('/api/blends').json() if b['classic_id'] == 'curry')
    one = c.get(f'/api/blends/{c.post(f"/api/blends/{seed["id"]}/riff").json()["id"]}').json()
    two = c.get(f'/api/blends/{c.post(f"/api/blends/{seed["id"]}/riff").json()["id"]}').json()
    assert (one['names']['en'], two['names']['en']) == ('Curry powder (2)', 'Curry powder (3)')
    assert one['origin'] == 'riff' and one['classic_id'] == 'curry' and one['parts'] == seed['parts']
    assert c.post('/api/blends/99999/riff').status_code == 404


def test_evaluate_echoes_its_sequence_and_carries_the_gf_line(c):
    r = c.post('/api/blends/evaluate', json={'parts': PORKOLT, 'seq': 41}).json()
    assert r['seq'] == 41 and r['gluten']['status'] == 'ok' and r['gluten']['hu']
    assert c.post('/api/blends/evaluate', json={'parts': [{'spice': 'nope', 'parts': 1}]}).status_code == 422
    big = c.post('/api/blends/evaluate', json={'parts': PORKOLT, 'batch_tbsp': 6}).json()
    assert big['batch']['tsp'] == 18


def test_a_label_jar_reads_check_until_it_is_the_owners_own(c):
    """Single spices are GF; mustard powder, chilli powder and asafoetida can hide wheat flour (the know-how says so)."""
    gl = {b['classic_id']: b['gluten'] for b in c.get('/api/blends').json()}
    assert gl['grill-rub']['status'] == 'check' and gl['grill-rub']['about'] == ['mustard-powder']
    assert 'mustárpor' in gl['grill-rub']['hu'].lower()
    assert gl['taco']['status'] == 'check' and gl['taco']['about'] == ['chili-powder']
    assert gl['porkolt']['status'] == 'ok'
    assert c.put('/api/pantry/mustard-powder', json={'have': True}).status_code == 200
    gl = {b['classic_id']: b['gluten'] for b in c.get('/api/blends').json()}
    assert gl['grill-rub']['status'] == 'yours'


def test_every_change_is_announced(c):
    q = c.app.state.events.subscribe()
    bid = c.post('/api/blends', json={'name': 'x', 'parts': PORKOLT}).json()['id']
    c.put(f'/api/blends/{bid}', json={'name': 'y', 'parts': PORKOLT})
    c.delete(f'/api/blends/{bid}')
    seen = []
    while not q.empty():
        seen.append(q.get_nowait())
    assert sum(1 for m in seen if 'blends' in str(m)) == 3


def test_blend_parts_are_stored_catalogue_ids(c):
    """references: a blend part pointing at a removed id is reported by /api/health, and replaced.yaml rewrites it."""
    bid = c.post('/api/blends', json={'name': 'x', 'parts': PORKOLT}).json()['id']

    async def corrupt():
        c.app.state.db.execute("UPDATE blend_part SET spice_id = 'gone-spice' WHERE blend_id = ? AND pos = 0", (bid,))
        return references.dangling(c.app.state.db, c.app.state.catalogue)
    assert f'blend {bid} part 0: gone-spice' in c.portal.call(corrupt)
    v = c.get(f'/api/blends/{bid}').json()                  # the blend still opens, without the lost jar
    assert v['missing_jars'] == ['gone-spice'] and len(v['parts']) == 2


def test_every_stored_item_id_column_is_tracked(tmp_path):
    conn = db.connect(tmp_path / 'k.db')

    def item_columns(conn: sqlite3.Connection) -> set[tuple[str, str]]:
        out = set()
        for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            for col in conn.execute(f'PRAGMA table_info({t})'):
                if col['name'] in ('item_id', 'spice_id'):
                    out.add((t, col['name']))
        return out
    assert item_columns(conn) == set(references.STORED_IDS)
    conn.execute('CREATE TABLE new_thing (item_id TEXT)')            # positive control
    assert item_columns(conn) != set(references.STORED_IDS)


def test_the_engine_is_quick_enough_to_answer_every_tap(c):
    parts = [{'spice': s, 'parts': 1} for s in ('cinnamon', 'cloves', 'cumin', 'caraway', 'sweet-paprika', 'chili-flakes',
                                                 'black-pepper', 'oregano', 'thyme', 'rosemary', 'dill-dried', 'parsley-dried',
                                                 'sumac', 'sesame', 'salt', 'garlic-powder')]
    t = time.perf_counter()
    for _ in range(20):
        c.post('/api/blends/evaluate', json={'parts': parts})
    assert (time.perf_counter() - t) / 20 < 0.05


def test_the_spices_switch(tmp_path):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL, spices=False)
    with TestClient(create_app(cfg, shopping_sync_every=None)) as c:
        assert c.get('/api/spices').status_code == 503 and c.get('/api/blends').status_code == 503


def test_the_image_carries_the_engine_knowledge():
    """The server refuses to start without engine/ — so the image must copy it (a deploy would otherwise crash-loop)."""
    dockerfile = (REAL.parent / 'deploy/Dockerfile').read_text()
    assert 'COPY engine ./engine' in dockerfile and 'COPY catalogue ./catalogue' in dockerfile
