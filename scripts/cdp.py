"""The one CDP (Chrome DevTools Protocol) client for the scripts that drive Chrome: touch-audit.py, clip-audit.py,
anim-sheet.py. (kiosk-tapthrough.py has its own Page with the same reader; this one is modelled on it.)

🚨 It reads the websocket CONTINUOUSLY, on a task of its own, and hands each reply to the call waiting for it — the
pattern kiosk-tapthrough.py already had. The audits used to read only while awaiting a reply, leaving Chrome's events
unread between calls. (The multi-second, growing stalls of the evening of 2026-11-11 were mostly something else: a fresh
profile's background machinery on Chrome's browser main thread, which also serves every DevTools call — see
chrome-flags.txt; with those flags a 9-screen walk went from 3m27s to 43.6 s.)
tests/test_hygiene.py keeps every other script from reading a CDP websocket itself.
"""
from __future__ import annotations

import asyncio
import json
import pathlib

# Every headless Chrome a script starts takes these first: scripts/chrome-flags.txt (shared with screens.sh) says why.
CHROME_FLAGS = [ln.strip() for ln in (pathlib.Path(__file__).with_name('chrome-flags.txt')).read_text().splitlines()
                if ln.strip() and not ln.lstrip().startswith('#')]


class Page:
    """One CDP session over an open websocket. Calls may overlap; JS exceptions thrown on the page are collected in
    `exc` once `Runtime.enable` has been called."""

    def __init__(self, ws):
        self.ws, self.n, self.wait, self.exc = ws, 0, {}, []
        self.reader = asyncio.ensure_future(self._read())

    async def _read(self) -> None:
        try:
            async for raw in self.ws:
                m = json.loads(raw)
                if m.get('method') == 'Runtime.exceptionThrown':
                    d = m['params']['exceptionDetails']
                    self.exc.append((d.get('exception') or {}).get('description', d.get('text', ''))[:300])
                f = self.wait.pop(m.get('id'), None)
                if f is not None and not f.done():
                    f.set_result(m)
        finally:   # the socket closed (or the reader was cancelled): nobody may wait forever for a reply
            for f in self.wait.values():
                if not f.done():
                    f.set_exception(ConnectionError('CDP websocket closed'))
            self.wait.clear()

    async def call(self, method: str, params: dict | None = None) -> dict:
        self.n += 1
        f = asyncio.get_running_loop().create_future()
        self.wait[self.n] = f
        await self.ws.send(json.dumps({'id': self.n, 'method': method, 'params': params or {}}))
        m = await f
        if 'error' in m:
            raise RuntimeError(m['error'])
        return m.get('result', {})

    async def js(self, expr: str):
        r = await self.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        return r.get('result', {}).get('value')
