"""The app's settings: a fixed set of keys with defaults and validators, stored as JSON in `settings`."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Callable


def _int_range(lo: int, hi: int) -> Callable[[Any], bool]:
    return lambda v: type(v) is int and lo <= v <= hi


def _one_of(*options: Any) -> Callable[[Any], bool]:
    return lambda v: type(v) is type(options[0]) and v in options


# Browse's built-in sites; the list with URLs lives in web/src/lib/sites.json (a test keeps the two in step)
SITE_IDS = ('nosalty', 'streetkitchen', 'mindmegette', 'receptneked')


def _site_ids(v: Any) -> bool:
    return type(v) is list and len(v) == len(set(v)) and all(type(x) is str and x in SITE_IDS for x in v)


def _custom_sites(v: Any) -> bool:
    """The owner's own Browse sites: up to 8 of {name 1–40 chars, url http(s) ≤ 300 chars}."""
    if type(v) is not list or len(v) > 8:
        return False
    for x in v:
        if type(x) is not dict or set(x) != {'name', 'url'} or type(x['name']) is not str or type(x['url']) is not str:
            return False
        if not 1 <= len(x['name'].strip()) <= 40 or len(x['url']) > 300 or not x['url'].startswith(('http://', 'https://')):
            return False
    return True


SCHEMA: dict[str, tuple[Any, Callable[[Any], bool]]] = {
    'language':         ('en', _one_of('en', 'hu')),
    'night_start':      (23, _int_range(0, 23)),       # hour the night window starts (Europe/Budapest)
    'night_end':        (6, _int_range(0, 23)),        # hour it ends; start == end means "never night"
    'idle_minutes':     (2, _one_of(1, 2, 5, 10)),      # minutes without a touch before the idle scene
    'sounds':           (True, lambda v: type(v) is bool),
    'night_brightness': (20, _int_range(5, 100)),       # backlight % at night (never 0: the display never turns off)
    'day_brightness':   (80, _int_range(5, 100)),
    'browse_sites':     (list(SITE_IDS), _site_ids),    # which built-in sites Browse shows, in this order
    'browse_custom':    ([], _custom_sites),             # the owner's own sites (GF blogs…)
}


def get_all(conn: sqlite3.Connection) -> dict[str, Any]:
    stored = {row['key']: json.loads(row['value']) for row in conn.execute('SELECT key, value FROM settings')}
    return {key: stored.get(key, default) for key, (default, _) in SCHEMA.items()}


def update(conn: sqlite3.Connection, patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if key not in SCHEMA:
            raise ValueError(f'unknown setting: {key}')
        if not SCHEMA[key][1](value):
            raise ValueError(f'bad value for {key}: {value!r}')
    conn.execute('BEGIN')
    try:
        for key, value in patch.items():
            conn.execute('INSERT INTO settings (key, value) VALUES (?, ?) '
                         'ON CONFLICT(key) DO UPDATE SET value = excluded.value', (key, json.dumps(value)))
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise
    return get_all(conn)
