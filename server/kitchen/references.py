"""Stored catalogue references: rewritten through catalogue/replaced.yaml at start-up, then checked.

Everything that stores a catalogue id: pantry switches (an item id or `group:<group id>`), shopping items' `item_id`,
recipe lines' `item_id` (lines not corrected by hand are re-matched anyway — recipes.rematch_all) and blend parts'
`spice_id`, sauce lines' `item_id` and `spice_id` (`STORED_IDS` lists the item-id columns; a guard test fails when a table stores one that is not listed). A reference
that still leads nowhere is reported by /api/health as 503 + the list — loud, without taking the kitchen down.
"""
from __future__ import annotations

import sqlite3

from .catalogue import Catalogue

GROUP = 'group:'
# every column (besides pantry_state.node) that stores a catalogue item id
STORED_IDS = (('shopping_item', 'item_id'), ('recipe_ingredient', 'item_id'), ('blend_part', 'spice_id'),
              ('sauce_ingredient', 'item_id'), ('sauce_ingredient', 'spice_id'))


def _node_exists(cat: Catalogue, node: str) -> bool:
    return node[len(GROUP):] in cat.groups if node.startswith(GROUP) else node in cat.items


def _resolve_node(cat: Catalogue, node: str) -> str:
    return GROUP + cat.resolve(node[len(GROUP):]) if node.startswith(GROUP) else cat.resolve(node)


def migrate(conn: sqlite3.Connection, cat: Catalogue) -> int:
    """Rewrite every stored id through `replaced`. Returns how many rows changed."""
    if not cat.replaced:
        return 0
    changed = 0
    conn.execute('BEGIN')
    try:
        for r in conn.execute('SELECT node, have, changed_at FROM pantry_state').fetchall():
            new = _resolve_node(cat, r['node'])
            if new != r['node']:
                # the successor's own row wins if it has one (it is the newer truth)
                conn.execute('INSERT OR IGNORE INTO pantry_state (node, have, changed_at) VALUES (?, ?, ?)',
                             (new, r['have'], r['changed_at']))
                conn.execute('DELETE FROM pantry_state WHERE node = ?', (r['node'],))
                changed += 1
        for table, col in STORED_IDS:
            for r in conn.execute(f'SELECT rowid AS k, {col} AS v FROM {table} WHERE {col} IS NOT NULL').fetchall():
                new = cat.resolve(r['v'])
                if new != r['v']:
                    conn.execute(f'UPDATE {table} SET {col} = ? WHERE rowid = ?', (new, r['k']))
                    changed += 1
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise
    return changed


def dangling(conn: sqlite3.Connection, cat: Catalogue) -> list[str]:
    """Every stored reference that leads to no catalogue node, as readable strings."""
    out = [f'pantry: {r["node"]}' for r in conn.execute('SELECT node FROM pantry_state')
           if not _node_exists(cat, r['node'])]
    out += [f'shopping #{r["id"]}: {r["item_id"]}' for r in
            conn.execute('SELECT id, item_id FROM shopping_item WHERE item_id IS NOT NULL') if r['item_id'] not in cat.items]
    out += [f'recipe {r["recipe_id"]} line {r["pos"]}: {r["item_id"]}' for r in
            conn.execute('SELECT recipe_id, pos, item_id FROM recipe_ingredient WHERE item_id IS NOT NULL')
            if r['item_id'] not in cat.items]
    out += [f'blend {r["blend_id"]} part {r["pos"]}: {r["spice_id"]}' for r in
            conn.execute('SELECT blend_id, pos, spice_id FROM blend_part') if r['spice_id'] not in cat.items]
    out += [f'sauce {r["sauce_id"]} line {r["pos"]}: {r["v"]}' for col in ('item_id', 'spice_id') for r in
            conn.execute(f'SELECT sauce_id, pos, {col} AS v FROM sauce_ingredient WHERE {col} IS NOT NULL')
            if r['v'] not in cat.items]
    return out
