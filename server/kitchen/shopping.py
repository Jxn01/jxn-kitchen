"""The shopping list, mirrored two-way with Home Assistant's to-do list `todo.shopping_list`.

Local rows carry `pending` for changes HA has not seen yet: 'add' (never sent), 'adding' (a push is awaiting HA),
'update', 'delete' (a tombstone until HA has removed it). A sync round PULLS first (apply HA's renames, ticks and
removals; link HA items to unlinked rows by text — the row's text or `ha_text`, the text we last sent — which also
absorbs an add whose response was lost), then PUSHES what is still pending, then re-pulls to link its adds.

Every local write bumps `rev`. A push only finishes what it started: its writes after an `await` are conditional on
the row's rev being unchanged, so a tick, rename or delete that lands while HA is answering is never lost, undone or
resurrected. HA being down just skips the round; everything keeps working locally.

Gluten: a GF twin of a wheat product ("Long pasta" for spaghetti) or a `label` item goes
on the shared list WITH the marker ("GM Hosszú tészta") — whoever shops from the phone must not buy the wheat one.
"""
from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
from datetime import datetime
from typing import Any, Callable

from .catalogue import Catalogue, Item, fold
from .events import Broadcaster
from .gluten import GF_PREFIX, marked, needs_marker   # noqa: F401 (GF_PREFIX re-exported for callers)
from .ha import HAClient

log = logging.getLogger(__name__)
ENTITY = 'todo.shopping_list'
_MARKED = re.compile(r'(^|[\s(])(gf|gm)\b|glut[eé]n', re.I)    # only to strip a typed marker before lookup
MAX_TEXT = 200


class NotFound(KeyError):
    pass


class BadText(ValueError):
    pass


def canonical(cat: Catalogue, item_id: str) -> Item:
    """The item that goes on the list: a hidden wheat item becomes its visible GF twin."""
    item = cat.items.get(item_id)
    if item is None:
        raise NotFound(item_id)
    if item.gluten == 'contains' and item.swap:
        item = cat.items[item.swap]
    return item


def text_for_item(cat: Catalogue, item_id: str, lang: str) -> str:
    item = canonical(cat, item_id)
    name = item.hu if lang == 'hu' else item.en
    return marked(name, lang) if needs_marker(cat, item) else name


def entry(cat: Catalogue, index: dict[str, str], lang: str, text: str | None,
          item_id: str | None) -> tuple[str, str | None]:
    """(text, item_id) for a new list row. A catalogue item gets its name in the UI language; typed text keeps the
    user's words but is linked to the item it names, and marked when it is gluten-sensitive."""
    if item_id:
        return text_for_item(cat, item_id, lang), canonical(cat, item_id).id
    text = (text or '').strip()
    if not text:
        raise BadText('text or item_id required')
    hit = index.get(fold(text)) or index.get(fold(_MARKED.sub(' ', text)).strip())
    if hit is None:
        return text, None
    item = canonical(cat, hit)
    return (marked(text, lang) if needs_marker(cat, item) else text), item.id


def _row(r: sqlite3.Row) -> dict[str, Any]:
    return {'id': r['id'], 'text': r['text'], 'item_id': r['item_id'], 'done': bool(r['done']),
            'ha_linked': r['ha_uid'] is not None}


def list_items(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [_row(r) for r in conn.execute(
        "SELECT * FROM shopping_item WHERE pending IS NOT 'delete' AND gone = 0 ORDER BY done, id")]


def add(conn: sqlite3.Connection, text: str, item_id: str | None, now: datetime) -> dict[str, Any]:
    text = text.strip()[:MAX_TEXT]
    if not text:
        raise BadText('empty')
    key = fold(text)
    for r in conn.execute("SELECT * FROM shopping_item WHERE done = 0 AND gone = 0 AND pending IS NOT 'delete'"):
        if (item_id and r['item_id'] == item_id) or fold(r['text']) == key:
            return _row(r)
    cur = conn.execute("INSERT INTO shopping_item (text, item_id, pending, added_at, updated_at) "
                       "VALUES (?, ?, 'add', ?, ?)", (text, item_id, now.isoformat(), now.isoformat()))
    return _row(conn.execute('SELECT * FROM shopping_item WHERE id = ?', (cur.lastrowid,)).fetchone())


def _get(conn: sqlite3.Connection, item: int) -> sqlite3.Row:
    r = conn.execute("SELECT * FROM shopping_item WHERE id = ? AND pending IS NOT 'delete'", (item,)).fetchone()
    if r is None:
        raise NotFound(item)
    return r


def update(conn: sqlite3.Connection, item: int, now: datetime, done: bool | None = None,
           text: str | None = None) -> dict[str, Any]:
    if text is not None and not text.strip():
        raise BadText('empty')
    r = _get(conn, item)
    pending = 'add' if r['pending'] == 'add' else 'update'       # 'adding' -> 'update': pushed after the add lands
    conn.execute('UPDATE shopping_item SET done = ?, text = ?, pending = ?, gone = 0, rev = rev + 1, updated_at = ? '
                 'WHERE id = ?', (int(r['done'] if done is None else done),
                                  (r['text'] if text is None else text.strip()[:MAX_TEXT]), pending, now.isoformat(), item))
    return _row(_get(conn, item))


def delete(conn: sqlite3.Connection, item: int, now: datetime) -> None:
    r = _get(conn, item)
    if r['pending'] == 'add' and r['ha_text'] is None:           # never sent: HA cannot have it
        conn.execute('DELETE FROM shopping_item WHERE id = ?', (item,))
    else:                                                         # a tombstone until HA has removed it
        conn.execute("UPDATE shopping_item SET pending = 'delete', rev = rev + 1, updated_at = ? WHERE id = ?",
                     (now.isoformat(), item))


def clear_done(conn: sqlite3.Connection, now: datetime) -> None:
    for r in conn.execute("SELECT id FROM shopping_item WHERE done = 1 AND pending IS NOT 'delete'").fetchall():
        delete(conn, r['id'], now)


class ShoppingSync:
    def __init__(self, ha: HAClient, conn: sqlite3.Connection, events: Broadcaster, now: Callable[[], datetime]):
        self.ha, self.conn, self.events, self.now = ha, conn, events, now
        self.list_ok = False
        self.lock = asyncio.Lock()

    def _publish(self) -> None:
        self.events.publish('shopping', {'items': list_items(self.conn)})

    async def round(self) -> None:
        if not self.ha.configured:
            return
        async with self.lock:
            if not self.list_ok:
                self.list_ok = await self.ha.ensure_shopping_list()
                if not self.list_ok:
                    return
            remote = await self.ha.todo_items(ENTITY)
            if remote is None:
                return
            changed = self._pull(remote)
            pushed_changed, sent = await self._push()
            changed |= pushed_changed
            if sent:                                        # link our adds at once, before HA can rename them
                remote = await self.ha.todo_items(ENTITY)
                if remote is not None:
                    changed |= self._pull(remote)
            if changed:
                self._publish()

    def _pull(self, remote: list[dict[str, Any]]) -> bool:
        c, now, changed = self.conn, self.now().isoformat(), False
        by_uid = {i['uid']: i for i in remote}
        rows = c.execute('SELECT * FROM shopping_item').fetchall()
        linked = {r['ha_uid'] for r in rows if r['ha_uid']}
        for r in rows:
            uid = r['ha_uid']
            if uid is None:
                continue
            h = by_uid.get(uid)
            if h is None:                                   # removed in HA (or our delete already happened)
                c.execute('DELETE FROM shopping_item WHERE id = ?', (r['id'],))
                changed = True
            elif r['pending'] is None:                      # HA's version wins when we have nothing pending
                done = h.get('status') == 'completed'
                if h['summary'] != r['text'] or done != bool(r['done']) or done != bool(r['gone']):
                    # ticked off in HA -> gone here; unticked there -> back
                    c.execute('UPDATE shopping_item SET text = ?, ha_text = ?, done = ?, gone = ?, updated_at = ? '
                              'WHERE id = ?', (h['summary'], h['summary'], int(done), int(done), now, r['id']))
                    changed = True
        # link HA items we don't know by uid to rows HA may hold under that text: ours whose add went out (or may
        # have — a lost response), renamed since, or deleted since
        unlinked = c.execute('SELECT * FROM shopping_item WHERE ha_uid IS NULL ORDER BY id').fetchall()
        for h in remote:
            if h['uid'] in linked:
                continue
            key, done = fold(h['summary']), h.get('status') == 'completed'
            match = next((r for r in unlinked if key in {fold(r['text']), fold(r['ha_text'] or '')}), None)
            if match is not None:
                unlinked.remove(match)
                pending = match['pending']
                if pending in ('add', 'adding', None):
                    same = h['summary'] == match['text'] and done == bool(match['done'])
                    pending = None if same else 'update'
                c.execute('UPDATE shopping_item SET ha_uid = ?, ha_text = ?, pending = ? WHERE id = ?',
                          (h['uid'], h['summary'], pending, match['id']))
            else:                                           # added in HA (the phone)
                c.execute('INSERT INTO shopping_item (text, ha_text, ha_uid, done, gone, added_at, updated_at) '
                          'VALUES (?, ?, ?, ?, ?, ?, ?)', (h['summary'], h['summary'], h['uid'], int(done), int(done),
                                                           now, now))
                changed = True
        for r in unlinked:
            if r['pending'] == 'delete':                    # a tombstone HA turned out not to have: done
                c.execute('DELETE FROM shopping_item WHERE id = ?', (r['id'],))
            elif r['pending'] == 'adding':                  # a push died mid-way (crash): send it again
                c.execute("UPDATE shopping_item SET pending = 'add' WHERE id = ?", (r['id'],))
        return changed

    async def _push(self) -> tuple[bool, int]:
        c, changed, sent = self.conn, False, 0
        for r in c.execute('SELECT * FROM shopping_item WHERE pending IS NOT NULL ORDER BY id').fetchall():
            rid, rev = r['id'], r['rev']
            if r['pending'] == 'add':
                c.execute("UPDATE shopping_item SET pending = 'adding', ha_text = ? WHERE id = ?", (r['text'], rid))
                ok = await self.ha.call_service('todo', 'add_item', {'entity_id': ENTITY, 'item': r['text']})
                sent += 1                                   # even on failure: HA may have it (a lost response)
                if ok is not None:                          # linked by text by the re-pull
                    c.execute("UPDATE shopping_item SET pending = NULL WHERE id = ? AND rev = ? AND pending = 'adding'",
                              (rid, rev))
                else:
                    c.execute("UPDATE shopping_item SET pending = 'add' WHERE id = ? AND pending IN ('adding', 'update') "
                              "AND ha_uid IS NULL", (rid,))
            elif r['ha_uid'] is None:
                continue                                    # wait for the pull to link it
            elif r['pending'] == 'update':
                ok = await self.ha.call_service('todo', 'update_item', {
                    'entity_id': ENTITY, 'item': r['ha_uid'], 'rename': r['text'],
                    'status': 'completed' if r['done'] else 'needs_action'})
                if ok is not None:
                    c.execute('UPDATE shopping_item SET pending = NULL, ha_text = ? WHERE id = ? AND rev = ?',
                              (r['text'], rid, rev))
            elif r['pending'] == 'delete':
                ok = await self.ha.call_service('todo', 'remove_item', {'entity_id': ENTITY, 'item': [r['ha_uid']]})
                if ok is not None:
                    c.execute('DELETE FROM shopping_item WHERE id = ? AND rev = ?', (rid, rev))
                    changed = True
        return changed, sent

    async def run(self, every: float) -> None:
        while True:
            try:
                await self.round()
            except Exception:                               # one bad round must not end the loop
                log.exception('shopping sync round failed')
            await asyncio.sleep(every)
