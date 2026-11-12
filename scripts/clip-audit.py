#!/usr/bin/env python3
"""Clipped-text audit: no text may be cut off by a box that hides its overflow. Exit 1 when any is.

Why (2026-11-11): on the owner's iPhone every home tile's subtitle was cut off at the tile's bottom edge — a row shorter
than its content, `overflow: hidden` on the tile — and Chrome hid it by squashing the icon plate into an oval instead,
so no kiosk screenshot ever showed it. This audit measures text against its clipping boxes in the browser, so the class
is caught on any screen, at any size, in either language, whatever the engine chose to sacrifice.

Runs the scratch build (scripts/build-web.sh) on a local server with the touch audit's demo data, opens every screen of
scripts/touch-audit.py (without its overlay steps) in headless Chrome at each size and language, and for every visible
text node checks its line boxes against each ancestor whose overflow is `hidden` or `clip`: a line box that sticks out
of that box is clipped text. An ancestor that SCROLLS in an axis makes the overflow reachable in that axis, so it
does not count. Tolerance: 2 px across, 0.3 em down/up — a display font's glyph box is taller than a tight
`line-height` (the tile titles: 1.05) without anything being cut; a missing line overflows by a whole line.

Deliberate truncation — `text-overflow: ellipsis` or `-webkit-line-clamp` on the text's element or the clipping box —
is listed as TRUNC and does not fail. A box that may clip text on purpose carries `data-clip="<reason>"`; its text is
listed as EXEMPT, so every exception stays visible.

  ~/.local/share/venvs/jxn-kitchen/bin/python scripts/clip-audit.py [route ...]
  ~/.local/share/venvs/jxn-kitchen/bin/python scripts/clip-audit.py --sizes iphone-app,se --langs hu [route ...]
  ~/.local/share/venvs/jxn-kitchen/bin/python scripts/clip-audit.py --selftest     (its positive control)
Sizes (as scripts/screens.sh): kiosk 1024x640 @1.25 (?kiosk=1), 720p 1280x720, iphone-app 393x759 @3,
se 375x667 @2, land 844x390 @3 — measured at 1x (layout is in CSS px; CLIP_DPR=1 keeps the real density). Default:
all of them, both languages.

Runtime: ~1 minute per size x language pass; a full run ~2.5 minutes with one process per size side by side (CLIP_PORT
moves a run's ports: --sizes kiosk on 8800, --sizes 720p on 8810, ...). It once took ~7 minutes a pass and hung outright:
the shared Chrome flags (scripts/chrome-flags.txt) and the shared client (scripts/cdp.py) say why.
"""
from __future__ import annotations

import asyncio
import importlib.util
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
_spec = importlib.util.spec_from_file_location('touch_audit', REPO / 'scripts/touch-audit.py')
touch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(touch)
Page, seed, CHROME_FLAGS = touch.Page, touch.seed, touch.CHROME_FLAGS
CACHE, VENV = touch.CACHE, touch.VENV
# CLIP_PORT moves the app server and Chrome's debugging port together, so passes can run side by side
PORT = int(os.environ.get('CLIP_PORT', '8767'))
CDP_PORT = PORT + 10565        # 19332 for the default
SELFTEST_CDP_PORT = PORT + 10566   # its own: a self-test next to a running audit would otherwise measure the audit's page

SIZES = {  # name: (width, height, device scale factor, kiosk mode)
    'kiosk': (1024, 640, 1.25, True), '720p': (1280, 720, 1, False), 'iphone-app': (393, 759, 3, False),
    'se': (375, 667, 2, False), 'land': (844, 390, 3, False),
}
ROUTES = list(dict.fromkeys(r for r, steps in touch.SCREENS if not steps))

MEASURE = r'''(() => {
  const out = [], trunc = [], exempt = [];
  const label = (e) => e.tagName.toLowerCase() + '.' + String(e.className?.baseVal ?? e.className ?? '').split(' ')
                         .filter((c) => c && !c.startsWith('svelte-')).join('.');
  // each element's overflow and box, read once per page: walking every text node's ancestors without a cache asked the
  // browser for thousands of styles on a dense know-how page and made a full run take ~70 minutes (2026-11-11)
  const styles = new Map(), boxes = new Map();
  const S = (e) => { let v = styles.get(e); if (!v) { const c = getComputedStyle(e);
    v = { ox: c.overflowX, oy: c.overflowY, to: c.textOverflow, lc: c.webkitLineClamp }; styles.set(e, v); } return v; };
  const box = (e) => { let v = boxes.get(e); if (!v) { const q = e.getBoundingClientRect();
    v = { q, L: q.left + e.clientLeft, T: q.top + e.clientTop }; v.R = v.L + e.clientWidth; v.B = v.T + e.clientHeight;
    boxes.set(e, v); } return v; };
  const truncates = (e) => { const s = S(e); return s.to === 'ellipsis' || (s.lc && s.lc !== 'none'); };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT,
    { acceptNode: (n) => (n.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT) });
  const range = document.createRange();
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const el = n.parentElement;
    if (!el || el.closest('svg, script, style, noscript, [aria-hidden="true"]')) continue;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none' || +st.opacity === 0) continue;
    range.selectNodeContents(n);
    const rects = [...range.getClientRects()].filter((r) => r.width > 0.5 && r.height > 0.5);
    if (!rects.length) continue;
    const em = parseFloat(st.fontSize) || 16, tolY = 0.3 * em, tolX = 2;
    // what is measured, per axis: the text's line boxes — until the walk passes a box that SCROLLS in that axis. Past
    // it, only the part of a line box inside the scroller's box can be cut by a higher box: a line outside it scrolls
    // into view, so it drops out (a panel scrolling inside a clipped body is fine), while a line sitting in the part of
    // a scroller that its parent cuts off is still caught (a scroller that is itself too tall for its box)
    let rx = rects, ry = rects;
    const clip = (list, q, axis) => list.map((r) => axis === 'x'
        ? { left: Math.max(r.left, q.left), right: Math.min(r.right, q.right), top: r.top, bottom: r.bottom }
        : { left: r.left, right: r.right, top: Math.max(r.top, q.top), bottom: Math.min(r.bottom, q.bottom) })
      .filter((r) => r.right - r.left > 0.5 && r.bottom - r.top > 0.5);
    for (let p = el; p && p !== document.body && p !== document.documentElement; p = p.parentElement) {
      const cs = S(p);
      const hx = /hidden|clip/.test(cs.ox), hy = /hidden|clip/.test(cs.oy);
      const sx = /auto|scroll/.test(cs.ox), sy = /auto|scroll/.test(cs.oy);
      if (!hx && !hy && !sx && !sy) continue;
      const { q, L, T, R, B } = box(p);
      if ((hx || hy) && q.width && q.height) {
        const r = (hx && rx.find((r) => r.left < L - tolX || r.right > R + tolX)) ||
                  (hy && ry.find((r) => r.top < T - tolY || r.bottom > B + tolY));
        if (r) {
          const d = { text: n.nodeValue.trim().slice(0, 40), el: label(el), box: label(p),
                      by: Math.round(Math.max(L - r.left, r.right - R, T - r.top, r.bottom - B)) };
          if (el.closest('[data-clip]') || p.closest('[data-clip]')) exempt.push({ ...d, why: (p.closest('[data-clip]') || el.closest('[data-clip]')).dataset.clip });
          else if (truncates(el) || truncates(p)) trunc.push(d);
          else out.push(d);
          break;
        }
      }
      if (sx) rx = clip(rx, q, 'x');
      if (sy) ry = clip(ry, q, 'y');
    }
  }
  return JSON.stringify({ out, trunc, exempt });
})()'''


async def run(routes: list[str], sizes: list[str], langs: list[str]) -> int:
    data = pathlib.Path(tempfile.mkdtemp(prefix='kk-clip-'))
    env = dict(os.environ, KITCHEN_SHOPPING_SYNC_SECONDS='0', KITCHEN_DATA_DIR=str(data),
               KITCHEN_STATIC_DIR=str(CACHE / 'web/dist'), PYTHONPATH=str(REPO / 'server'))
    srv = subprocess.Popen([str(VENV / 'bin/uvicorn'), 'kitchen.main:app', '--host', '127.0.0.1', '--port', str(PORT),
                            '--log-level', 'warning'], env=env)
    chrome_bin = shutil.which('google-chrome-stable') or shutil.which('chromium')
    chrome = subprocess.Popen([chrome_bin, '--headless=new', *CHROME_FLAGS, '--disable-gpu', '--hide-scrollbars',
                               '--force-prefers-reduced-motion', f'--remote-debugging-port={CDP_PORT}',
                               '--window-size=1280,800', f'--user-data-dir={data / "chrome"}', 'about:blank'],
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
        # night off, so a run at night measures the day look the screenshots show (same as screens.sh SCREENS_DAY=1)
        put = lambda body: urllib.request.urlopen(urllib.request.Request(base + '/api/settings', json.dumps(body).encode(),
                                                  {'Content-Type': 'application/json'}, method='PUT')).read()
        put({'night_start': 0, 'night_end': 0})
        target = next(t for t in json.load(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json/list'))
                      if t['type'] == 'page')
        bad = trunc = exempt = 0
        async with websockets.connect(target['webSocketDebuggerUrl'], max_size=None) as ws:
            page = Page(ws)
            await page.call('Page.enable')
            for lang in langs:
                put({'language': lang})
                for size in sizes:
                    w, h, dpr, kiosk = SIZES[size]
                    # measured at 1x: layout is in CSS px whatever the density, and software-rasterising every
                    # animated frame at 2-3x is what made a pass take ~7 minutes (2026-11-11). CLIP_DPR=1 keeps the
                    # real density for a check of text metrics at that density.
                    scale = dpr if os.environ.get('CLIP_DPR') == '1' else 1
                    await page.call('Emulation.setDeviceMetricsOverride',
                                    {'width': w, 'height': h, 'deviceScaleFactor': scale, 'mobile': False})
                    # a distinct query per pass: navigating to the same URL with only a hash is a same-document
                    # navigation, so the app would keep the previous pass's language (seen in the first run)
                    await page.call('Page.navigate', {'url': f'{base}/?{"kiosk=1&" if kiosk else ""}shot=1&pass={lang}-{size}#/'})
                    await asyncio.sleep(2.5)
                    for route in routes:
                        await page.js(f"location.hash = '#{route}'")
                        await asyncio.sleep(1.2)
                        res = json.loads(await page.js(MEASURE))
                        where = f'{lang}-{size:10} {route}'
                        for d in res['out']:
                            bad += 1
                            print(f'CLIPPED {where}  "{d["text"]}"  {d["el"]} cut by {d["box"]} ({d["by"]} px)')
                        for d in res['trunc']:
                            trunc += 1
                            print(f'TRUNC   {where}  "{d["text"]}"  {d["el"]} in {d["box"]}')
                        for d in res['exempt']:
                            exempt += 1
                            print(f'EXEMPT  {where}  "{d["text"]}"  {d["el"]} in {d["box"]} ({d["why"]})')
        print(f'{bad} clipped text(s), {trunc} truncated on purpose, {exempt} exempt — '
              f'{len(routes)} routes x {len(sizes)} sizes x {len(langs)} languages')
        return 1 if bad else 0
    finally:
        chrome.terminate(); srv.terminate()
        chrome.wait(10); srv.wait(10)
        shutil.rmtree(data, ignore_errors=True)


SELFTEST_HTML = (
    '<!doctype html><html><body style="margin:0;font:16px sans-serif">'
    # 1. the home-tile bug: a fixed-height box, overflow hidden, its second line cut off -> CLIPPED "second line"
    '<div style="height:24px;overflow:hidden;width:300px"><div>first line</div><div>second line</div></div>'
    # 2. the same, but the box scrolls: reachable -> nothing
    '<div style="height:24px;overflow:auto;width:300px"><div>scrolls a</div><div>scrolls b</div></div>'
    # 3. nowrap text cut on the right -> CLIPPED "a very long label that is cut on the right"
    '<div style="width:60px;overflow:hidden;white-space:nowrap">a very long label that is cut on the right</div>'
    # 4. deliberate ellipsis -> TRUNC
    '<div style="width:60px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">ellipsis on purpose here</div>'
    # 5. a tight line-height on a big font: the glyph box pokes out, nothing is cut -> nothing
    '<div style="overflow:hidden;font-size:40px;line-height:1">Tight</div>'
    # 6. exempt -> EXEMPT
    '<div data-clip="decorative marquee" style="width:40px;overflow:hidden;white-space:nowrap">exempt marquee text</div>'
    # 7. a panel that scrolls inside a clipped body (the mascot lab): reachable -> nothing
    '<div style="height:40px;overflow:hidden"><div style="height:40px;overflow-y:auto">'
    '<div>panel row 1</div><div>panel row 2</div><div>panel row 3</div><div>panel row 4</div></div></div>'
    # 8. a scroller that is itself cut off by its clipped parent: its lower half is unreachable -> CLIPPED "cut scroller 2"
    '<div style="height:20px;overflow:hidden"><div style="height:40px;overflow-y:auto">'
    '<div>cut scroller 1</div><div>cut scroller 2</div></div></div>'
    '</body></html>')


async def selftest() -> int:
    """The audit's positive control: the eight cases above must come out exactly as their comments say."""
    from urllib.parse import quote
    data = pathlib.Path(tempfile.mkdtemp(prefix='kk-clip-self-'))
    chrome_bin = shutil.which('google-chrome-stable') or shutil.which('chromium')
    chrome = subprocess.Popen([chrome_bin, '--headless=new', *CHROME_FLAGS, '--disable-gpu', f'--remote-debugging-port={SELFTEST_CDP_PORT}',
                               '--window-size=1024,640', f'--user-data-dir={data / "chrome"}', 'data:text/html,' + quote(SELFTEST_HTML)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                pages = json.load(urllib.request.urlopen(f'http://127.0.0.1:{SELFTEST_CDP_PORT}/json/list', timeout=2))
                break
            except OSError:
                time.sleep(0.1)
        target = [t for t in pages if t['type'] == 'page'][0]
        async with websockets.connect(target['webSocketDebuggerUrl'], max_size=None) as ws:
            await asyncio.sleep(1)
            res = json.loads(await Page(ws).js(MEASURE))
        got = {k: sorted(d['text'] for d in res[k]) for k in ('out', 'trunc', 'exempt')}
        want = {'out': ['a very long label that is cut on the rig', 'cut scroller 2', 'second line'], 'trunc': ['ellipsis on purpose here'],
                'exempt': ['exempt marquee text']}
        ok = got == want
        print(f"selftest {'OK' if ok else 'FAILED'}: got {got}" + ('' if ok else f', want {want}'))
        return 0 if ok else 1
    finally:
        chrome.terminate(); chrome.wait(10)
        shutil.rmtree(data, ignore_errors=True)


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--selftest']:
        sys.exit(asyncio.run(selftest()))
    sizes, langs = list(SIZES), ['en', 'hu']
    while args and args[0] in ('--sizes', '--langs'):
        flag, val, args = args[0], args[1].split(','), args[2:]
        if flag == '--sizes':
            unknown = [s for s in val if s not in SIZES]
            if unknown:
                sys.exit(f'clip-audit: unknown size(s) {unknown}; known: {list(SIZES)}')
            sizes = val
        else:
            langs = val
    sys.exit(asyncio.run(run([r for r in ROUTES if not args or r in args], sizes, langs)))
