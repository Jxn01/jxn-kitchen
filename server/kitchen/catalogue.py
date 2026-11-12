"""The ingredient & supplies catalogue: category -> group -> item, bilingual, gluten-flagged (spec §4.1, §7).

The YAML in catalogue/ is the source of truth; it is loaded at start and validated (validate() returns every
problem; the guard test requires zero). Ids are stable: pantry state and recipe matches key on them.
"""
from __future__ import annotations

import pathlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import yaml

GLUTEN = ('free', 'contains', 'label')
KINDS = ('food', 'supply')


@dataclass
class Item:
    id: str
    en: str
    hu: str
    group: str
    category: str
    aliases: list[str] = field(default_factory=list)
    icon: str | None = None          # None -> the group's icon
    gluten: str = 'free'             # free | contains | label
    swap: str | None = None          # for `contains`: the GF item to use instead
    pantry: bool = True              # False: a recipe-matching target only (never a tile)
    staple: bool = False             # True: counts as in unless switched off
    kind: str = 'food'               # inherited from the category
    tip_en: str | None = None        # a method tweak shown with the GF version (mostly on `contains` items)
    tip_hu: str | None = None


@dataclass
class Group:
    id: str
    en: str
    hu: str
    icon: str
    category: str
    items: list[str] = field(default_factory=list)


@dataclass
class Category:
    id: str
    en: str
    hu: str
    icon: str
    color: str
    kind: str
    groups: list[str] = field(default_factory=list)


@dataclass
class Catalogue:
    categories: list[Category]
    groups: dict[str, Group]
    items: dict[str, Item]
    _order: list[tuple[str, str]] = field(default_factory=list)   # (kind, id) in load order, for duplicate checks
    _unknown: list[str] = field(default_factory=list)            # unknown keys seen while loading
    replaced: dict[str, str] = field(default_factory=dict)       # removed id -> its successor (replaced.yaml)

    def resolve(self, node_id: str) -> str:
        """A stored id as it is now: followed through `replaced` (chains included, cycles stopped)."""
        seen = set()
        while node_id in self.replaced and node_id not in seen:
            seen.add(node_id)
            node_id = self.replaced[node_id]
        return node_id

    def node(self, node_id: str) -> Item | Group | Category | None:
        return self.items.get(node_id) or self.groups.get(node_id) or next(
            (c for c in self.categories if c.id == node_id), None)


def fold(text: str) -> str:
    """Lower-case, strip accents (ő->o, ű->u, é->e…), collapse whitespace. Search and matching both use it."""
    decomposed = unicodedata.normalize('NFKD', text.casefold())
    stripped = ''.join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', stripped).strip()


def icon_id(ref: str) -> str:
    """'om:1F969' -> 'om-1f969'; 'c:chicken-wing' -> 'c-chicken-wing'; a bare name is a manifest id."""
    if ref.startswith('om:'):
        return 'om-' + ref[3:].lower()
    if ref.startswith('c:'):
        return 'c-' + ref[2:]
    return ref


CATEGORY_KEYS = {'id', 'en', 'hu', 'icon', 'color', 'kind'}
GROUP_KEYS = {'id', 'en', 'hu', 'icon', 'items'}
ITEM_KEYS = {'id', 'en', 'hu', 'aliases', 'icon', 'gluten', 'swap', 'pantry', 'staple', 'tip_en', 'tip_hu'}


def _unknown_keys(where: str, d: dict, allowed: set[str]) -> list[str]:
    # YAML trap: in a flow mapping `{hu: Tojás, tejtermék}` the comma splits the value and silently adds a key
    # `tejtermék: null`. Every unexpected key is reported so that can never pass unnoticed.
    return [f'unknown key in {where}: {k!r}' for k in d if k not in allowed]


def load(directory: pathlib.Path | str) -> Catalogue:
    directory = pathlib.Path(directory)
    raw_cats = yaml.safe_load((directory / 'categories.yaml').read_text())['categories']
    unknown: list[str] = []
    for c in raw_cats:
        unknown += _unknown_keys(f"category {c.get('id')}", c, CATEGORY_KEYS)
    categories = [Category(id=c['id'], en=c.get('en', ''), hu=c.get('hu', ''), icon=c['icon'], color=c['color'],
                           kind=c.get('kind', 'food')) for c in raw_cats]
    by_id = {c.id: c for c in categories}
    groups: dict[str, Group] = {}
    items: dict[str, Item] = {}
    order: list[tuple[str, str]] = [('category', c.id) for c in categories]
    for path in sorted(directory.glob('*/*.yaml')):
        doc = yaml.safe_load(path.read_text())
        cat = by_id[doc['category']]
        for g in doc['groups']:
            unknown += _unknown_keys(f"group {g.get('id')} ({path.name})", g, GROUP_KEYS)
            group = Group(id=g['id'], en=g.get('en', ''), hu=g.get('hu', ''), icon=g['icon'], category=cat.id)
            order.append(('group', group.id))
            groups.setdefault(group.id, group)
            cat.groups.append(group.id)
            for it in g.get('items', []):
                unknown += _unknown_keys(f"item {it.get('id')} ({path.name})", it, ITEM_KEYS)
                item = Item(id=it['id'], en=it.get('en', ''), hu=it.get('hu', ''), group=group.id, category=cat.id,
                            aliases=list(it.get('aliases', [])), icon=it.get('icon'), gluten=it.get('gluten', 'free'),
                            swap=it.get('swap'), pantry=it.get('pantry', True), staple=it.get('staple', False),
                            kind=cat.kind, tip_en=it.get('tip_en'), tip_hu=it.get('tip_hu'))
                order.append(('item', item.id))
                items.setdefault(item.id, item)
                group.items.append(item.id)
    replaced_path = directory / 'replaced.yaml'
    replaced = (yaml.safe_load(replaced_path.read_text()) or {}) if replaced_path.exists() else {}
    if not isinstance(replaced, dict):
        unknown.append('replaced.yaml must be a mapping old-id: new-id')
        replaced = {}
    return Catalogue(categories=categories, groups=groups, items=items, _order=order, _unknown=unknown,
                     replaced={str(k): str(v) for k, v in replaced.items()})


def validate(cat: Catalogue, icon_ids: set[str] | None = None) -> list[str]:
    errors: list[str] = list(cat._unknown)
    for old, new in cat.replaced.items():
        if cat.node(old) is not None:
            errors.append(f'replaced.yaml: {old} still exists — only removed ids belong there')
        target = cat.resolve(old)
        if cat.node(target) is None:
            errors.append(f'replaced.yaml: {old} -> {new} leads to {target}, which does not exist')
    nodes: list[Any] = [*cat.categories, *cat.groups.values(), *cat.items.values()]
    # duplicate ids across every level: as declared in the files (load order keeps every occurrence) and as the
    # objects now stand (an id edited onto another's)
    from collections import Counter
    declared = Counter(nid for _, nid in cat._order)
    current = Counter([c.id for c in cat.categories] + [g.id for g in cat.groups.values()] +
                      [i.id for i in cat.items.values()])
    for nid in sorted({n for n, k in declared.items() if k > 1} | {n for n, k in current.items() if k > 1}):
        errors.append(f'duplicate id: {nid}')
    for n in nodes:
        for lang in ('en', 'hu'):
            if not getattr(n, lang, '').strip():
                errors.append(f'missing {lang}: {n.id}')
    for c in cat.categories:
        if c.kind not in KINDS:
            errors.append(f'bad kind: {c.id}')
    # Matching keys (spec §7.5): aliases outrank display names. Aliases must be unique; display names must be
    # unique; a display name may equal another item's alias only for a wheat -> GF swap pair ("kenyér" in a recipe
    # is the hidden wheat bread, whose swap is the "Kenyér" GF tile).
    alias_owner: dict[str, str] = {}
    name_owner: dict[str, str] = {}
    for it in cat.items.values():
        if it.gluten not in GLUTEN:
            errors.append(f'bad gluten: {it.id} ({it.gluten})')
        if it.kind == 'supply' and it.gluten != 'free':
            errors.append(f'supply must be gluten free: {it.id}')
        if it.gluten == 'contains':
            target = cat.items.get(it.swap or '')
            if target is None:
                errors.append(f'swap missing or unknown: {it.id} -> {it.swap}')
            elif target.gluten != 'free' or not target.pantry:
                errors.append(f'swap must be a visible gluten-free item: {it.id} -> {it.swap}')
            if it.pantry:                      # a wheat item never becomes a tile in a fully GF kitchen
                errors.append(f'contains item must be hidden (pantry: false): {it.id}')
        if it.id.startswith('gf-') and not any(o.gluten == 'contains' and o.swap == it.id for o in cat.items.values()):
            # gf-* = "the GF version of a wheat product"; its plain name must be claimed by that wheat item
            errors.append(f'gf- item is no wheat item\'s swap: {it.id}')
        for a in {fold(a) for a in it.aliases}:
            if alias_owner.get(a, it.id) != it.id:
                errors.append(f'alias collision: "{a}" ({alias_owner[a]}, {it.id})')
            alias_owner.setdefault(a, it.id)
        for n in {fold(it.en), fold(it.hu)}:
            if name_owner.get(n, it.id) != it.id:
                errors.append(f'name collision: "{n}" ({name_owner[n]}, {it.id})')
            name_owner.setdefault(n, it.id)
    for n, owner in name_owner.items():
        a_owner = alias_owner.get(n)
        if a_owner and a_owner != owner and cat.items[a_owner].swap != owner:
            errors.append(f'alias collision: "{n}" is {owner}\'s name and {a_owner}\'s alias (not a swap pair)')
    if icon_ids is not None:
        refs = [(c.id, c.icon) for c in cat.categories] + [(g.id, g.icon) for g in cat.groups.values()] + \
               [(i.id, i.icon) for i in cat.items.values() if i.icon]
        for nid, ref in refs:
            if icon_id(ref) not in icon_ids:
                errors.append(f'unknown icon: {nid} -> {ref}')
    return errors


def match_index(cat: Catalogue) -> dict[str, str]:
    """folded key -> item id, for search and recipe matching: aliases first, then display names (never overriding)."""
    index: dict[str, str] = {}
    for it in cat.items.values():
        for a in it.aliases:
            index.setdefault(fold(a), it.id)
    for it in cat.items.values():
        for n in (it.en, it.hu):
            index.setdefault(fold(n), it.id)
    return index


def icon_refs(cat: Catalogue) -> set[str]:
    refs = {c.icon for c in cat.categories} | {g.icon for g in cat.groups.values()}
    return refs | {i.icon for i in cat.items.values() if i.icon}


def to_json(cat: Catalogue) -> dict[str, Any]:
    """The tree the web app consumes (both languages; the client picks)."""
    def item(i: Item) -> dict[str, Any]:
        d: dict[str, Any] = {'id': i.id, 'en': i.en, 'hu': i.hu, 'icon': icon_id(i.icon) if i.icon else None,
                             'gluten': i.gluten}
        if i.aliases:
            d['aliases'] = i.aliases
        if i.staple:
            d['staple'] = True
        return d
    return {'categories': [
        {'id': c.id, 'en': c.en, 'hu': c.hu, 'icon': icon_id(c.icon), 'color': c.color, 'kind': c.kind,
         'groups': [{'id': g.id, 'en': g.en, 'hu': g.hu, 'icon': icon_id(g.icon),
                     'items': [item(cat.items[i]) for i in g.items if cat.items[i].pantry]}
                    for g in (cat.groups[gid] for gid in c.groups)]}
        for c in cat.categories]}
