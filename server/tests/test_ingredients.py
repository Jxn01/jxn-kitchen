import pytest

from kitchen.ingredients import format_qty, parse_line, scale

# raw line -> list of (qty, qty_max, unit, name) ; note is checked separately where it matters
CASES = [
    ('50 dkg Finomliszt', [(500, None, 'g', 'Finomliszt')]),
    ('2 dkg Friss élesztő', [(20, None, 'g', 'Friss élesztő')]),
    ('3 dl Tej', [(300, None, 'ml', 'Tej')]),
    ('1 púpozott ek Cukor', [(1, None, 'tbsp', 'Cukor')]),
    ('2 db Tojássárgája', [(2, None, 'pcs', 'Tojássárgája')]),
    ('1 ek Vaj a forma kikenéséhez', [(1, None, 'tbsp', 'Vaj')]),
    ('15 dkg Cukor ízlés szerint', [(150, None, 'g', 'Cukor')]),
    ('0 dl Napraforgó olaj', [(None, None, None, 'Napraforgó olaj')]),
    ('2 közepes db Vöröshagyma', [(2, None, 'pcs', 'Vöröshagyma')]),
    ('1 gerezd Fokhagyma', [(1, None, 'clove', 'Fokhagyma')]),
    ('1 kávéskanál Só', [(0.5, None, 'tsp', 'Só')]),
    ('0 ízlés szerint Bors', [(None, None, None, 'Bors')]),
    ('1 teáskanál Fűszerpaprika', [(1, None, 'tsp', 'Fűszerpaprika')]),
    ('6 db Csirke alsócomb', [(6, None, 'pcs', 'Csirke alsócomb')]),
    ('1 kk Majoranna', [(0.5, None, 'tsp', 'Majoranna')]),
    ('5 dl Víz', [(500, None, 'ml', 'Víz')]),
    ('só, bors', [(None, None, None, 'só'), (None, None, None, 'bors')]),
    ('só, bors ízlés szerint', [(None, None, None, 'só'), (None, None, None, 'bors')]),
    ('500 ml tej', [(500, None, 'ml', 'tej')]),
    ('400 g csirkemell', [(400, None, 'g', 'csirkemell')]),
    ('bő olaj a sütéshez', [(None, None, None, 'olaj')]),
    ('1 szál Sárgarépa', [(1, None, 'stalk', 'Sárgarépa')]),
    ('1 fej Vöröshagyma', [(1, None, 'head', 'Vöröshagyma')]),
    ('7.5 dkg Szalonna', [(75, None, 'g', 'Szalonna')]),
    ('7,5 dkg Szalonna', [(75, None, 'g', 'Szalonna')]),
    ('2-3 gerezd fokhagyma', [(2, 3, 'clove', 'fokhagyma')]),
    ('2–3 ek olívaolaj', [(2, 3, 'tbsp', 'olívaolaj')]),
    ('½ csokor petrezselyem', [(0.5, None, 'bunch', 'petrezselyem')]),
    ('1 1/2 cup flour', [(1.5, None, 'cup', 'flour')]),
    ('1½ tsp salt', [(1.5, None, 'tsp', 'salt')]),
    ('fél kg darált hús', [(500, None, 'g', 'darált hús')]),
    ('másfél bögre rizs', [(1.5, None, 'cup', 'rizs')]),
    ('két fej hagyma', [(2, None, 'head', 'hagyma')]),
    ('egy csipet szerecsendió', [(1, None, 'pinch', 'szerecsendió')]),
    ('2 tablespoons olive oil', [(2, None, 'tbsp', 'olive oil')]),
    ('3 cloves garlic, minced', [(3, None, 'clove', 'garlic')]),
    ('1 (400 g) can chopped tomatoes', [(1, None, 'can', 'chopped tomatoes')]),
    ('2 eggs', [(2, None, None, 'eggs')]),
    ('salt and pepper to taste', [(None, None, None, 'salt'), (None, None, None, 'pepper')]),
    ('1 csomag sütőpor', [(1, None, 'pack', 'sütőpor')]),
    ('1 doboz hámozott paradicsom', [(1, None, 'can', 'hámozott paradicsom')]),
    ('4 db Tojás (M-es)', [(4, None, 'pcs', 'Tojás')]),
    ('1 db Vanília kikapart magja', [(1, None, 'pcs', 'Vanília kikapart magja')]),
    ('30 dkg Dió darált', [(300, None, 'g', 'Dió darált')]),
    ('1 marék dió', [(1, None, 'handful', 'dió')]),
]


@pytest.mark.parametrize('raw,want', CASES)
def test_parse(raw, want):
    got = [(p.qty, p.qty_max, p.unit, p.name) for p in parse_line(raw)]
    assert got == want


def test_notes_are_kept():
    assert parse_line('15 dkg Cukor ízlés szerint')[0].note == 'ízlés szerint'
    assert parse_line('3 cloves garlic, minced')[0].note == 'minced'
    assert parse_line('2 közepes db Vöröshagyma')[0].note == 'közepes'
    assert parse_line('4 db Tojás (M-es)')[0].note == 'M-es'
    assert all(p.raw == 'só, bors' for p in parse_line('só, bors'))


def test_blank_and_header_lines():
    assert parse_line('') == []
    assert parse_line('   ') == []
    assert [p.name for p in parse_line('A tésztához:')] == []          # a section header, not an ingredient


def test_format_and_scale():
    assert format_qty(500, 'g', 'hu') == '500 g'
    assert format_qty(1500, 'g', 'hu') == '1,5 kg' and format_qty(1500, 'g', 'en') == '1.5 kg'
    assert format_qty(0.5, 'tsp', 'hu') == '½ tk' and format_qty(0.5, 'tsp', 'en') == '½ tsp'
    assert format_qty(1.5, 'cup', 'en') == '1½ cups'
    assert format_qty(2, 'pcs', 'hu') == '2 db'
    assert format_qty(None, None, 'hu') == ''
    assert format_qty(2, None, 'en') == '2'
    p = scale(parse_line('2-3 gerezd fokhagyma')[0], 2)
    assert (p.qty, p.qty_max) == (4, 6)
    assert format_qty(1250, 'ml', 'hu') == '1,25 l'
    assert format_qty(0.33333, 'cup', 'en') == '⅓ cup'


# --- what an ingredient is FOR goes to the note (gluten hazard: "liszt a tejföl behabarásához" matched
# sour cream because "a tejföl …" stayed in the name)
@pytest.mark.parametrize('raw,name,note', [
    ('1 ek liszt a tejföl behabarásához', 'liszt', 'a tejföl behabarásához'),
    ('2 ek porcukor a tészta szórásához', 'porcukor', 'a tészta szórásához'),
    ('1 ek Vaj a forma kikenéséhez', 'Vaj', 'a forma kikenéséhez'),
    ('2 ek liszt a paprika mellé', 'liszt', 'a paprika mellé'),
    ('1 ek liszt habaráshoz', 'liszt', 'habaráshoz'),
    ('olaj a sütéshez', 'olaj', 'a sütéshez'),
    ('flour for dusting', 'flour', 'for dusting'),
])
def test_purpose_phrases_go_to_the_note(raw, name, note):
    [p] = parse_line(raw)
    assert (p.name, p.note) == (name, note)


@pytest.mark.parametrize('raw,name', [('juice of a lemon', 'juice of a lemon'), ('20 dkg darált dió', 'darált dió'),
                                      ('1 csomag gluténmentes liszt', 'gluténmentes liszt'), ('2 db tojás', 'tojás')])
def test_ordinary_names_keep_every_word(raw, name):
    [p] = parse_line(raw)
    assert p.name == name
