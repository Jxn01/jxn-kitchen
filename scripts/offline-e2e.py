#!/usr/bin/env python3
"""Offline mode, end to end, as the kiosk uses it — against a LOCAL server with a throwaway database (never the live one).

  1. start the server (scratch data dir, the scratch build in ~/.cache/jxn-kitchen/web/dist — run
     scripts/build-web.sh first), seed one recipe;
  2. open the app in headless Chrome as the kiosk (?kiosk=1), wait for the service worker and the warm-up;
  3. STOP the server, then in the UI: turn sounds off, start a 3-minute timer, edit the recipe's title;
  4. check the offline screen: the timer is listed, the recipe says it was edited offline, two changes wait;
  5. START the server again (same port, same data) and wait for the app to reconnect and replay;
  6. check the server: sounds off, the new title, the timer — ending when it ended on the kiosk.
Exit 0 only if every check passed. A screenshot of the offline recipe screen lands in the scratch dir.
(The unit tests cover folders and the replay rules; this proves the wiring in a real browser.)
"""
from __future__ import annotations

import asyncio
import base64
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

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cdp import CHROME_FLAGS, Page  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
CACHE = pathlib.Path(os.environ.get('KITCHEN_SCRATCH', pathlib.Path.home() / '.cache/jxn-kitchen'))
VENV = pathlib.Path(os.environ.get('KITCHEN_VENV', pathlib.Path.home() / '.local/share/venvs/jxn-kitchen'))
PORT, CDP_PORT = 18765, 9351
BASE = f'http://localhost:{PORT}'          # localhost: a service worker needs https or localhost
TITLE, NEW_TITLE, LABEL, MINUTES = 'Offline teszt', 'Offline teszt (szerkesztve)', 'Offline tészta', 3

failures: list[str] = []


def check(ok: bool, what: str) -> None:
    print(('  ok    ' if ok else '  FAIL  ') + what)
    if not ok:
        failures.append(what)


def api(method: str, path: str, body: dict | None = None):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


def start_server(data: pathlib.Path) -> subprocess.Popen:
    env = dict(os.environ, KITCHEN_SHOPPING_SYNC_SECONDS='0', KITCHEN_DATA_DIR=str(data),
               KITCHEN_STATIC_DIR=str(CACHE / 'web/dist'), PYTHONPATH=str(REPO / 'server'))
    srv = subprocess.Popen([str(VENV / 'bin/uvicorn'), 'kitchen.main:app', '--host', '127.0.0.1', '--port', str(PORT),
                            '--log-level', 'warning'], env=env, cwd=REPO / 'server')
    for _ in range(100):
        try:
            api('GET', '/api/settings')
            return srv
        except Exception:
            time.sleep(0.2)
    srv.kill()
    raise SystemExit('the local server did not start')


async def wait_for(p: Page, expr: str, timeout: float, what: str) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if await p.js(expr):
            return True
        await asyncio.sleep(0.5)
    check(False, f'timed out waiting for: {what}')
    return False


async def set_input(p: Page, selector: str, value: str) -> None:
    await p.js(f"""(() => {{ const el = document.querySelector({json.dumps(selector)});
        el.value = {json.dumps(value)}; el.dispatchEvent(new Event('input', {{ bubbles: true }})); }})()""")


async def main(data: pathlib.Path, prof: pathlib.Path) -> None:
    srv = start_server(data)
    rid = api('POST', '/api/recipes', {'title': TITLE, 'servings': 2, 'ingredients': ['2 tojás'], 'steps': ['Megfőzöd.'],
                                       'tags': []})['id']
    chrome = subprocess.Popen([shutil.which('google-chrome-stable') or shutil.which('chromium'), '--headless=new',
                               *CHROME_FLAGS, '--disable-gpu', f'--remote-debugging-port={CDP_PORT}',
                               '--window-size=1024,640', f'--user-data-dir={prof}', 'about:blank'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json/list', timeout=2))
                break
            except Exception:
                await asyncio.sleep(0.2)
        ws_url = next(t for t in tabs if t['type'] == 'page')['webSocketDebuggerUrl']
        async with websockets.connect(ws_url, max_size=None) as ws:
            p = Page(ws)
            await p.call('Page.enable')
            await p.call('Page.navigate', {'url': BASE + '/?kiosk=1'})
            await wait_for(p, '!!navigator.serviceWorker.controller', 30, 'the service worker')
            await p.call('Page.reload')
            print('online: waiting for the warm-up')
            await wait_for(p, f"caches.has('kitchen-data').then(h => h && caches.open('kitchen-data')"
                              f".then(c => c.match('/api/recipes/{rid}')).then(Boolean))", 60, 'the warm-up')

            print('server STOPPED; editing offline')
            srv.kill(); srv.wait()      # a dead server, not a graceful stop (that waits forever on the open SSE stream)
            # settings: sounds off
            await p.call('Page.navigate', {'url': BASE + '/?kiosk=1#/settings'})
            await wait_for(p, "[...document.querySelectorAll('h2')].some(h => /sound|hang/i.test(h.textContent))", 15, 'settings')
            await p.js("[...document.querySelectorAll('h2')].find(h => /sound|hang/i.test(h.textContent)).nextElementSibling.querySelectorAll('button')[1].click()")
            # a timer
            await p.call('Page.navigate', {'url': BASE + '/?kiosk=1#/timers'})
            await wait_for(p, "!!document.querySelector('.preset')", 15, 'the timers screen')
            await set_input(p, 'input[maxlength="60"]', LABEL)
            started = time.time()
            await p.js(f"[...document.querySelectorAll('.preset')].find(b => b.textContent.trim().startsWith('{MINUTES}')).click()")
            await asyncio.sleep(1)
            check(LABEL in (await p.js('document.body.innerText') or ''), 'offline: the timer started and is listed')
            # the recipe's title
            await p.call('Page.navigate', {'url': f'{BASE}/?kiosk=1#/recipe/{rid}/edit'})
            await wait_for(p, f"document.querySelector('input[maxlength=\"200\"]')?.value === {json.dumps(TITLE)}", 15, 'the editor, filled')
            await set_input(p, 'input[maxlength="200"]', NEW_TITLE)
            await p.js("document.querySelector('button.save').click()")
            await wait_for(p, f"location.hash === '#/recipe/{rid}'", 10, 'the recipe screen after saving')
            await asyncio.sleep(1.5)
            check(bool(await p.js("!!document.querySelector('.pending')")), 'offline: the recipe says it was edited offline')
            badge = await p.js('document.body.innerText') or ''
            check('2 changes waiting' in badge or '2 változás vár' in badge, 'offline: the badge counts 2 changes waiting')
            shot = await p.call('Page.captureScreenshot', {'format': 'png'})
            (CACHE / 'offline-e2e.png').write_bytes(base64.b64decode(shot['data']))

            print('server STARTED again; waiting for the replay')
            srv = start_server(data)
            end = time.time() + 75
            got = {}
            while time.time() < end:
                got = {'sounds': api('GET', '/api/settings')['sounds'], 'title': api('GET', f'/api/recipes/{rid}')['title'],
                       'timers': [t for t in api('GET', '/api/timers') if t['label'] == LABEL]}
                if got['sounds'] is False and got['title'] == NEW_TITLE and got['timers']:
                    break
                await asyncio.sleep(1)
            check(got.get('sounds') is False, 'server: sounds off (the settings patch replayed)')
            check(got.get('title') == NEW_TITLE, 'server: the new title (the recipe edit replayed)')
            ts = got.get('timers') or []
            check(len(ts) == 1, 'server: exactly one replayed timer')
            if ts:
                expected = MINUTES * 60 - (time.time() - started)
                check(abs(ts[0]['remaining'] - expected) <= 5,
                      f"server: the timer ends when it ended on the kiosk ({ts[0]['remaining']} s left, expected ~{expected:.0f})")
            await asyncio.sleep(2)
            check(not await p.js("!!document.querySelector('.pending')"), 'online again: the offline note is gone')
    finally:
        chrome.kill()
        srv.kill()


if __name__ == '__main__':
    if not (CACHE / 'web/dist/index.html').exists():
        raise SystemExit('no build in the scratch dir: run scripts/build-web.sh first')
    work = pathlib.Path(tempfile.mkdtemp(prefix='kitchen-offline-e2e-'))
    try:
        (work / 'data').mkdir()
        asyncio.run(main(work / 'data', work / 'chrome'))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print('PASS' if not failures else f'FAILED: {len(failures)} check(s)')
    sys.exit(1 if failures else 0)
