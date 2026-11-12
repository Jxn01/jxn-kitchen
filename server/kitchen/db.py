"""SQLite access: one file, WAL, ordered migrations recorded in schema_version."""
from __future__ import annotations

import pathlib
import sqlite3

# Append-only. Each entry is one migration; its index + 1 is its version. Never edit a shipped one.
MIGRATIONS: list[str] = [
    """CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)""",
    # 2: the pantry — one row per switched node: an item id, or 'group:<id>' for "some … somewhere". Staples have a row
    # only when switched off. Nothing else is stored about pantry items, by design (no quantities, no dates).
    """CREATE TABLE pantry_state (node TEXT PRIMARY KEY, have INTEGER NOT NULL, changed_at TEXT NOT NULL)""",
    # 3: the shopping list, mirrored with HA's todo.shopping_list. pending = a local change not yet pushed to HA:
    # 'add' (never reached HA), 'update', 'delete' (a tombstone until HA has removed it).
    """CREATE TABLE shopping_item (id INTEGER PRIMARY KEY, text TEXT NOT NULL, item_id TEXT, ha_uid TEXT UNIQUE,
       done INTEGER NOT NULL DEFAULT 0, pending TEXT, added_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    # 4: recipes. Ingredient lines keep the raw text AND the parse/match; ok_gf = "marked GF by hand" for an
    # unmatched line; user_item = the owner corrected the match.
    """CREATE TABLE recipe (id INTEGER PRIMARY KEY, title TEXT NOT NULL, lang TEXT NOT NULL, source_url TEXT,
       source_site TEXT, image TEXT, servings INTEGER, prep_min INTEGER, cook_min INTEGER, total_min INTEGER,
       notes TEXT, origin TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
     CREATE TABLE recipe_ingredient (recipe_id INTEGER NOT NULL REFERENCES recipe(id), pos INTEGER NOT NULL,
       raw TEXT NOT NULL, qty REAL, qty_max REAL, unit TEXT, name TEXT NOT NULL, note TEXT, item_id TEXT,
       match_how TEXT, ok_gf INTEGER NOT NULL DEFAULT 0, user_item INTEGER NOT NULL DEFAULT 0,
       PRIMARY KEY (recipe_id, pos));
     CREATE TABLE recipe_step (recipe_id INTEGER NOT NULL REFERENCES recipe(id), pos INTEGER NOT NULL,
       text TEXT NOT NULL, PRIMARY KEY (recipe_id, pos));
     CREATE TABLE recipe_tag (recipe_id INTEGER NOT NULL REFERENCES recipe(id), tag TEXT NOT NULL,
       PRIMARY KEY (recipe_id, tag));""",
    # 5: shopping sync safety. rev = bumped by every local write, so a sync round only finishes what it started
    # (a write that landed while HA was answering is never overwritten). ha_text = the text HA last knew, so a row
    # renamed while its add was in flight still links. gone = ticked off in HA: hidden here (spec §6.6).
    """ALTER TABLE shopping_item ADD COLUMN rev INTEGER NOT NULL DEFAULT 0;
     ALTER TABLE shopping_item ADD COLUMN ha_text TEXT;
     ALTER TABLE shopping_item ADD COLUMN gone INTEGER NOT NULL DEFAULT 0;
     UPDATE shopping_item SET ha_text = text WHERE ha_uid IS NOT NULL""",
    # 6: counters — 'pantry' = the pantry state's revision, bumped by every write, so a client can drop a late
    # (older) answer or SSE event instead of letting it overwrite newer state.
    """CREATE TABLE counter (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
     INSERT INTO counter (name, value) VALUES ('pantry', 0)""",
    # 7: kitchen timers (spec §6.5) — state running (ends_at) | paused (remaining s) | done | dismissed; notified =
    # the phone was pinged (once).
    """CREATE TABLE timer (id INTEGER PRIMARY KEY, label TEXT NOT NULL, seconds INTEGER NOT NULL, ends_at TEXT,
       remaining INTEGER, state TEXT NOT NULL, recipe_id INTEGER, step_pos INTEGER, notified INTEGER NOT NULL DEFAULT 0,
       created_at TEXT NOT NULL)""",
    # 8: the scan inbox — each file imported once (by path + size + mtime: a rescan under the same name is new);
    # recipe_ids = the drafts it became (JSON list).
    """CREATE TABLE scan_import (path TEXT NOT NULL, size INTEGER NOT NULL, mtime REAL NOT NULL, recipe_ids TEXT NOT NULL,
       at TEXT NOT NULL, PRIMARY KEY (path, size, mtime))""",
    # 9: the gluten item a line's NOTE mentions ("vaj a kenyérhez" -> wheat bread). Purpose phrases moved to the note
    # (2026-10-11) must not take their gluten out of the check: a GF item with such a note reads 'check', not OK.
    """ALTER TABLE recipe_ingredient ADD COLUMN note_gluten TEXT""",
    # 10: the owner's spice blends (spec 2026-10-19 §4.4). origin: typed | seed | riff; classic_id = the classic a seed
    # or a riff came from (engine/spices/classics.yaml). parts are level teaspoons; spice_id is a catalogue id.
    """CREATE TABLE blend (id INTEGER PRIMARY KEY, name TEXT NOT NULL, lang TEXT NOT NULL, notes TEXT, origin TEXT NOT NULL,
       classic_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
     CREATE TABLE blend_part (blend_id INTEGER NOT NULL REFERENCES blend(id), pos INTEGER NOT NULL, spice_id TEXT NOT NULL,
       parts REAL NOT NULL CHECK (parts > 0), PRIMARY KEY (blend_id, pos));
     CREATE TABLE blend_tag (blend_id INTEGER NOT NULL REFERENCES blend(id), tag TEXT NOT NULL, PRIMARY KEY (blend_id, tag))""",
    # 11: the owner's sauces (spec 2026-10-19 §4.4, plan SP11). A line is one of: a sauce-shelf item (shelf_id = the
    # engine/sauces entry, item_id = its catalogue item — they differ for a kitchen form like egg yolk of `eggs`), a rack
    # jar (spice_id = item_id), a blend (blend_id), a typed line matched to a catalogue item off the shelves (item_id,
    # raw) or a typed line nothing matched (raw only). Gluten is read from item_id by the gluten engine, like a recipe's.
    """CREATE TABLE sauce (id INTEGER PRIMARY KEY, name TEXT NOT NULL, lang TEXT NOT NULL, family TEXT,
       family_user INTEGER NOT NULL DEFAULT 0, yield_ml INTEGER, notes TEXT, origin TEXT NOT NULL, classic_id TEXT,
       created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
     CREATE TABLE sauce_ingredient (sauce_id INTEGER NOT NULL REFERENCES sauce(id), pos INTEGER NOT NULL, shelf_id TEXT,
       item_id TEXT, spice_id TEXT, blend_id INTEGER REFERENCES blend(id), raw TEXT, qty REAL, qty_max REAL, unit TEXT,
       name TEXT NOT NULL, note TEXT, match_how TEXT, ok_gf INTEGER NOT NULL DEFAULT 0, user_item INTEGER NOT NULL DEFAULT 0,
       note_gluten TEXT, PRIMARY KEY (sauce_id, pos));
     CREATE TABLE sauce_step (sauce_id INTEGER NOT NULL REFERENCES sauce(id), pos INTEGER NOT NULL, text TEXT NOT NULL,
       PRIMARY KEY (sauce_id, pos));
     CREATE TABLE sauce_tag (sauce_id INTEGER NOT NULL REFERENCES sauce(id), tag TEXT NOT NULL, PRIMARY KEY (sauce_id, tag))""",
    # 12: recipe folders (2026-11-03). A tree: parent_id NULL = top level. A recipe sits in at most one folder
    # (folder_id NULL = top level). Names are unique among siblings, compared accent- and case-folded — kept by
    # folders.py, not by an index, because SQLite cannot index the fold. Deleting a folder never deletes a recipe.
    """CREATE TABLE recipe_folder (id INTEGER PRIMARY KEY, name TEXT NOT NULL,
       parent_id INTEGER REFERENCES recipe_folder(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
     CREATE INDEX recipe_folder_parent ON recipe_folder(parent_id);
     ALTER TABLE recipe ADD COLUMN folder_id INTEGER REFERENCES recipe_folder(id);
     CREATE INDEX recipe_by_folder ON recipe(folder_id)""",
]


def connect(path: pathlib.Path | str) -> sqlite3.Connection:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread stays ON: the app touches SQLite only from the event loop (every DB route is `async def`);
    # a sync route would run in FastAPI's thread pool and share this connection across threads, which corrupts
    # cursors (seen as IndexError under concurrent pantry writes). Cross-thread use now fails loudly instead.
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=5000')
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute('CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)')
    current = conn.execute('SELECT COALESCE(MAX(version), 0) FROM schema_version').fetchone()[0]
    for version, sql in enumerate(MIGRATIONS, start=1):
        if version <= current:
            continue
        # One script per migration, transaction included: executescript() commits anything already open, so a
        # BEGIN issued outside it would not cover a multi-statement migration.
        try:
            conn.executescript(f'BEGIN;\n{sql};\nINSERT INTO schema_version (version) VALUES ({version});\nCOMMIT;')
        except Exception:
            if conn.in_transaction:
                conn.execute('ROLLBACK')
            raise
