"""Recipe folders (2026-11-03): a tree the owner files recipes into — create, rename, nest, move, delete.

Rules, all kept here (the endpoints only translate errors):
- A folder's name is 1–60 characters after trimming, and unique among its siblings, compared accent- and case-folded
  (`Levesek` and `levesek` cannot share a parent). The top level counts as one parent.
- Nesting goes at most MAX_DEPTH levels deep (a top-level folder is level 1), and a folder can never move into itself
  or anything inside it.
- A recipe sits in at most one folder; NULL means the top level.
- **Deleting a folder never deletes a recipe.** Its recipes and its subfolders move up into its parent (the top level
  for a top-level folder). A subfolder whose name is already taken there is renamed `Name (2)`, `Name (3)`, ….
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Iterable

from .catalogue import fold

MAX_NAME = 60
MAX_DEPTH = 8


class NotFound(KeyError):
    """A folder (or a recipe in a move) that does not exist."""


class Invalid(ValueError):
    """A request the rules refuse. `code` says which: name, taken, cycle, depth."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def _row(conn: sqlite3.Connection, fid: int) -> sqlite3.Row:
    r = conn.execute('SELECT * FROM recipe_folder WHERE id = ?', (fid,)).fetchone()
    if r is None:
        raise NotFound(fid)
    return r


def _clean(name: str) -> str:
    n = ' '.join(name.split())
    if not 1 <= len(n) <= MAX_NAME:
        raise Invalid('name', f'a folder name is 1–{MAX_NAME} characters')
    return n


def _taken(conn: sqlite3.Connection, parent_id: int | None, name: str, exclude: int | None = None) -> bool:
    f = fold(name)
    return any(fold(r['name']) == f and r['id'] != exclude for r in
               conn.execute('SELECT id, name FROM recipe_folder WHERE parent_id IS ?', (parent_id,)))


def _free_name(conn: sqlite3.Connection, parent_id: int | None, name: str, exclude: int) -> str:
    if not _taken(conn, parent_id, name, exclude):
        return name
    n = 2
    while True:
        suffix = f' ({n})'
        cand = name[:MAX_NAME - len(suffix)] + suffix
        if not _taken(conn, parent_id, cand, exclude):
            return cand
        n += 1


def _depth(conn: sqlite3.Connection, fid: int | None) -> int:
    """How deep `fid` sits: the top level is 0, a top-level folder 1."""
    d = 0
    while fid is not None:
        fid = _row(conn, fid)['parent_id']
        d += 1
    return d


def _height(conn: sqlite3.Connection, fid: int) -> int:
    """Levels in the subtree under and including `fid` (a folder with no subfolders is 1)."""
    kids = [r['id'] for r in conn.execute('SELECT id FROM recipe_folder WHERE parent_id = ?', (fid,))]
    return 1 + max((_height(conn, k) for k in kids), default=0)


def _inside(conn: sqlite3.Connection, fid: int, ancestor: int) -> bool:
    """True when `fid` is `ancestor` or anywhere below it."""
    cur: int | None = fid
    while cur is not None:
        if cur == ancestor:
            return True
        cur = _row(conn, cur)['parent_id']
    return False


def _view(conn: sqlite3.Connection, r: sqlite3.Row) -> dict[str, Any]:
    recipes = conn.execute('SELECT COUNT(*) FROM recipe WHERE folder_id = ?', (r['id'],)).fetchone()[0]
    folders = conn.execute('SELECT COUNT(*) FROM recipe_folder WHERE parent_id = ?', (r['id'],)).fetchone()[0]
    return {'id': r['id'], 'name': r['name'], 'parent_id': r['parent_id'], 'recipes': recipes, 'folders': folders,
            'created_at': r['created_at'], 'updated_at': r['updated_at']}


def list_all(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every folder, flat, siblings in name order (accent-folded). The client builds the tree from parent_id."""
    rows = conn.execute('SELECT * FROM recipe_folder').fetchall()
    return [_view(conn, r) for r in sorted(rows, key=lambda r: (fold(r['name']), r['id']))]


def get(conn: sqlite3.Connection, fid: int) -> dict[str, Any]:
    return _view(conn, _row(conn, fid))


def create(conn: sqlite3.Connection, name: str, parent_id: int | None, now: datetime) -> int:
    n = _clean(name)
    if parent_id is not None:
        _row(conn, parent_id)
    if _depth(conn, parent_id) + 1 > MAX_DEPTH:
        raise Invalid('depth', f'folders nest at most {MAX_DEPTH} levels deep')
    if _taken(conn, parent_id, n):
        raise Invalid('taken', 'a folder with that name is already there')
    ts = now.isoformat()
    cur = conn.execute('INSERT INTO recipe_folder (name, parent_id, created_at, updated_at) VALUES (?,?,?,?)',
                       (n, parent_id, ts, ts))
    return int(cur.lastrowid)


_KEEP = object()   # "parent not given": a rename alone must not move the folder to the top level


def update(conn: sqlite3.Connection, fid: int, now: datetime, name: str | None = None,
           parent_id: Any = _KEEP) -> None:
    """Rename and/or move one folder. `parent_id=None` moves it to the top level; leave it out to keep it in place."""
    r = _row(conn, fid)
    n = _clean(name) if name is not None else r['name']
    parent = r['parent_id'] if parent_id is _KEEP else parent_id
    if parent is not None:
        _row(conn, parent)
        if _inside(conn, parent, fid):
            raise Invalid('cycle', 'a folder cannot go inside itself')
    if parent != r['parent_id'] and _depth(conn, parent) + _height(conn, fid) > MAX_DEPTH:
        raise Invalid('depth', f'folders nest at most {MAX_DEPTH} levels deep')
    if _taken(conn, parent, n, exclude=fid):
        raise Invalid('taken', 'a folder with that name is already there')
    conn.execute('UPDATE recipe_folder SET name = ?, parent_id = ?, updated_at = ? WHERE id = ?',
                 (n, parent, now.isoformat(), fid))


def delete(conn: sqlite3.Connection, fid: int, now: datetime) -> dict[str, int]:
    """Remove one folder; its recipes and subfolders move up into its parent. Returns what moved."""
    r = _row(conn, fid)
    parent = r['parent_id']
    conn.execute('BEGIN')
    try:
        moved_recipes = conn.execute('UPDATE recipe SET folder_id = ? WHERE folder_id = ?', (parent, fid)).rowcount
        kids = conn.execute('SELECT id, name FROM recipe_folder WHERE parent_id = ? ORDER BY id', (fid,)).fetchall()
        for k in kids:
            conn.execute('UPDATE recipe_folder SET parent_id = ?, updated_at = ? WHERE id = ?',
                         (parent, now.isoformat(), k['id']))
            new = _free_name(conn, parent, k['name'], exclude=k['id'])
            if new != k['name']:
                conn.execute('UPDATE recipe_folder SET name = ? WHERE id = ?', (new, k['id']))
        conn.execute('DELETE FROM recipe_folder WHERE id = ?', (fid,))
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise
    return {'recipes': moved_recipes, 'folders': len(kids)}


def move_recipes(conn: sqlite3.Connection, ids: Iterable[int], folder_id: int | None) -> int:
    """File recipes into `folder_id` (None = the top level). All or nothing: one unknown id moves none."""
    ids = list(dict.fromkeys(ids))
    if folder_id is not None:
        _row(conn, folder_id)
    conn.execute('BEGIN')
    try:
        for rid in ids:
            if conn.execute('UPDATE recipe SET folder_id = ? WHERE id = ?', (folder_id, rid)).rowcount == 0:
                raise NotFound(rid)
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise
    return len(ids)


def exists(conn: sqlite3.Connection, fid: int) -> bool:
    return conn.execute('SELECT 1 FROM recipe_folder WHERE id = ?', (fid,)).fetchone() is not None
