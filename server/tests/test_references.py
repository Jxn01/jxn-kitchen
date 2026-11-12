"""Spec §9: catalogue ids are stable; a removed id maps through catalogue/replaced.yaml, and a start-up check fails
loudly (health 503 + the list) when something stored still points at an id that no longer exists."""
import pathlib
import shutil

from fastapi.testclient import TestClient

from kitchen import catalogue as C
from kitchen.app import create_app
from kitchen.config import Config

FIX = pathlib.Path(__file__).parent / 'fixtures' / 'catalogue'
REAL = pathlib.Path(__file__).resolve().parents[2] / 'catalogue'


def copy_fixture(tmp_path, replaced: str | None = None) -> pathlib.Path:
    d = tmp_path / 'cat'
    shutil.copytree(FIX, d)
    if replaced is not None:
        (d / 'replaced.yaml').write_text(replaced)
    return d


def run(tmp_path, catdir, setup=None):
    cfg = Config(data_dir=tmp_path / 'data', static_dir=None, ha_url=None, ha_token=None, catalogue_dir=catdir, spices=False)
    with TestClient(create_app(cfg, shopping_sync_every=None)) as c:
        if setup:
            setup(c)
        return c.get('/api/health'), c.get('/api/pantry').json(), c.get('/api/shopping').json()


def corrupt(c, sql, *args):
    async def go():
        c.app.state.db.execute(sql, args)
    c.portal.call(go)


def test_the_real_catalogue_has_a_valid_replaced_map():
    cat = C.load(REAL)
    assert C.validate(cat) == []
    assert isinstance(cat.replaced, dict)


def test_removed_ids_are_rewritten_through_replaced(tmp_path):
    catdir = copy_fixture(tmp_path, replaced='')
    def setup(c):                                    # what an older catalogue left behind
        corrupt(c, "INSERT INTO pantry_state (node, have, changed_at) VALUES ('old-wings', 1, 'x')")
        corrupt(c, "INSERT INTO shopping_item (text, item_id, added_at, updated_at) VALUES ('Wings', 'old-wings', 'x', 'x')")
    run(tmp_path, catdir, setup)
    (catdir / 'replaced.yaml').write_text('old-wings: chicken-wings\n')
    health, pantry, shopping = run(tmp_path, catdir)          # restart with the map
    assert health.status_code == 200
    assert 'chicken-wings' in pantry['have'] and shopping[0]['item_id'] == 'chicken-wings'


def test_a_dangling_id_fails_loudly(tmp_path):
    catdir = copy_fixture(tmp_path, replaced='')
    def setup(c):
        corrupt(c, "INSERT INTO pantry_state (node, have, changed_at) VALUES ('vanished-item', 1, 'x')")
    run(tmp_path, catdir, setup)
    health, _, _ = run(tmp_path, catdir)
    assert health.status_code == 503
    assert any('vanished-item' in d for d in health.json()['dangling'])


def test_replaced_map_is_validated(tmp_path):
    catdir = copy_fixture(tmp_path, replaced='old-x: no-such-item\nchicken-wings: rice-white\n')
    errors = C.validate(C.load(catdir))
    assert any('no-such-item' in e for e in errors)                  # target must exist
    assert any('chicken-wings' in e for e in errors)                 # a live id cannot be "removed"
