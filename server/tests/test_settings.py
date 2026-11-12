import pytest

from kitchen import db, settings


def test_defaults_and_patch(tmp_path):
    c = db.connect(tmp_path / 'k.db')
    s = settings.get_all(c)
    assert s == {'language': 'en', 'night_start': 23, 'night_end': 6, 'idle_minutes': 2,
                 'sounds': True, 'night_brightness': 20, 'day_brightness': 80,
                 'browse_sites': ['nosalty', 'streetkitchen', 'mindmegette', 'receptneked'], 'browse_custom': []}
    s2 = settings.update(c, {'language': 'hu', 'night_start': 22})
    assert s2['language'] == 'hu' and s2['night_start'] == 22
    assert settings.get_all(db.connect(tmp_path / 'k.db'))['night_start'] == 22   # persisted


@pytest.mark.parametrize('patch', [
    {'language': 'de'}, {'night_start': 24}, {'night_end': -1}, {'idle_minutes': 3}, {'nope': 1},
    {'sounds': 'yes'}, {'night_brightness': 4}, {'day_brightness': 101}, {'night_start': True},
])
def test_rejects_bad(tmp_path, patch):
    c = db.connect(tmp_path / 'k.db')
    with pytest.raises(ValueError):
        settings.update(c, patch)
    assert settings.get_all(c)['language'] == 'en'          # nothing half-applied


def test_migrations_are_idempotent(tmp_path):
    db.connect(tmp_path / 'k.db')
    c = db.connect(tmp_path / 'k.db')
    assert c.execute('select max(version) from schema_version').fetchone()[0] == len(db.MIGRATIONS)


def test_api_settings(client):
    assert client.get('/api/health').json()['ok'] is True
    assert client.get('/api/health').json()['build'] == 'dev'
    assert client.get('/api/settings').json()['language'] == 'en'
    r = client.put('/api/settings', json={'language': 'xx'})
    assert r.status_code == 422
    r = client.put('/api/settings', json={'language': 'hu', 'idle_minutes': 5})
    assert r.status_code == 200 and r.json()['idle_minutes'] == 5
    assert client.get('/api/settings').json()['language'] == 'hu'


def test_shopping_sync_can_be_disabled_from_the_env():
    from kitchen.config import Config
    assert Config.from_env({'KITCHEN_SHOPPING_SYNC_SECONDS': '0'}).shopping_sync_seconds == 0
    assert Config.from_env({}).shopping_sync_seconds == 20


def test_a_failing_multi_statement_migration_leaves_nothing_behind(tmp_path, monkeypatch):
    import sqlite3
    import pytest as _pytest
    monkeypatch.setattr(db, 'MIGRATIONS', db.MIGRATIONS + ['CREATE TABLE half_a (x); CREATE TABLE half_b (']) # syntax error
    with _pytest.raises(sqlite3.Error):
        db.connect(tmp_path / 'k.db')
    c = sqlite3.connect(tmp_path / 'k.db')
    assert c.execute("SELECT count(*) FROM sqlite_master WHERE name = 'half_a'").fetchone()[0] == 0


def test_browse_site_ids_match_the_web_list():
    import json, pathlib
    from kitchen.settings import SITE_IDS
    web = json.loads((pathlib.Path(__file__).resolve().parents[2] / 'web/src/lib/sites.json').read_text())
    assert tuple(s['id'] for s in web['sites']) == SITE_IDS


@pytest.mark.parametrize('value,ok', [
    (['nosalty'], True), ([], True), (['nosalty', 'nosalty'], False), (['google'], False), ('nosalty', False),
])
def test_browse_sites_validation(value, ok):
    from kitchen.settings import SCHEMA
    assert SCHEMA['browse_sites'][1](value) is ok


@pytest.mark.parametrize('value,ok', [
    ([{'name': 'Mentes blog', 'url': 'https://example.hu/'}], True), ([], True),
    ([{'name': '', 'url': 'https://x.hu'}], False), ([{'name': 'x', 'url': 'javascript:alert(1)'}], False),
    ([{'name': 'x', 'url': 'https://x.hu', 'extra': 1}], False), ([{'name': 'x', 'url': 'https://x.hu'}] * 9, False),
])
def test_browse_custom_validation(value, ok):
    from kitchen.settings import SCHEMA
    assert SCHEMA['browse_custom'][1](value) is ok
