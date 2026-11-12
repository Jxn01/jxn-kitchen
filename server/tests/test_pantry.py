import pathlib
import threading

from fastapi.testclient import TestClient

from kitchen import catalogue as C, db, pantry
from kitchen.app import create_app
from kitchen.config import Config

FIX = pathlib.Path(__file__).parent / 'fixtures' / 'catalogue'


def make(tmp_path):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=FIX, spices=False)
    return TestClient(create_app(cfg))


def test_default_state_has_staples_in(tmp_path):
    with make(tmp_path) as c:
        s = c.get('/api/pantry').json()
        assert s == {'have': ['rice-white'], 'groups_some': [], 'staples_off': [], 'rev': 0}


def test_toggle_item_round_trip_publishes(tmp_path):
    with make(tmp_path) as c:
        q = c.app.state.events.subscribe()
        r = c.put('/api/pantry/chicken-wings', json={'have': True})
        assert r.status_code == 200 and 'chicken-wings' in r.json()['have']
        ev = q.get_nowait()
        assert ev[0] == 'pantry' and ev[1]['node'] == 'chicken-wings' and ev[1]['have'] is True
        assert 'chicken-wings' in ev[1]['state']['have']
        r = c.put('/api/pantry/chicken-wings', json={'have': False})
        assert 'chicken-wings' not in r.json()['have']


def test_toggle_then_undo_ends_where_it_started(tmp_path):
    with make(tmp_path) as c:
        before = c.get('/api/pantry').json()
        q = c.app.state.events.subscribe()
        c.put('/api/pantry/alu-foil', json={'have': True})
        c.put('/api/pantry/alu-foil', json={'have': False})       # the toast's Undo
        assert q.qsize() == 2
        after = c.get('/api/pantry').json()
        assert after['rev'] == before['rev'] + 2                    # two writes…
        assert {**after, 'rev': 0} == {**before, 'rev': 0}          # …and the contents are back where they were


def test_group_switch_counts_for_every_item_of_the_group(tmp_path):
    with make(tmp_path) as c:
        s = c.put('/api/pantry/group:chicken', json={'have': True}).json()
        assert s['groups_some'] == ['chicken']
        cat = c.app.state.catalogue
        assert pantry.has(cat, s, 'chicken-breast') and pantry.has(cat, s, 'chicken-wings')
        assert not pantry.has(cat, s, 'smoked-sausage')


def test_staple_switched_off_and_back(tmp_path):
    with make(tmp_path) as c:
        s = c.put('/api/pantry/rice-white', json={'have': False}).json()
        assert 'rice-white' not in s['have'] and s['staples_off'] == ['rice-white']
        s = c.put('/api/pantry/rice-white', json={'have': True}).json()
        assert 'rice-white' in s['have'] and s['staples_off'] == []


def test_has_follows_the_swap_for_wheat_items(tmp_path):
    with make(tmp_path) as c:
        cat = c.app.state.catalogue
        s = c.put('/api/pantry/gf-pasta-long', json={'have': True}).json()
        assert pantry.has(cat, s, 'wheat-pasta')                  # a recipe's "pasta" is your GF pasta


def test_unknown_404_hidden_422_bad_body_422(tmp_path):
    with make(tmp_path) as c:
        assert c.put('/api/pantry/nope', json={'have': True}).status_code == 404
        assert c.put('/api/pantry/group:nope', json={'have': True}).status_code == 404
        assert c.put('/api/pantry/wheat-pasta', json={'have': True}).status_code == 422
        assert c.put('/api/pantry/chicken-wings', json={'have': 'yes'}).status_code == 422


def test_concurrent_writers_converge_to_the_last(tmp_path):
    with make(tmp_path) as c:
        def put(v):
            c.put('/api/pantry/chicken-breast', json={'have': v})
        threads = [threading.Thread(target=put, args=(i % 2 == 0,)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        c.put('/api/pantry/chicken-breast', json={'have': True})
        assert 'chicken-breast' in c.get('/api/pantry').json()['have']


def test_catalogue_endpoint_hides_wheat_and_has_an_etag(tmp_path):
    with make(tmp_path) as c:
        r = c.get('/api/catalogue')
        assert r.status_code == 200 and r.headers.get('etag')
        ids = [i['id'] for cat in r.json()['categories'] for g in cat['groups'] for i in g['items']]
        assert 'gf-pasta-long' in ids and 'wheat-pasta' not in ids
        assert c.get('/api/catalogue', headers={'If-None-Match': r.headers['etag']}).status_code == 304


def test_app_refuses_an_invalid_catalogue(tmp_path):
    import shutil, pytest
    shutil.copytree(FIX, tmp_path / 'c')
    f = tmp_path / 'c' / 'food' / 'meat.yaml'
    f.write_text(f.read_text().replace('hu: Csirkeszárny', 'hu: ""'))
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=tmp_path / 'c', spices=False)
    with pytest.raises(RuntimeError):
        with TestClient(create_app(cfg)):
            pass


def test_every_route_runs_on_the_event_loop():
    """Sync (`def`) routes run in a thread pool; with one SQLite connection that corrupts cursors. Guard the class."""
    import inspect
    from fastapi.routing import APIRoute
    cfg = Config(data_dir=pathlib.Path('/tmp'), static_dir=None, ha_url=None, ha_token=None, catalogue_dir=FIX, spices=False)
    sync_routes = [r.path for r in create_app(cfg).routes
                   if isinstance(r, APIRoute) and not inspect.iscoroutinefunction(r.endpoint)]
    assert sync_routes == []


def test_tile_less_staples_like_water_are_always_in():
    cat = C.load(pathlib.Path(__file__).resolve().parents[2] / 'catalogue')
    empty = {'have': [], 'groups_some': [], 'staples_off': []}
    assert pantry.has(cat, empty, 'water')
    assert not pantry.has(cat, empty, 'milk')



def test_every_write_bumps_rev_so_clients_can_drop_stale_state(tmp_path):
    with make(tmp_path) as c:
        r1 = c.put('/api/pantry/chicken-wings', json={'have': True}).json()['rev']
        r2 = c.put('/api/pantry/chicken-wings', json={'have': False}).json()['rev']
        assert r2 > r1 >= 1 and c.get('/api/pantry').json()['rev'] == r2
