"""The pantry: have / don't-have per catalogue item, plus the "I've got some <group> somewhere" switches (spec §6.2).

State shape (GET /api/pantry, SSE `pantry`):
  have        — every item that counts as in: switched on, or a staple not switched off
  groups_some — groups whose "some … somewhere" switch is on
  staples_off — staples explicitly switched off
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from .catalogue import Catalogue

GROUP_PREFIX = 'group:'


class UnknownNode(KeyError):
    pass


class HiddenItem(ValueError):
    pass


def get_state(conn: sqlite3.Connection, cat: Catalogue) -> dict[str, Any]:
    rows = {r['node']: bool(r['have']) for r in conn.execute('SELECT node, have FROM pantry_state')}
    have, staples_off = [], []
    for item in cat.items.values():
        if not item.pantry:
            continue
        on = rows.get(item.id, item.staple)
        if on:
            have.append(item.id)
        elif item.staple:
            staples_off.append(item.id)
    groups = [n[len(GROUP_PREFIX):] for n, v in rows.items()
              if n.startswith(GROUP_PREFIX) and v and n[len(GROUP_PREFIX):] in cat.groups]
    rev = conn.execute("SELECT value FROM counter WHERE name = 'pantry'").fetchone()[0]
    return {'have': sorted(have), 'groups_some': sorted(groups), 'staples_off': sorted(staples_off), 'rev': rev}


def set_node(conn: sqlite3.Connection, cat: Catalogue, node: str, have: bool, now: datetime) -> dict[str, Any]:
    if node.startswith(GROUP_PREFIX):
        if node[len(GROUP_PREFIX):] not in cat.groups:
            raise UnknownNode(node)
    else:
        item = cat.items.get(node)
        if item is None:
            raise UnknownNode(node)
        if not item.pantry:
            raise HiddenItem(node)
    conn.execute('INSERT INTO pantry_state (node, have, changed_at) VALUES (?, ?, ?) '
                 'ON CONFLICT(node) DO UPDATE SET have = excluded.have, changed_at = excluded.changed_at',
                 (node, int(have), now.isoformat()))
    conn.execute("UPDATE counter SET value = value + 1 WHERE name = 'pantry'")
    return get_state(conn, cat)


def has(cat: Catalogue, state: dict[str, Any], item_id: str) -> bool:
    """Does the kitchen have this item? A wheat (`contains`) item asks about its GF swap; a group's "some …
    somewhere" switch counts for every item in the group."""
    item = cat.items.get(item_id)
    if item is None:
        return False
    if item.gluten == 'contains' and item.swap:
        item = cat.items[item.swap]
    if item.staple and not item.pantry:             # water & co.: always there, never a tile
        return True
    return item.id in state['have'] or item.group in state['groups_some']
