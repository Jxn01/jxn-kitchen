#!/usr/bin/env python3
"""Touch-target audit (every touch target >= 64 CSS px). Exit 1 when anything is smaller.

Runs the scratch build (scripts/build-web.sh) on a local server with demo data, opens each screen in headless Chrome
at the kiosk's 1024x640 CSS px as the kiosk (?kiosk=1), opens the overlays (on-screen keyboard, match picker, toast),
and measures every button, link, input and [role=button] on screen: both sides must be >= 64 px.

  ~/.local/share/venvs/jxn-kitchen/bin/python scripts/touch-audit.py [route ...]
  ~/.local/share/venvs/jxn-kitchen/bin/python scripts/touch-audit.py --selftest   (its positive control)
A target out of view or clipped (below the fold, past the end of a scrolling row) is measured scrolled into view.

A target that genuinely cannot be 64 px carries `data-touch="<reason>"` in the markup; the audit lists those
separately so every exception stays visible.
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

REPO = pathlib.Path(__file__).resolve().parents[1]
CACHE = pathlib.Path(os.environ.get('KITCHEN_SCRATCH', pathlib.Path.home() / '.cache/jxn-kitchen'))
VENV = pathlib.Path.home() / '.local/share/venvs/jxn-kitchen'
PORT, CDP_PORT, MIN = 8766, 19331, 64

# (route, steps) — a step is JS run after the route settles, to open an overlay before measuring
SCREENS: list[tuple[str, list[str]]] = [
    ('/', []), ('/settings', []), ('/pantry', []), ('/pantry/meat', []), ('/pantry/meat/chicken', []),
    ('/pantry-have', []), ('/shopping', ["document.querySelector('.add input').focus()"]),
    ('/recipes', []), ('/recipes', ["document.querySelector('.hbtn:not(.new)').click()",
                                    "document.querySelector('.import input').focus()"]),
    ('/recipe/1', []), ('/recipe/1', ["document.querySelector('.ing li button, .ing li[role=button]')?.click()"]),
    ('/recipe/1/edit', []), ('/recipe/new', ["document.querySelector('textarea').focus()"]),
    ('/pantry/meat', ["document.querySelector('button.item').click()"]),   # a pantry toggle -> its toast (Undo)
    ('/shopping', ["document.querySelector('.list .del').click()"]),      # remove -> toast with Undo
    ('/browse', []), ('/browse', ["document.querySelector('.search input').focus()"]),
    ('/add?url=https%3A%2F%2Fwww.nosalty.hu%2Frecept%2Fpaprikas-csirke', []),
    ('/recipes', ["[...document.querySelectorAll('.f')][1].click()"]),   # What can I cook (not an overlay: see below)
    ('/knowhow', []), ('/knowhow', ["document.querySelector('.search').focus()"]),
    ('/knowhow/blends/season', []), ('/knowhow/blends/diy', []), ('/knowhow/cuts/pork', []), ('/lab/mascot?still=1', []),
    # the infographics: one page per chart type and the three knife drawings
    ('/knowhow/conversions/hungarian-measures', []), ('/knowhow/hungarian/porkolt-paprikas-gulyas', []), ('/knowhow/celiac/basics', []),
    ('/knowhow/temperatures/food-safety', []), ('/knowhow/spices/paprika', []), ('/knowhow/baking/bread', []),
    ('/knowhow/knife/onion', []), ('/knowhow/knife/sharpening', []), ('/knowhow/knife/cuts', []),
    # the know-how expansion: every new chart type and drawing
    ('/knowhow/appliances/where', []), ('/knowhow/appliances/rice-cooker', []), ('/knowhow/spices/warm', []),
    ('/knowhow/coffee/french-press', []), ('/knowhow/coffee/moka', []), ('/knowhow/coffee/milk-drinks', []),
    ('/knowhow/coffee/nespresso', []), ('/knowhow/eggs/boiling', []), ('/knowhow/eggs/freshness', []),
    ('/knowhow/storage/fridge', []), ('/knowhow/grains/ratios', []), ('/knowhow/cheese/uses', []),
    ('/knowhow/temperatures', []), ('/knowhow/temperatures/sugar', []), ('/knowhow/temperatures/oils', []),
    ('/knowhow/temperatures/oven', []), ('/knowhow/cuts/beef', []), ('/knowhow/celiac/labels', []),
    ('/knowhow/blends/classics', []), ('/knowhow/methods/roast', []),
    ('/timers', []), ('/cook/1', []), ('/cook/1', ["document.querySelector('header .ing').click()"]),   # the drawer
    ('/cook/1', ["for (let i = 0; i < 30; i++) document.querySelector('nav .next')?.click()"]),        # used up?
    # Spices: the shelf, a blend, the engine — every tab, the notes with the keyboard, a jar's note sheet
    ('/spices', []), ('/spices/1', []), ('/spices/new', []), ('/spices/4/edit', []),
    *[('/spices/4/edit', [f"[...document.querySelectorAll('.sg')][{i}].click()"]) for i in (1, 2, 3, 4)],
    ('/spices/4/edit', ["[...document.querySelectorAll('.tab')].at(-1).click()", "document.querySelector('.notes textarea').focus()"]),
    ('/spices/new', ["new Promise((r) => { const b = document.querySelector('.rj'), x = b.getBoundingClientRect();"
                        " b.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, clientX: x.x + 9, clientY: x.y + 9})); setTimeout(r, 800); })"]),
    # Sauces: the sideboard, a sauce, the engine — every tab, the notes with the keyboard, both sheets, cook mode
    ('/sauces', []), ('/sauces/1', []), ('/sauces/new', []), ('/sauces/4/edit', []),
    *[('/sauces/4/edit', [f"[...document.querySelectorAll('.sg')][{i}].click()"]) for i in (1, 2, 3, 4)],
    ('/sauces/4/edit', ["[...document.querySelectorAll('.tab')].at(-1).click()", "document.querySelector('.notes textarea').focus()"]),
    ('/sauces/4/edit', ["[...document.querySelectorAll('.tab')].at(-2).click()"]),                       # the rack's shelves
    ('/sauces/4/edit', ["document.querySelector('.hbtn.fam').click()"]),                                 # the family sheet
    ('/sauces/new', ["document.querySelector('.typed').click()", "document.querySelector('.tin').focus()"]),   # something else…
    ('/cook/sauce/1', []), ('/cook/sauce/1', ["document.querySelector('header .ing').click()"]),
    ('/cook/sauce/1', ["for (let i = 0; i < 30; i++) document.querySelector('nav .next')?.click()"]),
]

MEASURE = '''(() => {
  // The HIT AREA, not the box: probe a 64x64 square around the centre with elementFromPoint, so a pill with an
  // invisible ::after tap zone counts as what a finger meets, and a covered element is skipped (it can't be tapped).
  const R = %d / 2 - 1, out = [], ok = [];
  const clampX = (x) => Math.min(innerWidth - 1, Math.max(0, x)), clampY = (y) => Math.min(innerHeight - 1, Math.max(0, y));
  // clipped by the viewport or by a scrolling ancestor (a chip at the end of a row, a slot half under the tray): the
  // user scrolls it into view first, so it is measured scrolled into view — one that is still clipped there is real
  const clipped = (el, r) => {
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (!/(auto|scroll|hidden)/.test(cs.overflowX + cs.overflowY)) continue;
      const q = p.getBoundingClientRect();
      if (r.left < q.left - 0.5 || r.right > q.right + 0.5 || r.top < q.top - 0.5 || r.bottom > q.bottom + 0.5) return true;
    }
    return r.left < 0 || r.right > innerWidth || r.top < 0 || r.bottom > innerHeight;
  };
  const off = (r) => r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth;
  for (const el of document.querySelectorAll('button, a[href], input, select, textarea, [role=button]')) {
    let r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    // out of view or clipped (below the fold, past the end of a row): measured where scrolling brings it — before
    // a target wholly out of view must not be skipped, or nothing past a scroll edge is ever measured
    if (off(r) || clipped(el, r)) { el.scrollIntoView({ block: 'nearest', inline: 'nearest' }); r = el.getBoundingClientRect(); }
    if (off(r)) continue;                       // unreachable by scrolling (off-canvas): not a target
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none' || el.closest('[aria-hidden="true"]') || el.type === 'hidden') continue;
    const mine = (x, y) => { const h = document.elementFromPoint(clampX(x), clampY(y));
      return !!h && (h === el || el.contains(h) || (h.tagName === 'LABEL' && h.contains(el))); };
    // partly under an overlay (the keyboard, a toast): the user scrolls it into view, so not a size defect
    const under = (x, y) => { const h = document.elementFromPoint(clampX(x), clampY(y));
      const ov = h?.closest('.kb, .toast, .sheet'); return !!ov && !ov.contains(el); };
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const probes = [[cx - R, cy], [cx + R, cy], [cx, cy - R], [cx, cy + R]];
    if (!mine(cx, cy) || probes.some(([x, y]) => under(x, y))) continue;
    if (probes.every(([x, y]) => mine(x, y))) continue;
    const d = { tag: el.tagName.toLowerCase(), cls: String(el.className?.baseVal ?? el.className ?? '').split(' ').filter((c) => !c.startsWith('svelte-')).join('.'),
                text: (el.getAttribute('aria-label') || el.textContent || el.placeholder || '').trim().slice(0, 28),
                w: Math.round(r.width), h: Math.round(r.height),
                // which probe missed and what it met instead: a box >= 64 px that fails is covered or clipped there
                miss: probes.filter(([x, y]) => !mine(x, y)).map(([x, y]) => { const h = document.elementFromPoint(clampX(x), clampY(y));
                  return `${Math.round(x)},${Math.round(y)} ${h ? h.tagName.toLowerCase() + '.' + String(h.className?.baseVal ?? h.className ?? '').split(' ').filter((c) => !c.startsWith('svelte-')).join('.') : 'nothing'}`; }) };
    (el.closest('[data-touch]') ? ok : out).push({ ...d, why: el.closest('[data-touch]')?.dataset.touch });
  }
  return JSON.stringify({ out, ok, kb: !!document.querySelector('.kb'), toast: !!document.querySelector('.toast'),
                          sheet: [...document.querySelectorAll('.sheet')].some((e) => e.getClientRects().length > 0) });
})()''' % MIN


from cdp import CHROME_FLAGS, Page   # noqa: E402 — the shared client (scripts/cdp.py): it reads the socket continuously


def seed(base: str) -> None:
    def send(method: str, path: str, body) -> None:
        req = urllib.request.Request(base + path, json.dumps(body).encode(), {'Content-Type': 'application/json'},
                                     method=method)
        urllib.request.urlopen(req).read()
    recipes = json.loads(subprocess.run([str(VENV / 'bin/python'), str(REPO / 'scripts/demo-recipes.py')],
                                        capture_output=True, text=True, check=True).stdout)
    for r in recipes:
        send('POST', '/api/recipes', r)
    for node in ('onion', 'eggs', 'butter', 'chicken-breast', 'group:pork'):
        send('PUT', f'/api/pantry/{node}', {'have': True})
    for t in ('Tej', 'Alufólia'):
        send('POST', '/api/shopping', {'text': t})


async def audit(routes: list[tuple[str, list[str]]]) -> int:
    data = pathlib.Path(tempfile.mkdtemp(prefix='kk-touch-'))
    env = dict(os.environ, KITCHEN_SHOPPING_SYNC_SECONDS='0', KITCHEN_DATA_DIR=str(data),
               KITCHEN_STATIC_DIR=str(CACHE / 'web/dist'), PYTHONPATH=str(REPO / 'server'))
    srv = subprocess.Popen([str(VENV / 'bin/uvicorn'), 'kitchen.main:app', '--host', '127.0.0.1', '--port', str(PORT),
                            '--log-level', 'warning'], env=env)
    chrome_bin = shutil.which('google-chrome-stable') or shutil.which('chromium')
    chrome = subprocess.Popen([chrome_bin, '--headless=new', *CHROME_FLAGS, '--disable-gpu', '--hide-scrollbars',
                               f'--remote-debugging-port={CDP_PORT}', '--window-size=1024,640',
                               '--force-device-scale-factor=1.25', f'--user-data-dir={data / "chrome"}', 'about:blank'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f'http://127.0.0.1:{PORT}'
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(base + '/api/health').read()
                json.load(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json/list'))
                break
            except OSError:
                time.sleep(0.2)
        seed(base)
        target = next(t for t in json.load(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json/list'))
                      if t['type'] == 'page')
        bad = 0
        async with websockets.connect(target['webSocketDebuggerUrl'], max_size=None) as ws:
            page = Page(ws)
            await page.call('Page.enable')
            await page.call('Emulation.setFocusEmulationEnabled', {'enabled': True})   # headless: let focus() fire
            await page.call('Page.navigate', {'url': f'{base}/?kiosk=1&shot=1#/'})
            await asyncio.sleep(2.5)
            for route, steps in routes:
                await page.js(f"location.hash = '#{route}'; document.activeElement?.blur?.()")
                await asyncio.sleep(1.2)
                for s in steps:
                    await page.js(s)
                    await asyncio.sleep(0.8)
                res = json.loads(await page.js(MEASURE))
                label = route + (' +' + '+'.join(k for k in ('kb', 'toast', 'sheet') if res[k]) if steps else '')
                if steps and not any(res[k] for k in ('kb', 'toast', 'sheet')) and 'click()' not in steps[-1]:
                    print(f'NOOVERLAY {route}: the overlay step opened nothing — fix the step, the audit is blind there')
                    bad += 1
                for d in res['out']:
                    bad += 1
                    print(f'SMALL {label:22} {d["w"]:3}x{d["h"]:<3} {d["tag"]}.{d["cls"]}  "{d["text"]}"  missed at: {"; ".join(d.get("miss", []))}')
                for d in res['ok']:
                    print(f'EXEMPT {label:21} {d["w"]:3}x{d["h"]:<3} {d["tag"]}.{d["cls"]}  ({d["why"]})')
                # leave overlays closed for the next screen
                await page.js("document.activeElement?.blur?.(); document.querySelector('.scrim')?.click()")
        print(f'{bad} target(s) under {MIN} px' if bad else f'all touch targets >= {MIN} px')
        return 1 if bad else 0
    finally:
        chrome.terminate(); srv.terminate()
        chrome.wait(10); srv.wait(10)
        shutil.rmtree(data, ignore_errors=True)


SELFTEST_HTML = ('<!doctype html><html><body style="margin:0"><div style="display:flex;gap:6px;overflow-x:auto;width:1024px;padding:8px 18px 0">'
                 + ''.join(f'<button style="flex:none;width:112px;height:64px;border-radius:999px">pill {i}</button>' for i in range(10))
                 + '<button style="flex:none;width:40px;height:40px">far</button></div>'
                 '<button style="width:40px;height:40px;margin:20px">small</button></body></html>')


async def selftest() -> int:
    """The audit's positive control: a row of 64 px pills running off the edge of a scroller (none may be flagged — a
    clipped target is measured scrolled into view) and two 40 px buttons, one visible and one past the row's end (both
    must be: a target out of view must still be measured)."""
    from urllib.parse import quote
    data = pathlib.Path(tempfile.mkdtemp(prefix='kk-touch-self-'))
    chrome_bin = shutil.which('google-chrome-stable') or shutil.which('chromium')
    chrome = subprocess.Popen([chrome_bin, '--headless=new', *CHROME_FLAGS, '--disable-gpu', f'--remote-debugging-port={CDP_PORT}',
                               '--window-size=1024,640', f'--user-data-dir={data / "chrome"}', 'data:text/html,' + quote(SELFTEST_HTML)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                pages = json.load(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json/list', timeout=2))
                break
            except OSError:
                time.sleep(0.1)
        target = [t for t in pages if t['type'] == 'page'][0]
        async with websockets.connect(target['webSocketDebuggerUrl'], max_size=None) as ws:
            pg = Page(ws)
            await asyncio.sleep(1)
            got = sorted(d['text'] for d in json.loads(await pg.js(MEASURE))['out'])
        ok = got == ['far', 'small']
        print(f"selftest {'OK' if ok else 'FAILED'}: flagged {got}, want ['far', 'small']")
        return 0 if ok else 1
    finally:
        chrome.terminate(); chrome.wait(10)
        shutil.rmtree(data, ignore_errors=True)


if __name__ == '__main__':
    only = sys.argv[1:]
    if only == ['--selftest']:
        sys.exit(asyncio.run(selftest()))
    sys.exit(asyncio.run(audit([s for s in SCREENS if not only or s[0] in only])))
