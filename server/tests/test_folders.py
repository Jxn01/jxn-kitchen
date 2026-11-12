"""Recipe folders (folders.py + /api/folders, /api/recipes/move): create, rename, nest, move, delete, file recipes."""
import pathlib

import pytest
from fastapi.testclient import TestClient

from kitchen.app import create_app
from kitchen.config import Config
from kitchen import folders

REAL = pathlib.Path(__file__).resolve().parents[2] / 'catalogue'


@pytest.fixture
def c(tmp_path):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL)
    with TestClient(create_app(cfg, shopping_sync_every=None)) as client:
        yield client


def folder(c, name, parent=None):
    r = c.post('/api/folders', json={'name': name, 'parent_id': parent})
    assert r.status_code == 200, r.text
    return r.json()['id']


def recipe(c, title, folder_id=None):
    body = {'title': title, 'ingredients': ['1 db Tojás']}
    if folder_id is not None:
        body['folder_id'] = folder_id
    r = c.post('/api/recipes', json=body)
    assert r.status_code == 200, r.text
    return r.json()['id']


def where(c, rid):
    return c.get(f'/api/recipes/{rid}').json()['folder_id']


def by_id(c):
    return {f['id']: f for f in c.get('/api/folders').json()}


def test_create_nest_and_list_in_name_order(c):
    soups = folder(c, 'Levesek')
    folder(c, 'Édességek')
    hu = folder(c, 'Magyar', soups)
    fs = c.get('/api/folders').json()
    assert [f['name'] for f in fs] == ['Édességek', 'Levesek', 'Magyar']        # accent-folded order
    assert by_id(c)[hu]['parent_id'] == soups and by_id(c)[soups]['folders'] == 1


def test_names_are_trimmed_and_unique_among_siblings_only(c):
    a = folder(c, '  Levesek   gyorsan ')
    assert by_id(c)[a]['name'] == 'Levesek gyorsan'
    r = c.post('/api/folders', json={'name': 'LEVESEK GYORSAN'})
    assert r.status_code == 409 and r.json()['detail']['code'] == 'taken'
    folder(c, 'Levesek gyorsan', a)                                              # same name, other parent: fine
    assert c.post('/api/folders', json={'name': '   '}).status_code == 422
    assert c.post('/api/folders', json={'name': 'x' * 61}).status_code == 422


def test_unknown_parent_is_404(c):
    assert c.post('/api/folders', json={'name': 'A', 'parent_id': 999}).status_code == 404


def test_rename_keeps_the_folder_where_it_is(c):
    top = folder(c, 'Top')
    sub = folder(c, 'Sub', top)
    r = c.patch(f'/api/folders/{sub}', json={'name': 'Renamed'})
    assert r.status_code == 200 and r.json() == {**r.json(), 'name': 'Renamed', 'parent_id': top}


def test_move_to_another_parent_and_to_the_top_level(c):
    a, b = folder(c, 'A'), folder(c, 'B')
    x = folder(c, 'X', a)
    assert c.patch(f'/api/folders/{x}', json={'parent_id': b}).json()['parent_id'] == b
    assert c.patch(f'/api/folders/{x}', json={'parent_id': None}).json()['parent_id'] is None


def test_a_folder_never_goes_inside_itself(c):
    a = folder(c, 'A')
    b = folder(c, 'B', a)
    cc = folder(c, 'C', b)
    for target in (a, b, cc):
        r = c.patch(f'/api/folders/{a}', json={'parent_id': target})
        assert r.status_code == 409 and r.json()['detail']['code'] == 'cycle', target
    assert by_id(c)[a]['parent_id'] is None


def test_moving_into_a_name_clash_is_refused(c):
    a = folder(c, 'A')
    folder(c, 'Same', a)
    other = folder(c, 'Same')
    r = c.patch(f'/api/folders/{other}', json={'parent_id': a})
    assert r.status_code == 409 and r.json()['detail']['code'] == 'taken'


def test_depth_is_capped_for_new_and_moved_folders(c):
    parent = None
    chain = []
    for i in range(folders.MAX_DEPTH):
        parent = folder(c, f'L{i + 1}', parent)
        chain.append(parent)
    r = c.post('/api/folders', json={'name': 'too deep', 'parent_id': parent})
    assert r.status_code == 409 and r.json()['detail']['code'] == 'depth'
    two = folder(c, 'Two')
    folder(c, 'Two-child', two)                                                 # a subtree two levels high
    r = c.patch(f'/api/folders/{two}', json={'parent_id': chain[-2]})            # would end at MAX_DEPTH + 1
    assert r.status_code == 409 and r.json()['detail']['code'] == 'depth'
    assert c.patch(f'/api/folders/{two}', json={'parent_id': chain[-3]}).status_code == 200   # exactly MAX_DEPTH


def test_new_recipe_lands_in_the_folder_it_was_written_in(c):
    f = folder(c, 'F')
    assert where(c, recipe(c, 'In F', f)) == f
    assert where(c, recipe(c, 'Nowhere', 999)) is None                          # a folder that is gone: top level
    assert where(c, recipe(c, 'Top')) is None


def test_editing_a_recipe_keeps_its_folder(c):
    f = folder(c, 'F')
    rid = recipe(c, 'Soup', f)
    r = c.put(f'/api/recipes/{rid}', json={'title': 'Soup 2', 'ingredients': ['1 db Tojás'], 'folder_id': None})
    assert r.status_code == 200 and where(c, rid) == f


def test_move_recipes_in_between_and_out(c):
    a, b = folder(c, 'A'), folder(c, 'B')
    r1, r2 = recipe(c, 'One'), recipe(c, 'Two')
    assert c.post('/api/recipes/move', json={'ids': [r1, r2], 'folder_id': a}).json() == {'moved': 2}
    assert where(c, r1) == a and where(c, r2) == a and by_id(c)[a]['recipes'] == 2
    c.post('/api/recipes/move', json={'ids': [r1], 'folder_id': b})
    assert where(c, r1) == b
    c.post('/api/recipes/move', json={'ids': [r1, r2], 'folder_id': None})
    assert where(c, r1) is None and where(c, r2) is None
    summary = {s['id']: s for s in c.get('/api/recipes').json()}
    assert summary[r1]['folder_id'] is None


def test_a_move_is_all_or_nothing(c):
    a = folder(c, 'A')
    r1 = recipe(c, 'One')
    r = c.post('/api/recipes/move', json={'ids': [r1, 4242], 'folder_id': a})
    assert r.status_code == 404 and where(c, r1) is None
    assert c.post('/api/recipes/move', json={'ids': [r1], 'folder_id': 777}).status_code == 404
    assert c.post('/api/recipes/move', json={'ids': [], 'folder_id': a}).status_code == 422


def test_deleting_a_folder_never_deletes_a_recipe(c):
    top = folder(c, 'Top')
    mid = folder(c, 'Mid', top)
    low = folder(c, 'Low', mid)
    r_mid, r_low = recipe(c, 'In mid', mid), recipe(c, 'In low', low)
    r = c.delete(f'/api/folders/{mid}')
    assert r.status_code == 200 and r.json() == {'recipes': 1, 'folders': 1}
    assert where(c, r_mid) == top and where(c, r_low) == low                     # contents move up one level
    assert by_id(c)[low]['parent_id'] == top and mid not in by_id(c)
    c.delete(f'/api/folders/{top}')
    assert where(c, r_mid) is None and by_id(c)[low]['parent_id'] is None
    assert len(c.get('/api/recipes').json()) == 2
    assert c.delete(f'/api/folders/{top}').status_code == 404


def test_a_lifted_subfolder_whose_name_is_taken_gets_a_number(c):
    folder(c, 'Soups')
    outer = folder(c, 'Outer')
    inner = folder(c, 'soups', outer)
    c.delete(f'/api/folders/{outer}')
    assert by_id(c)[inner]['name'] == 'soups (2)' and by_id(c)[inner]['parent_id'] is None


def test_deleting_a_recipe_in_a_folder_updates_the_count(c):
    f = folder(c, 'F')
    rid = recipe(c, 'Gone', f)
    assert c.delete(f'/api/recipes/{rid}').status_code == 204
    assert by_id(c)[f]['recipes'] == 0


def test_folder_changes_reach_every_screen_as_a_recipes_event(c):
    seen = []
    c.app.state.events.publish = lambda kind, data: seen.append((kind, data))
    f = folder(c, 'F')
    c.patch(f'/api/folders/{f}', json={'name': 'G'})
    rid = recipe(c, 'R')
    c.post('/api/recipes/move', json={'ids': [rid], 'folder_id': f})
    c.delete(f'/api/folders/{f}')
    assert [k for k, d in seen if d == {'folders': True}] == ['recipes'] * 4


def test_the_migration_adds_folders_to_an_existing_database(tmp_path):
    """A kitchen.db from before migration 12 keeps every recipe, all at the top level."""
    import sqlite3
    from kitchen import db
    path = tmp_path / 'old.db'
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute('CREATE TABLE schema_version (version INTEGER PRIMARY KEY)')
    for v, sql in enumerate(db.MIGRATIONS[:11], start=1):
        conn.executescript(f'BEGIN;\n{sql};\nINSERT INTO schema_version (version) VALUES ({v});\nCOMMIT;')
    conn.execute("INSERT INTO recipe (title, lang, origin, created_at, updated_at) VALUES ('Old', 'hu', 'typed', 'x', 'x')")
    conn.close()
    conn = db.connect(path)
    assert conn.execute('SELECT title, folder_id FROM recipe').fetchall()[0][:] == ('Old', None)
    assert conn.execute('SELECT MAX(version) FROM schema_version').fetchone()[0] == len(db.MIGRATIONS)
