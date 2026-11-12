import gzip
import io
import pathlib

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from kitchen import importer
from kitchen.app import create_app
from kitchen.config import Config

SITES = pathlib.Path(__file__).parent / 'fixtures' / 'sites'
REAL = pathlib.Path(__file__).resolve().parents[2] / 'catalogue'


def page(name):
    return (SITES / f'{name}.url').read_text().strip(), gzip.open(SITES / f'{name}.html.gz', 'rt', encoding='utf-8').read()


# Hand-written pages (the private repo tests real sites' saved pages; they are not ours to publish): a schema.org
# @graph with a HowToSection, a plain Recipe with a HowToStep list, and one with plain-string instructions.
@pytest.mark.parametrize('name,title,n_ingr,n_steps,servings,minutes', [
    ('example-lecso', 'Lecsó tojással', 7, 4, 4, 40),
    ('example-paprikas', 'Csirkepaprikás rizzsel', 9, 5, 4, 70),
    ('example-palacsinta', 'Gluténmentes palacsinta', 6, 3, 4, 35),
    ('example-nokedli', 'Nokedli', 5, 3, 4, 30),
])
def test_extract_real_pages(name, title, n_ingr, n_steps, servings, minutes):
    url, html = page(name)
    r = importer.extract(html, url)
    assert r['title'] == title
    assert r['servings'] == servings and r['total_min'] == minutes
    assert r['image_url'] and r['image_url'].startswith('https://')
    if n_ingr: assert len(r['ingredients']) == n_ingr
    else: assert len(r['ingredients']) >= 8
    if n_steps: assert len(r['steps']) == n_steps
    else: assert len(r['steps']) >= 3
    assert r['site'] in url


def test_jsonld_reader_handles_graph_sections_and_durations():
    html = '''<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"WebPage"},
      {"@type":["Recipe"],"name":"Teszt","recipeIngredient":["1 db tojás","2 dl tej"],"recipeYield":["4 adag"],
       "totalTime":"PT1H15M","image":{"url":"https://x.test/a.jpg"},
       "recipeInstructions":[{"@type":"HowToSection","itemListElement":[{"@type":"HowToStep","text":"Egy."},
       {"@type":"HowToStep","text":"Kettő."}]},"Három."]}]}</script>'''
    r = importer.jsonld(html)
    assert r['title'] == 'Teszt' and r['ingredients'] == ['1 db tojás', '2 dl tej'] and r['servings'] == 4
    assert r['total_min'] == 75 and r['image_url'] == 'https://x.test/a.jpg' and r['steps'] == ['Egy.', 'Kettő.', 'Három.']


@pytest.mark.parametrize('url', ['http://192.168.1.2:8123/', 'http://localhost/', 'file:///etc/passwd', 'ftp://x.test/',
                                 'http://127.0.0.1/', 'http://[::1]/', 'http://10.0.0.1/', 'http://169.254.169.254/',
                                 'http://100.64.0.8/', 'http://kitchen.example.com/', 'http://router.home/',
                                 'http://printer.local/'])
def test_ssrf_guard(url):
    def resolve(host):
        return {'kitchen.example.com': ['192.168.1.4'], 'x.test': ['93.184.216.34']}.get(host, ['93.184.216.34'])
    with pytest.raises(importer.ImportRefused):
        importer.check_url(url, resolve)


def make_client(tmp_path, handler):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL)
    app = create_app(cfg, http=httpx.AsyncClient(transport=httpx.MockTransport(handler)), shopping_sync_every=None,
                     resolver=lambda host: ['93.184.216.34'])
    return TestClient(app)


def test_import_endpoint_saves_recipe_with_photo_and_gf_verdict(tmp_path):
    url, html = page('example-nokedli')
    buf = io.BytesIO(); Image.new('RGB', (1600, 1000), (180, 60, 30)).save(buf, 'JPEG')
    def handler(req):
        assert req.url.host == '93.184.216.34'                 # connected to the CHECKED address (no re-resolve)
        assert req.extensions.get('sni_hostname') == req.headers['host'].split(':')[0]
        if req.headers['host'] == 'recipes.example.com' and req.url.path == httpx.URL(url).path:
            return httpx.Response(200, text=html, headers={'content-type': 'text/html; charset=utf-8'})
        if req.headers['host'] == 'recipes.example.com' and req.url.path.startswith('/img/'):
            return httpx.Response(200, content=buf.getvalue(), headers={'content-type': 'image/jpeg'})
        return httpx.Response(404)
    with make_client(tmp_path, handler) as c:
        r = c.post('/api/import', json={'url': url}).json()
        assert r['draft'] is False
        d = c.get(f"/api/recipes/{r['id']}").json()
        assert d['title'] == 'Nokedli' and d['origin'] == 'url' and d['source_site'] == 'recipes.example.com'
        assert d['image'] and c.get(d['image']).status_code == 200
        assert d['verdict']['state'] in ('swaps', 'unknown') and d['verdict']['swaps'] >= 1   # nokedli flour
        assert any(l['item_id'] == 'wheat-flour' and l['gluten'] == 'swap' for l in d['lines'])


def test_page_without_recipe_becomes_a_draft(tmp_path):
    def handler(req):
        return httpx.Response(200, text='<html><head><title>Hírek | Valami</title></head><body>nincs recept</body></html>',
                              headers={'content-type': 'text/html'})
    with make_client(tmp_path, handler) as c:
        r = c.post('/api/import', json={'url': 'https://x.test/hir'}).json()
        assert r['draft'] is True and r['reason'] and r['code'] == 'no_recipe'
        d = c.get(f"/api/recipes/{r['id']}").json()
        assert d['title'] == 'Hírek' and d['source_url'] == 'https://x.test/hir' and d['notes']


def test_unreachable_site_is_a_draft_not_a_crash(tmp_path):
    def handler(req):
        raise httpx.ConnectError('down')
    with make_client(tmp_path, handler) as c:
        r = c.post('/api/import', json={'url': 'https://x.test/recept'})
        assert r.status_code == 200 and r.json()['draft'] is True and r.json()['code'] == 'unreachable'


def test_refused_urls_are_422(tmp_path):
    with make_client(tmp_path, lambda req: httpx.Response(200)) as c:
        r = c.post('/api/import', json={'url': 'file:///etc/passwd'})
        assert r.status_code == 422 and r.json()['detail']['code'] == 'scheme'
        assert c.post('/api/import', json={'url': 'not a url'}).status_code == 422


def test_a_redirect_to_the_lan_is_refused(tmp_path):
    def handler(req):
        return httpx.Response(302, headers={'location': 'http://192.168.1.2:8123/api/'})
    with make_client(tmp_path, handler) as c:
        r = c.post('/api/import', json={'url': 'https://x.test/recept'}).json()
        assert r['draft'] is True and 'home network' in r['reason']


def test_rebinding_resolver_cannot_sneak_in(tmp_path):
    # public for both of our checks, the LAN for any lookup after that — a client that resolved again would land on HA
    answers = iter([['93.184.216.34'], ['93.184.216.34']])
    seen = []
    def handler(req):
        seen.append(req.url.host)
        return httpx.Response(200, text='<title>x</title>', headers={'content-type': 'text/html'})
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL)
    app = create_app(cfg, http=httpx.AsyncClient(transport=httpx.MockTransport(handler)), shopping_sync_every=None,
                     resolver=lambda host: next(answers, ['192.168.1.2']))
    with TestClient(app) as c:
        c.post('/api/import', json={'url': 'https://x.test/recept'})
    assert seen and all(h == '93.184.216.34' for h in seen)


def test_a_second_lookup_turning_hostile_is_refused_not_followed(tmp_path):
    answers = iter([['93.184.216.34'], ['192.168.1.2']])   # public at the first check, LAN at the pin
    seen = []
    def handler(req):
        seen.append(req.url.host)
        return httpx.Response(200)
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL)
    app = create_app(cfg, http=httpx.AsyncClient(transport=httpx.MockTransport(handler)), shopping_sync_every=None,
                     resolver=lambda host: next(answers, ['192.168.1.2']))
    with TestClient(app) as c:
        r = c.post('/api/import', json={'url': 'https://x.test/recept'}).json()
    assert seen == [] and r['draft'] is True


def test_every_reason_code_has_a_sentence_in_both_languages():
    import json
    web = pathlib.Path(__file__).resolve().parents[2] / 'web' / 'src' / 'i18n'
    for lang in ('en', 'hu'):
        strings = json.loads((web / f'{lang}.json').read_text())
        for code in importer.DRAFT_REASONS + ('scheme',):
            assert f'import.reason.{code}' in strings, (lang, code)
