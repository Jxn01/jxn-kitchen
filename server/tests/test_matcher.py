import pathlib
import re

import pytest

from kitchen import catalogue as C
from kitchen.matcher import Matcher

REAL = pathlib.Path(__file__).resolve().parents[2] / 'catalogue'
M = Matcher(C.load(REAL))

# names as the fixtures' parser output gives them (+ unit hint) -> expected catalogue item
FIXTURE_NAMES = [
    # Nosalty: paprikás csirke nokedlivel
    ('Napraforgó olaj', None, 'sunflower-oil'), ('Vöröshagyma', 'pcs', 'onion'), ('Fokhagyma', 'clove', 'garlic'),
    ('Só', 'tsp', 'salt'), ('Bors', None, 'black-pepper'), ('Fűszerpaprika', 'tsp', 'sweet-paprika'),
    ('Paprika', 'pcs', 'hungarian-pepper'), ('Paradicsom', 'pcs', 'tomato'), ('Csirke alsócomb', 'pcs', 'chicken-drumsticks'),
    ('Tejföl', 'tbsp', 'sour-cream'), ('Majoranna', 'tsp', 'marjoram'), ('Finomliszt', 'g', 'wheat-flour'),
    ('Tojás', 'pcs', 'eggs'), ('Víz', 'ml', 'water'),
    # Nosalty: aranygaluska
    ('Friss élesztő', 'g', 'fresh-yeast'), ('Vaj', 'g', 'butter'), ('Tej', 'ml', 'milk'), ('Cukor', 'tbsp', 'sugar'),
    ('Tojássárgája', 'pcs', 'eggs'), ('Vaj a forma kikenéséhez', 'tbsp', 'butter'), ('Dió darált', 'g', 'walnuts'),
    ('Vanília kikapart magja', 'pcs', 'vanilla-pod'),
    # Street Kitchen: rántott csirkemell
    ('só', None, 'salt'), ('bors', None, 'black-pepper'), ('tej', 'ml', 'milk'), ('fokhagyma', 'clove', 'garlic'),
    ('csirkemell', 'g', 'chicken-breast'), ('finomliszt', 'g', 'wheat-flour'), ('tojás', 'pcs', 'eggs'),
    ('zsemlemorzsa', 'g', 'breadcrumbs'), ('olaj a sütéshez', None, 'sunflower-oil'),
    # Mindmegette: bolognai
    ('Sárgarépa', 'stalk', 'carrot'), ('Zeller', 'stalk', 'celery'), ('Szalonna', 'g', 'smoked-bacon-slab'),
    ('Olívaolaj', 'tbsp', 'olive-oil'), ('Darált hús', 'g', 'mince-mixed'), ('vörösbor', 'ml', 'red-wine'),
]


@pytest.mark.parametrize('name,unit,want', FIXTURE_NAMES)
def test_fixture_ingredients(name, unit, want):
    assert M.match(name, unit=unit).item_id == want


@pytest.mark.parametrize('name,want', [
    ('apróra vágott vöröshagymát', 'onion'),          # descriptors + accusative
    ('csirkemellet', 'chicken-breast'),
    ('tojások', 'eggs'),
    ('liszttel', 'wheat-flour'),
    ('szecsuáni bors', 'sichuan-pepper'),            # longest key wins over "bors"
    ('őrölt szecsuani bors', 'sichuan-pepper'),
    ('darált dió', 'walnuts'),
    ('tejföl', 'sour-cream'),                         # not "tej" + suffix
    ('borsó', 'peas'),                                # not "bors" + suffix
    ('spagetti', 'wheat-pasta-long'),                 # wheat word -> hidden contains item
    ('gluténmentes spagetti', 'gf-pasta-long'),
    ('vöröshagma', 'onion'),                          # typo -> fuzzy
    ('fresh basil leaves', 'basil'),
    ('2 cans chopped tomatoes', 'canned-tomatoes'),
    ('Zeller', 'celeriac'),                           # no stalk hint -> the root
    ('paprika', 'sweet-paprika'),                     # no countable hint -> the powder
])
def test_hungarian_and_english_forms(name, want):
    assert M.match(name).item_id == want


@pytest.mark.parametrize('name', ['asdfgh', 'valami ismeretlen dolog', '', 'xyzzy plugh'])
def test_garbage_does_not_match(name):
    assert M.match(name).item_id is None


def test_how_is_reported():
    assert M.match('Vöröshagyma').how == 'exact'
    assert M.match('vöröshagymát kockázva').how in ('exact', 'stem')
    assert M.match('vöröshagma').how == 'fuzzy'


# 🚨 Celiac safety guard: the everyday words for wheat products must land on a hidden `contains` item, so a recipe
# shows the swap. If a GF tile's plain display name ("Zsemlemorzsa") ever absorbs one of these, this fails.


@pytest.mark.parametrize('word', [
    'liszt', 'finomliszt', 'búzaliszt', 'rétesliszt', 'zsemlemorzsa', 'morzsa', 'panko', 'kenyér', 'zsemle', 'kifli',
    'bagett', 'kalács', 'briós', 'toastkenyér', 'pirítós', 'tészta', 'spagetti', 'makaróni', 'penne', 'lasagne',
    'cérnametélt', 'levestészta', 'nokedli', 'galuska', 'tarhonya', 'csipetke', 'búzadara', 'gríz', 'kuszkusz',
    'bulgur', 'gersli', 'árpa', 'tönköly', 'leveles tészta', 'réteslap', 'pizzatészta', 'tortilla', 'pita',
    'szójaszósz', 'sör', 'keksz', 'babapiskóta', 'ostya', 'nápolyi', 'teriyaki', 'osztrigaszósz', 'hoisin',
    'malátaecet', 'krutonok', 'lasagne lap', 'rövid tészta', 'hosszú tészta', 'metélt tészta',
    'csuszatészta', 'kockatészta', 'fodros kockatészta', 'lebbencstészta', 'szélesmetélt', 'csigatésztát',
    'flour', 'bread', 'breadcrumbs', 'pasta', 'spaghetti', 'macaroni', 'noodles', 'couscous', 'barley', 'semolina',
    'soy sauce', 'beer', 'tortillas', 'puff pastry', 'filo', 'biscuits', 'cookies', 'ladyfingers', 'croutons', 'ramen',
    'udon', 'gnocchi', 'lasagna'])
def test_wheat_words_land_on_a_contains_item(word):
    m = M.match(word)
    assert m.item_id is not None, word
    assert M.cat.items[m.item_id].gluten == 'contains', (word, m)


# --- review I6: the CLASS guard. A gf-* item is "the GF version of a wheat product": its display name is the generic
# product name ("Soup noodles", "Zsemle, buci"), and a recipe saying it means the WHEAT product. So every plain part
# of a gf-* display name must resolve to a `contains` item — or to nothing (unknown fails safe) — never to a GF item.
import re as _re  # noqa: E402

_GF_MARK = _re.compile(r'\(?\b(gf|gm)\b\)?|glut[eé]nmentes|gluten[- ]free', _re.I)
_CAT = C.load(REAL)


def _gf_twin_name_parts():
    for y in _CAT.items.values():
        if y.id.startswith('gf-'):
            for n in (y.en, y.hu):
                for part in _re.split(r',|/|&| and | és ', _GF_MARK.sub(' ', n)):
                    if part.strip(' ()'):
                        yield y.id, part.strip(' ()')
            yield y.id, _GF_MARK.sub(' ', y.en).strip(' ()')
            yield y.id, _GF_MARK.sub(' ', y.hu).strip(' ()')


@pytest.mark.parametrize('gf_id,name', sorted(set(_gf_twin_name_parts())))
def test_plain_name_of_a_gf_version_means_the_wheat_product(gf_id, name):
    got = M.match(name, None, None).item_id
    assert got is None or _CAT.items[got].gluten == 'contains', f'{name!r} -> {got} (would earn ✓ GF)'


def test_gf_guard_bites():   # positive control: the display name that slipped through in the review
    import dataclasses
    cat = C.load(REAL)
    soup = cat.items['soup-noodles']
    cat.items['soup-noodles'] = dataclasses.replace(soup, aliases=[a for a in soup.aliases if a != 'soup noodles'])
    assert Matcher(cat).match('Soup noodles', None, None).item_id == 'gf-soup-noodles'


@pytest.mark.parametrize('word', ['seitan', 'búzasikér', 'malt extract', 'maláta', 'knäckebrot', 'rolls & buns'])
def test_more_wheat_words(word):
    got = M.match(word, None, None).item_id
    assert got and _CAT.items[got].gluten == 'contains', (word, got)


# --- Task 2 (SP3) guards the review found missing: breadth of the real catalogue, and the owner's own example
def test_catalogue_breadth():
    visible = [i for i in _CAT.items.values() if i.pantry]
    assert len(visible) >= 450
    assert len(_CAT.categories) == 18
    for c in _CAT.categories:
        assert any(g.category == c.id for g in _CAT.groups.values()), c.id


@pytest.mark.parametrize('typed', ['sechuan pepper', 'sichuan pepper', 'szecsuáni bors', 'szechuan pepper'])
def test_sechuan_pepper_is_there(typed):
    assert M.match(typed, None, None).item_id == 'sichuan-pepper'


# found unmatched in the first live imports (2026-10-10): Street Kitchen töltött paprika, Nosalty rétes/morzsasüti
@pytest.mark.parametrize('name,want', [('zellerzöld', 'celery'), ('Mandulapehely kissé összetörve', 'almonds'),
                                       ('Mandulapehely pirított', 'almonds')])
def test_live_import_gaps(name, want):
    assert M.match(name, None, None).item_id == want


# --- stage 4, compounds (live gap 2026-10-11: Street Kitchen's "25 dkg csuszatészta" stayed '?')
def test_compound_heads_are_only_gluten_containing_items():
    assert M.compound_heads, 'no compound heads at all'
    assert all(M.cat.items[item].gluten == 'contains' for _, item in M.compound_heads)


@pytest.mark.parametrize('word', ['búzakeményítő', 'búzacsíra', 'búzakeményítővel'])
def test_a_compound_never_turns_into_ok(word):
    m = M.match(word)
    assert m.item_id is None or M.cat.items[m.item_id].gluten != 'free', (word, m)


def test_gf_compounds_in_the_catalogue_still_win():
    for word in ('rizsliszt', 'mandulaliszt', 'kukoricaliszt', 'kukoricakeményítővel'):
        m = M.match(word)
        assert m.item_id is not None and M.cat.items[m.item_id].gluten == 'free', (word, m)
        assert m.how != 'compound'


def test_compound_guard_bites():   # positive control: without stage 4 the live line stays unknown
    stage = M._compound
    try:
        M._compound = lambda toks: None
        assert M.match('csuszatészta').item_id is None
    finally:
        M._compound = stage
    assert M.match('csuszatészta').how == 'compound'


# --- the gluten safety net in the stem stage (celiac hazard found 2026-10-11): a longer GF word in the same name
# ("liszt a tejföl behabarásához" -> sour cream) must never outrank a gluten-containing one
@pytest.mark.parametrize('name', ['liszt a tejföl behabarásához', 'liszt a paradicsom sűrítéséhez', 'liszt a paprika mellé',
                                  'zsemlemorzsa a padlizsán panírozásához', 'tejföl liszttel', 'paradicsom liszt'])
def test_a_gluten_word_anywhere_in_the_name_wins(name):
    m = M.match(name)
    assert m.item_id is not None and M.cat.items[m.item_id].gluten == 'contains', (name, m)


def test_safety_net_bites():   # positive control: the plain longest-key rule picked sour cream
    rank_only = M.cat.items['wheat-flour'].gluten
    try:
        M.cat.items['wheat-flour'].gluten = 'free'          # pretend flour were GF: the net no longer applies
        assert M.match('liszt a tejföl behabarásához').item_id == 'sour-cream'
    finally:
        M.cat.items['wheat-flour'].gluten = rank_only
    assert M.match('liszt a tejföl behabarásához').item_id == 'wheat-flour'
