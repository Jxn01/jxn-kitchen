"""Every file of the built web app carries an explicit cache rule (WebFiles in app.py)."""
import pytest
from fastapi.testclient import TestClient

from kitchen.app import create_app
from kitchen.config import Config


@pytest.fixture
def web(tmp_path):
    static = tmp_path / 'static'
    (static / 'assets').mkdir(parents=True)
    (static / 'fonts').mkdir()
    (static / 'index.html').write_text('<!doctype html><title>k</title>')
    (static / 'sw.js').write_text("import { x } from './sw-strategy.js';")
    (static / 'sw-strategy.js').write_text('export const x = 1;')
    (static / 'sprite.svg').write_text('<svg/>')
    (static / 'assets' / 'index-AbC123.js').write_text('console.log(1)')
    (static / 'fonts' / 'a.woff2').write_bytes(b'\\0')
    cfg = Config(data_dir=tmp_path / 'data', static_dir=static, ha_url=None, ha_token=None)
    (tmp_path / 'data').mkdir()
    with TestClient(create_app(cfg)) as c:
        yield c


@pytest.mark.parametrize('path', ['/', '/index.html', '/sw.js?v=abc', '/sw-strategy.js', '/sprite.svg', '/fonts/a.woff2'])
def test_a_file_that_keeps_its_name_across_builds_revalidates(web, path):
    r = web.get(path)
    assert r.status_code == 200
    assert r.headers['cache-control'] == 'no-cache'


def test_a_hashed_asset_is_immutable(web):
    r = web.get('/assets/index-AbC123.js')
    assert r.status_code == 200
    assert r.headers['cache-control'] == 'public, max-age=31536000, immutable'


def test_a_revalidation_answers_304_and_keeps_the_rule(web):
    etag = web.get('/sw-strategy.js').headers['etag']
    r = web.get('/sw-strategy.js', headers={'If-None-Match': etag})
    assert r.status_code == 304


def test_the_api_keeps_its_own_rules(web):
    assert 'immutable' not in web.get('/api/health').headers.get('cache-control', '')
