"""Digitising: printed recipe -> OCR -> a draft recipe. Pages are rendered here (DejaVu), so the tests
need no fixture images; OCR needs the hun/eng models (scripts/get-tessdata.sh)."""
import io
import os
import pathlib
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from kitchen import ocr

HAS_OCR = shutil.which('tesseract') is not None and pathlib.Path(os.environ.get('TESSDATA_PREFIX', '/usr/share/tessdata'),
                                                                   'hun.traineddata').exists()
needs_ocr = pytest.mark.skipif(not HAS_OCR, reason='tesseract with hun+eng models: run scripts/get-tessdata.sh')
FONT = '/usr/share/fonts/TTF/DejaVuSans.ttf'

HU = """Rakott krumpli
4 személyre

Hozzávalók:
1 kg burgonya
6 db tojás
30 dkg füstölt kolbász
4 dl tejföl
5 dkg vaj
só, bors

Elkészítés:
1. A burgonyát héjában megfőzzük, majd
meghámozzuk és felkarikázzuk.
2. A tojásokat 10 percig főzzük, majd felkarikázzuk.
3. Egy kivajazott tálba rétegezzük a burgonyát,
a tojást és a kolbászt.
4. Tejföllel locsoljuk, és 180 fokon 40 percig sütjük."""

EN = """Pancakes
Serves 4

Ingredients
200 g rice flour
2 eggs
300 ml milk
1 pinch of salt

Method
Whisk everything into a smooth batter.
Rest it for 15 minutes.
Fry thin pancakes in a hot pan, 1 minute a side."""


def page(text: str, rotate: int = 0, fmt: str = 'PNG') -> bytes:
    img = Image.new('RGB', (1240, 1754), 'white')
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 30)
    y = 90
    for line in text.split('\n'):
        d.text((90, y), line, fill=(25, 25, 25), font=f)
        y += 46
    if rotate:
        img = img.rotate(rotate, expand=True, fillcolor='white')
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def test_structuring_without_ocr():
    r = ocr.recipe_from_text(HU)
    assert r['title'] == 'Rakott krumpli' and r['servings'] == 4
    assert r['ingredients'][:2] == ['1 kg burgonya', '6 db tojás'] and len(r['ingredients']) == 6
    assert len(r['steps']) == 4
    assert r['steps'][0] == 'A burgonyát héjában megfőzzük, majd meghámozzuk és felkarikázzuk.'
    e = ocr.recipe_from_text(EN)
    assert e['title'] == 'Pancakes' and e['servings'] == 4 and len(e['ingredients']) == 4 and len(e['steps']) == 3


def test_structuring_without_headers_and_with_hyphenation():
    text = "Gyors leves\n2 adag\n1 l víz\n2 db sárgarépa\n\nA vizet felforraljuk, bele-\ntesszük a répát.\n\nSózzuk."
    r = ocr.recipe_from_text(text)
    assert r['title'] == 'Gyors leves' and r['servings'] == 2
    assert r['ingredients'] == ['1 l víz', '2 db sárgarépa']
    assert r['steps'] == ['A vizet felforraljuk, beletesszük a répát.', 'Sózzuk.']


def test_nothing_readable_is_still_a_draft():
    r = ocr.recipe_from_text('   \n\n ')
    assert r['title'] == '' and r['ingredients'] == [] and r['steps'] == []


@needs_ocr
def test_ocr_reads_a_hungarian_card():
    r = ocr.recipe_from_text(ocr.image_text(page(HU)))
    assert r['title'] == 'Rakott krumpli' and r['servings'] == 4
    assert '30 dkg füstölt kolbász' in r['ingredients'] and len(r['steps']) == 4


@needs_ocr
def test_ocr_reads_an_english_card():
    r = ocr.recipe_from_text(ocr.image_text(page(EN)))
    assert r['title'] == 'Pancakes' and '200 g rice flour' in r['ingredients']


@needs_ocr
def test_ocr_turns_a_sideways_scan_upright():
    r = ocr.recipe_from_text(ocr.image_text(page(HU, rotate=90)))
    assert r['title'] == 'Rakott krumpli' and len(r['ingredients']) >= 5


@needs_ocr
def test_a_pdf_of_two_cards_is_two_pages():
    a, b = Image.open(io.BytesIO(page(HU))), Image.open(io.BytesIO(page(EN)))
    buf = io.BytesIO()
    a.save(buf, 'PDF', save_all=True, append_images=[b], resolution=150)
    pages = ocr.pdf_pages(buf.getvalue())
    assert len(pages) == 2
    assert ocr.recipe_from_text(ocr.image_text(pages[1]))['title'] == 'Pancakes'


# --- POST /api/scan and the scan inbox ------------------------------------------------------------------------
from fastapi.testclient import TestClient  # noqa: E402

from kitchen.app import create_app  # noqa: E402
from kitchen.config import Config  # noqa: E402

REAL = pathlib.Path(__file__).resolve().parents[2] / 'catalogue'


def make(tmp_path, scans=None):
    cfg = Config(data_dir=tmp_path / 'data', static_dir=None, ha_url=None, ha_token=None, catalogue_dir=REAL,
                 scans_dir=scans)
    return TestClient(create_app(cfg, shopping_sync_every=None, timers_autorun=False, scans_autorun=False))


@needs_ocr
def test_a_photo_becomes_a_draft_recipe_with_the_scan_as_its_photo(tmp_path):
    with make(tmp_path) as c:
        r = c.post('/api/scan', content=page(HU), headers={'Content-Type': 'image/png'})
        assert r.status_code == 200, r.text
        (rid,) = r.json()['ids']
        d = c.get(f'/api/recipes/{rid}').json()
        assert d['title'] == 'Rakott krumpli' and d['origin'] == 'scan' and 'scan' in d['tags'] and d['image']
        assert d['servings'] == 4 and len(d['steps']) == 4
        items = {l['item_id'] for l in d['lines']}
        assert {'potatoes', 'eggs'} <= items or len(items - {None}) >= 4
        assert any(t['seconds'] == 600 for s in d['steps'] for t in s['timers'])     # "10 percig" -> a timer chip


@needs_ocr
def test_a_pdf_stack_becomes_one_draft_per_page(tmp_path):
    a, b = Image.open(io.BytesIO(page(HU))), Image.open(io.BytesIO(page(EN)))
    buf = io.BytesIO()
    a.save(buf, 'PDF', save_all=True, append_images=[b], resolution=150)
    with make(tmp_path) as c:
        ids = c.post('/api/scan', content=buf.getvalue(), headers={'Content-Type': 'application/pdf'}).json()['ids']
        assert [c.get(f'/api/recipes/{i}').json()['title'] for i in ids] == ['Rakott krumpli', 'Pancakes']


def test_not_an_image_is_refused(tmp_path):
    with make(tmp_path) as c:
        assert c.post('/api/scan', content=b'hello', headers={'Content-Type': 'text/plain'}).status_code == 422
        assert c.post('/api/scan', content=b'').status_code == 422


@needs_ocr
def test_the_inbox_imports_each_scan_once(tmp_path):
    scans = tmp_path / 'scans'
    scans.mkdir()
    (scans / 'stack-001.png').write_bytes(page(HU))
    (scans / 'notes.txt').write_text('not a scan')
    old = os.stat(scans / 'stack-001.png').st_mtime - 120
    os.utime(scans / 'stack-001.png', (old, old))                     # settled: not still being written
    with make(tmp_path, scans) as c:
        c.portal.call(c.app.state.scans.poll)
        c.portal.call(c.app.state.scans.poll)                          # again: nothing new
        titles = [r['title'] for r in c.get('/api/recipes').json()]
        assert titles == ['Rakott krumpli']
    with make(tmp_path, scans) as c:                                   # a restart: still once
        c.portal.call(c.app.state.scans.poll)
        assert len(c.get('/api/recipes').json()) == 1
        assert c.get('/api/scans').json()['imported'] == 1


# --- scan upload hardening -----------------------------------------------------------------------
def _png_header(w, h):
    import struct
    import zlib
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0)) + chunk(b'IEND', b'')


def test_ocr_refuses_a_decompression_bomb_before_decoding():
    with pytest.raises(ocr.OcrFailed):
        ocr.image_text(_png_header(30000, 30000))                       # 900 Mpx claimed in a few bytes


def test_the_scan_endpoint_refuses_a_bomb_and_odd_formats(tmp_path):
    import io as _io
    with make(tmp_path) as c:
        assert c.post('/api/scan', content=_png_header(30000, 30000), headers={'Content-Type': 'image/png'}).status_code == 422
        buf = _io.BytesIO(); Image.new('RGB', (40, 40)).save(buf, 'ICO')
        assert c.post('/api/scan', content=buf.getvalue(), headers={'Content-Type': 'image/x-icon'}).status_code == 422


@needs_ocr
def test_pdf_pages_are_rendered_at_a_capped_size():
    """A PDF page can declare any size; it must not become an enormous bitmap."""
    big = Image.new('RGB', (1000, 1000), 'white')
    buf = io.BytesIO()
    big.save(buf, 'PDF', resolution=5)                                  # 1000 px at 5 dpi = a 200-inch page
    (p,) = ocr.pdf_pages(buf.getvalue())
    assert max(Image.open(io.BytesIO(p)).size) <= ocr.MAX_PAGE_PX


@needs_ocr
def test_a_poison_file_neither_loops_nor_blocks_the_rest(tmp_path, monkeypatch):
    scans = tmp_path / 'scans'
    scans.mkdir()
    for name, data in (('a-bad.png', page(HU)), ('b-good.png', page(EN))):
        (scans / name).write_bytes(data)
        old = os.stat(scans / name).st_mtime - 120
        os.utime(scans / name, (old, old))
    real = ocr.image_text
    calls = []
    def flaky(data):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError('boom')                                  # an unexpected crash on the first file
        return real(data)
    monkeypatch.setattr(ocr, 'image_text', flaky)
    with make(tmp_path, scans) as c:
        c.portal.call(c.app.state.scans.poll)
        c.portal.call(c.app.state.scans.poll)
        titles = [r['title'] for r in c.get('/api/recipes').json()]
        assert 'Pancakes' in titles                                     # the good file got through
        assert len(calls) == 2                                          # and the bad one was not retried
        assert c.get('/api/scans').json()['imported'] == 2
