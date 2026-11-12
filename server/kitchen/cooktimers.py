"""Kitchen timers: any number, labelled, kept on the server so the kiosk, the phone and HA see the same
ones. A scheduler sleeps until the next end, marks the timer done (the kiosk rings until someone taps it), broadcasts
SSE `timers`, and asks Home Assistant to notify the phone through `script.notify_owner` — priority `urgent` (iOS
*time-sensitive*, so it breaks through a Focus such as Sleep; `normal` would arrive silently). The script sends at once;
the 22:00–08:00 hold belongs to HA's own alert automations, not to the script. HA unreachable: the ring alone.

States: running (ends_at) · paused (remaining) · done (rang; shown until dismissed) · dismissed (gone).
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Callable

from .events import Broadcaster
from .ha import HAClient

log = logging.getLogger(__name__)
LATE_PING = timedelta(minutes=10)      # a timer found ended longer ago than this (server was down) rings, but no ping
# Phone pings are capped: the app has no logins (LAN/tailnet by design), so anyone on the home
# Wi-Fi could otherwise fire urgent notifications at the phone with 1-second timers. Past the cap the kiosk
# still rings; only the phone stays quiet.
PING_LIMIT, PING_WINDOW = 6, timedelta(minutes=10)


class NotFound(KeyError):
    pass


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def view(r: sqlite3.Row, now: datetime) -> dict[str, Any]:
    if r['state'] == 'running':
        remaining = max(0, round((_dt(r['ends_at']) - now).total_seconds()))
    elif r['state'] == 'paused':
        remaining = r['remaining']
    else:
        remaining = 0
    return {'id': r['id'], 'label': r['label'], 'seconds': r['seconds'], 'state': r['state'], 'remaining': remaining,
            'ends_at': r['ends_at'] if r['state'] == 'running' else None, 'recipe_id': r['recipe_id'],
            'step_pos': r['step_pos']}


def list_active(conn: sqlite3.Connection, now: datetime) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM timer WHERE state != 'dismissed' ORDER BY state = 'done' DESC, id").fetchall()
    return [view(r, now) for r in rows]


def _get(conn: sqlite3.Connection, tid: int) -> sqlite3.Row:
    r = conn.execute("SELECT * FROM timer WHERE id = ? AND state != 'dismissed'", (tid,)).fetchone()
    if r is None:
        raise NotFound(tid)
    return r


def create(conn: sqlite3.Connection, now: datetime, label: str, seconds: int, recipe_id: int | None = None,
           step_pos: int | None = None) -> dict[str, Any]:
    cur = conn.execute('INSERT INTO timer (label, seconds, ends_at, state, recipe_id, step_pos, notified, created_at) '
                       "VALUES (?, ?, ?, 'running', ?, ?, 0, ?)",
                       (label.strip(), seconds, (now + timedelta(seconds=seconds)).isoformat(), recipe_id, step_pos,
                        now.isoformat()))
    return view(_get(conn, cur.lastrowid), now)


def act(conn: sqlite3.Connection, now: datetime, tid: int, action: str, seconds: int = 60) -> dict[str, Any]:
    r = _get(conn, tid)
    state = r['state']
    if action == 'pause' and state == 'running':
        left = max(0, round((_dt(r['ends_at']) - now).total_seconds()))
        conn.execute("UPDATE timer SET state = 'paused', remaining = ?, ends_at = NULL WHERE id = ?", (left, tid))
    elif action == 'resume' and state == 'paused':
        conn.execute("UPDATE timer SET state = 'running', ends_at = ?, remaining = NULL WHERE id = ?",
                     ((now + timedelta(seconds=r['remaining'])).isoformat(), tid))
    elif action == 'add':
        if state == 'running':
            conn.execute('UPDATE timer SET ends_at = ? WHERE id = ?',
                         ((_dt(r['ends_at']) + timedelta(seconds=seconds)).isoformat(), tid))
        elif state == 'paused':
            conn.execute('UPDATE timer SET remaining = remaining + ? WHERE id = ?', (seconds, tid))
        else:                                       # done: "a minute more" restarts it
            conn.execute("UPDATE timer SET state = 'running', ends_at = ?, notified = 0 WHERE id = ?",
                         ((now + timedelta(seconds=seconds)).isoformat(), tid))
    elif action == 'dismiss':
        conn.execute("UPDATE timer SET state = 'dismissed' WHERE id = ?", (tid,))
        return {'id': tid, 'state': 'dismissed'}
    return view(_get(conn, tid), now)


def delete(conn: sqlite3.Connection, tid: int) -> None:
    if conn.execute('DELETE FROM timer WHERE id = ?', (tid,)).rowcount == 0:
        raise NotFound(tid)


class TimerService:
    def __init__(self, conn: sqlite3.Connection, events: Broadcaster, ha: HAClient, now: Callable[[], datetime],
                 lang: Callable[[], str]):
        self.conn, self.events, self.ha, self.now, self.lang = conn, events, ha, now, lang
        self.wake = asyncio.Event()
        self.pings: list[datetime] = []

    def changed(self) -> list[dict[str, Any]]:
        items = list_active(self.conn, self.now())
        self.events.publish('timers', {'timers': items})
        self.wake.set()                              # the next end may have moved
        return items

    async def fire_due(self) -> None:
        now = self.now()
        due = self.conn.execute("SELECT * FROM timer WHERE state = 'running' AND ends_at <= ?",
                                (now.isoformat(),)).fetchall()
        if not due:
            return
        for r in due:
            self.conn.execute("UPDATE timer SET state = 'done' WHERE id = ? AND state = 'running'", (r['id'],))
        self.changed()
        labels = []
        for r in due:
            claimed = self.conn.execute('UPDATE timer SET notified = 1 WHERE id = ? AND notified = 0', (r['id'],)).rowcount
            if claimed and now - _dt(r['ends_at']) <= LATE_PING:   # not pinged yet, and not so late it would confuse
                labels.append(r['label'])
        if labels:
            await self.notify(labels, now)            # timers ending together: one notification

    async def notify(self, labels: list[str], now: datetime) -> None:
        hu = self.lang() == 'hu'
        self.pings = [p for p in self.pings if now - p < PING_WINDOW]
        if len(self.pings) >= PING_LIMIT:
            log.warning('timers ended (%r) but the phone was pinged %d times in %s: no ping (the kiosk rings)',
                        labels, len(self.pings), PING_WINDOW)
            return
        self.pings.append(now)
        names = ', '.join(l or ('Időzítő' if hu else 'Timer') for l in labels)
        ok = await self.ha.call_service('script', 'notify_owner', {
            'title': 'Konyha' if hu else 'Kitchen',
            'message': f'Lejárt: {names}' if hu else f"Time's up: {names}",
            'priority': 'urgent', 'group': 'kitchen-timer'})
        if ok is None:
            log.warning('timers ended (%r); HA could not notify the phone (the kiosk rings anyway)', names)

    async def run(self) -> None:
        while True:
            try:
                await self.fire_due()
            except Exception:                         # never let one bad round stop the kitchen's timers
                log.exception('timer round failed')
            row = self.conn.execute("SELECT MIN(ends_at) AS t FROM timer WHERE state = 'running'").fetchone()
            wait = 3600.0
            if row['t']:
                wait = max(0.0, min(3600.0, (_dt(row['t']) - self.now()).total_seconds() + 0.05))
            self.wake.clear()
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass
