#!/usr/bin/env python3
"""Filmstrips of the mascot's actions — motion is judged by LOOKING.

Serves the scratch build (like screens.sh), opens #/lab/mascot in headless Chrome over CDP, plays each action, pauses
every animation (Web Animations API) and steps `currentTime` through the action, screenshotting the stage at each
step. The frames go into one contact sheet per action, labelled with the time.

usage: scripts/anim-sheet.py [--frames 12] [--size 360] [--night] [--out DIR] ACTION [ACTION ...]
       scripts/anim-sheet.py --all          every action in lib/mascot.ts
       scripts/anim-sheet.py --sheet FILE   the character sheet: every expression, the props, day and night
       scripts/anim-sheet.py --scene chop   an idle-scene prop act (chop | herbs | chicken), day look
Output: DIR/anim-<action>[-night].png  (default DIR ~/.cache/jxn-kitchen/anim)
"""
from __future__ import annotations

import argparse, asyncio, base64, io, json, os, pathlib, shutil, subprocess, sys, tempfile, time, urllib.request

import websockets

from cdp import CHROME_FLAGS, Page
from PIL import Image, ImageDraw, ImageFont

REPO = pathlib.Path(__file__).resolve().parent.parent
CACHE = pathlib.Path(os.environ.get('KITCHEN_SCRATCH', pathlib.Path.home() / '.cache/jxn-kitchen'))
VENV = pathlib.Path.home() / '.local/share/venvs/jxn-kitchen'
PORT, CDP = 8767, 9460
WAIT = 1.6                     # --states: seconds each tap gets to settle


def font(px: int):
    for f in ('/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        if pathlib.Path(f).exists():
            return ImageFont.truetype(f, px)
    return ImageFont.load_default()


SHEET = [('neutral', None, False), ('happy', None, False), ('joy', None, False), ('surprised', None, False),
         ('proud', None, False), ('focus', None, False), ('worried', None, False), ('alarm', None, False),
         ('sleepy', None, False), ('asleep', None, True), ('neutral', 'chef', False), ('neutral', None, True)]


SCENE_MS = {'chop': 2900, 'herbs': 2600, 'chicken': 7400}


async def run(actions: list[str], frames: int, size: int, night: bool, out: pathlib.Path,
              sheet: pathlib.Path | None = None, scene: str | None = None, states: str | None = None,
              page: str | None = None) -> list[pathlib.Path]:
    tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{CDP}/json/list'))
    ws_url = [t for t in tabs if t['type'] == 'page'][0]['webSocketDebuggerUrl']
    written = []
    async with websockets.connect(ws_url, max_size=None) as ws:
        cdp = Page(ws)   # scripts/cdp.py (not `page`: that is run()'s --page ROUTE parameter, which it would shadow)
        call, ev = cdp.call, cdp.js

        await call('Emulation.setDeviceMetricsOverride', {'width': 1280, 'height': 800, 'deviceScaleFactor': 1, 'mobile': False})
        if page:
            # a whole know-how article at kiosk width — tables, tips and all (a screenshot stops at the fold)
            await call('Emulation.setDeviceMetricsOverride', {'width': 1024, 'height': 640, 'deviceScaleFactor': 1.25, 'mobile': False})
            await call('Page.navigate', {'url': f'http://127.0.0.1:{PORT}/?shot=1#{page}'})
            for _ in range(80):
                await asyncio.sleep(0.1)
                if await ev("!!document.querySelector('.page .md')"):
                    break
            await asyncio.sleep(2.0)
            # the viewport must hold the article's own height PLUS everything above it (header, title row)
            h = await ev("(() => { const a = document.querySelector('article.page'); return Math.ceil(a.getBoundingClientRect().top + a.scrollHeight + 60); })()")
            for _ in range(4):   # growing the viewport re-lays the page out: grow until nothing overflows the article
                await call('Emulation.setDeviceMetricsOverride', {'width': 1024, 'height': max(640, h), 'deviceScaleFactor': 1.25, 'mobile': False})
                await asyncio.sleep(0.6)
                # overflowing inside the article, or the article itself running past the window
                over = await ev("(() => { const a = document.querySelector('article.page'); return Math.ceil(Math.max(a.scrollHeight - a.clientHeight, a.getBoundingClientRect().bottom - innerHeight)); })()")
                if os.environ.get('ANIM_DEBUG'):
                    print(await ev("JSON.stringify((() => { const a = document.querySelector('article.page'); const r = a.getBoundingClientRect(); return {inner: innerHeight, top: r.top, bottom: r.bottom, sh: a.scrollHeight, ch: a.clientHeight, doc: document.documentElement.scrollHeight}; })())"))
                if over <= 0:
                    break
                h += over + 20
            d = await call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True})
            path = out / f"page{page.replace('/', '_')}.png"
            path.write_bytes(base64.b64decode(d['data']))
            print(path)
            return [path]
        if states:
            # every state of a know-how page's infographic: tap each of its buttons in turn, let the motion settle,
            # capture the infographic — one contact sheet (a screenshot without taps shows the first state only)
            await call('Emulation.setDeviceMetricsOverride', {'width': 1024, 'height': 640, 'deviceScaleFactor': 1.25, 'mobile': False})
            await call('Page.navigate', {'url': f'http://127.0.0.1:{PORT}/?shot=1#{states}'})
            for _ in range(80):
                await asyncio.sleep(0.1)
                if await ev("!!document.querySelector('.page .illus')"):
                    break
            await asyncio.sleep(2.0)                   # the entrance animations are over
            n = await ev("document.querySelectorAll('.page .illus button').length")
            shots = []
            for k in range(n):
                label = await ev(f"(b => (b.click(), b.textContent.trim().replace(/\\s+/g, ' ')))(document.querySelectorAll('.page .illus button')[{k}])")
                await asyncio.sleep(WAIT)
                r = await ev("JSON.stringify(document.querySelector('.page .illus').getBoundingClientRect())")
                b = json.loads(r)
                d = await call('Page.captureScreenshot', {'format': 'png', 'clip': {'x': b['x'], 'y': b['y'], 'width': b['width'],
                                                                                    'height': min(b['height'], 640 - b['y']), 'scale': 1}})
                shots.append((label, Image.open(io.BytesIO(base64.b64decode(d['data']))).convert('RGB')))
            if not shots:
                raise SystemExit(f'no buttons in the infographic on {states}')
            cols = 2
            fw, fh = shots[0][1].size
            tw, th = int(fw * .62), int(fh * .62)
            img = Image.new('RGB', (cols * tw + 10, ((len(shots) + 1) // 2) * (th + 24) + 40), '#FFFFFF')
            dr = ImageDraw.Draw(img)
            dr.text((10, 8), f'states: {states}', fill='#1F1A17', font=font(22))
            for idx, (label, im) in enumerate(shots):
                x, y = (idx % cols) * (tw + 10), 40 + (idx // cols) * (th + 24)
                img.paste(im.resize((tw, th)), (x, y))
                dr.text((x + 6, y + th + 2), f'tap {idx + 1}: {label[:60]}', fill='#1F1A17', font=font(15))
            path = out / f"states{states.replace('/', '_')}.png"
            img.save(path)
            print(path)
            return [path]
        if scene:
            await call('Emulation.setDeviceMetricsOverride', {'width': 1024, 'height': 640, 'deviceScaleFactor': 1, 'mobile': False})
            req = urllib.request.Request(f'http://127.0.0.1:{PORT}/api/settings', json.dumps({'night_start': 0, 'night_end': 0}).encode(),
                                         {'Content-Type': 'application/json'}, method='PUT')
            urllib.request.urlopen(req).read()
            await call('Page.navigate', {'url': f'http://127.0.0.1:{PORT}/?shot=1#/idle'})
            for _ in range(80):
                await asyncio.sleep(0.1)
                if await ev('!!window.__idle'):
                    break
            await asyncio.sleep(4.5)                   # the arrival yawn is over
            await ev(f"window.__idle.prop('{scene}')")
            await asyncio.sleep(0.08)
            await ev('document.getAnimations().forEach(a => a.pause())')
            dur = SCENE_MS[scene]
            shots = []
            for k in range(frames):
                t = dur * k / (frames - 1)
                await ev(f'document.getAnimations().forEach(a => {{ a.currentTime = {t}; }})')
                await asyncio.sleep(0.03)
                d = await call('Page.captureScreenshot', {'format': 'png', 'clip': {'x': 0, 'y': 300, 'width': 1024, 'height': 240, 'scale': 1}})
                shots.append((t, Image.open(io.BytesIO(base64.b64decode(d['data']))).convert('RGB')))
            tw, th = 512, 120
            img = Image.new('RGB', (2 * tw, ((frames + 1) // 2) * (th + 22) + 40), '#FFFFFF')
            dr = ImageDraw.Draw(img)
            dr.text((10, 8), f'scene: {scene} ({dur} ms)', fill='#1F1A17', font=font(22))
            for idx, (t, im) in enumerate(shots):
                x, y = (idx % 2) * tw, 40 + (idx // 2) * (th + 22)
                img.paste(im.resize((tw, th)), (x, y))
                dr.text((x + 6, y + th + 2), f'{t / 1000:.2f}s', fill='#1F1A17', font=font(15))
            path = out / f'scene-{scene}.png'
            img.save(path)
            print(path)
            return [path]
        q = f'still=1&size={size}' + ('&night=1' if night else '')
        await call('Page.navigate', {'url': f'http://127.0.0.1:{PORT}/?shot=1#/lab/mascot?{q}'})
        for _ in range(80):
            await asyncio.sleep(0.1)
            if await ev('!!window.__mascot'):
                break
        await asyncio.sleep(1.0)                       # fonts, first paint
        durations = await ev('window.__mascot.actions')
        rect = await ev("(() => { const r = document.querySelector('#stage .m').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()")
        z = rect[2] / 340                              # the rig's zoom: headroom for jumps and the egg flip (196 units up)
        top = 200 * z
        clip = {'x': max(0, rect[0] - 30 * z), 'y': max(0, rect[1] - top), 'width': rect[2] + 60 * z,
                'height': rect[3] + top + 10 * z, 'scale': 1}
        if sheet is not None:
            cells = []
            for expr, prop, nt in SHEET:
                await ev(f"window.__mascot.setExpr('{expr}'); window.__mascot.setProp({json.dumps(prop)}); window.__mascot.setNight({json.dumps(nt)})")
                await asyncio.sleep(0.6)
                d = await call('Page.captureScreenshot', {'format': 'png', 'clip': clip})
                label = expr + (f' + {prop}' if prop else '') + (' (night)' if nt else '')
                cells.append((label, Image.open(io.BytesIO(base64.b64decode(d['data']))).convert('RGB')))
            fw, fh = cells[0][1].size
            tw, th = int(fw * 0.7), int(fh * 0.7)
            cols = 4
            img = Image.new('RGB', (cols * tw, ((len(cells) + cols - 1) // cols) * (th + 26) + 50), '#FFFFFF')
            dr = ImageDraw.Draw(img)
            dr.text((12, 10), 'JXN Kitchen mascot: expressions, props, night', fill='#1F1A17', font=font(24))
            for idx, (label, im) in enumerate(cells):
                x, y = (idx % cols) * tw, 50 + (idx // cols) * (th + 26)
                img.paste(im.resize((tw, th)), (x, y))
                dr.text((x + 8, y + th + 3), label, fill='#1F1A17', font=font(17))
            sheet.parent.mkdir(parents=True, exist_ok=True)
            img.save(sheet)
            print(sheet)
            return [sheet]
        for act in actions:
            dur = durations.get(act)
            if dur is None:
                print(f'unknown action {act!r}', file=sys.stderr)
                continue
            await ev(f"window.__mascot.play('{act}', true)")
            await asyncio.sleep(0.08)                  # the rAF that applies the class
            await ev('document.getAnimations().forEach(a => a.pause())')
            shots = []
            for k in range(frames):
                t = dur * k / (frames - 1)
                await ev(f'document.getAnimations().forEach(a => {{ a.currentTime = {t}; }})')
                await asyncio.sleep(0.03)
                d = await call('Page.captureScreenshot', {'format': 'png', 'clip': clip})
                shots.append((t, Image.open(io.BytesIO(base64.b64decode(d['data']))).convert('RGB')))
            await ev('window.__mascot.stop()')
            await asyncio.sleep(0.2)
            cols = 6 if frames > 6 else frames
            rows = (frames + cols - 1) // cols
            fw, fh = shots[0][1].size
            thumb = min(1.0, 300 / fw)
            tw, th = int(fw * thumb), int(fh * thumb)
            sheet = Image.new('RGB', (cols * tw, rows * (th + 22) + 40), '#FFFFFF')
            draw = ImageDraw.Draw(sheet)
            draw.text((10, 8), f'{act}  ({dur} ms){"  — night" if night else ""}', fill='#1F1A17', font=font(22))
            for idx, (t, im) in enumerate(shots):
                x, y = (idx % cols) * tw, 40 + (idx // cols) * (th + 22)
                sheet.paste(im.resize((tw, th)), (x, y))
                draw.text((x + 6, y + th + 2), f'{t / 1000:.2f}s', fill='#1F1A17', font=font(15))
            path = out / f'anim-{act}{"-night" if night else ""}.png'
            sheet.save(path)
            written.append(path)
            print(path)
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('actions', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--frames', type=int, default=12)
    ap.add_argument('--size', type=int, default=360)
    ap.add_argument('--night', action='store_true')
    ap.add_argument('--out', default=str(CACHE / 'anim'))
    ap.add_argument('--sheet', help='write the character sheet to this PNG instead of filmstrips')
    ap.add_argument('--scene', choices=['chop', 'herbs', 'chicken'], help='filmstrip an idle-scene prop act')
    ap.add_argument('--wait', type=float, default=1.6, help='--states: seconds to let each tap settle')
    ap.add_argument('--page', metavar='ROUTE', help='a whole know-how article, below the fold too, e.g. /knowhow/coffee/tea')
    ap.add_argument('--states', metavar='ROUTE', help="every state of a know-how page's infographic, e.g. /knowhow/knife/onion")
    a = ap.parse_args()
    global WAIT
    WAIT = a.wait
    actions = a.actions
    if a.all:
        src = (REPO / 'web/src/lib/mascot.ts').read_text()
        block = src[src.index('export const ACTIONS'):src.index('};', src.index('export const ACTIONS'))]
        actions = [ln.strip().split(':')[0] for ln in block.splitlines()[1:] if ':' in ln]
    if not actions and not a.sheet and not a.scene and not a.states and not a.page:
        ap.error('name actions, pass --all, --sheet FILE, --scene, --states ROUTE or --page ROUTE')
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = pathlib.Path(tempfile.mkdtemp(prefix='anim-data-'))
    env = dict(os.environ, KITCHEN_SHOPPING_SYNC_SECONDS='0', KITCHEN_DATA_DIR=str(data),
               KITCHEN_STATIC_DIR=str(CACHE / 'web/dist'), PYTHONPATH=str(REPO / 'server'))
    srv = subprocess.Popen([str(VENV / 'bin/uvicorn'), 'kitchen.main:app', '--host', '127.0.0.1', '--port', str(PORT),
                            '--log-level', 'warning', '--timeout-graceful-shutdown', '1'], env=env)
    chrome_bin = shutil.which('google-chrome-stable') or shutil.which('chromium')
    prof = tempfile.mkdtemp(prefix='anim-chrome-')
    chrome = subprocess.Popen([chrome_bin, '--headless=new', *CHROME_FLAGS, '--hide-scrollbars', f'--user-data-dir={prof}',
                               f'--remote-debugging-port={CDP}', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/health', timeout=1)
                urllib.request.urlopen(f'http://127.0.0.1:{CDP}/json/version', timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        asyncio.run(run(actions, a.frames, a.size, a.night, out, pathlib.Path(a.sheet) if a.sheet else None, a.scene, a.states, a.page))
    finally:
        chrome.terminate(); srv.terminate()
        chrome.wait(); srv.wait()
        shutil.rmtree(prof, ignore_errors=True); shutil.rmtree(data, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
