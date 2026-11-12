import copy
import pathlib

import pytest

from kitchen import catalogue as C

FIX = pathlib.Path(__file__).parent / 'fixtures' / 'catalogue'
REAL = pathlib.Path(__file__).resolve().parents[2] / 'catalogue'
ICONS = {'om-1f969', 'om-1f35d', 'om-1f9fb', 'om-1f414', 'om-1f32d', 'om-1f35a'}


def test_fold():
    assert C.fold('Szecsuáni BORS ') == 'szecsuani bors'
    assert C.fold('  Tejföl  ') == 'tejfol'
    assert C.fold('Őrölt   fahéj') == 'orolt fahej'


def test_fixture_loads_and_validates():
    cat = C.load(FIX)
    assert [c.id for c in cat.categories] == ['meat', 'grains', 'kitchen-supplies']
    assert cat.items['chicken-breast'].group == 'chicken' and cat.items['chicken-breast'].category == 'meat'
    assert cat.items['wheat-pasta'].pantry is False and cat.items['rice-white'].staple is True
    assert cat.items['alu-foil'].kind == 'supply'
    assert C.validate(cat, icon_ids=ICONS) == []


def mutate(fn):
    cat = C.load(FIX)
    cat = copy.deepcopy(cat)
    fn(cat)
    return C.validate(cat, icon_ids=ICONS)


@pytest.mark.parametrize('fn,needle', [
    (lambda c: setattr(c.items['chicken-wings'], 'id', 'chicken-breast'), 'duplicate id'),
    (lambda c: setattr(c.items['chicken-wings'], 'hu', ''), 'missing hu'),
    (lambda c: setattr(c.items['chicken-wings'], 'gluten', 'maybe'), 'bad gluten'),
    (lambda c: setattr(c.items['wheat-pasta'], 'swap', 'nope'), 'swap'),
    (lambda c: setattr(c.items['wheat-pasta'], 'swap', 'smoked-sausage'), 'swap'),
    (lambda c: setattr(c.items['wheat-pasta'], 'swap', None), 'swap'),
    (lambda c: c.items['chicken-wings'].aliases.append('Chicken Breast'), 'alias'),
    (lambda c: setattr(c.groups['chicken'], 'icon', 'om:FFFF'), 'icon'),
    (lambda c: setattr(c.items['alu-foil'], 'gluten', 'label'), 'supply'),
])
def test_each_rule_bites(fn, needle):
    errors = mutate(fn)
    assert errors and any(needle in e for e in errors), errors


def test_comma_in_an_unquoted_flow_value_is_caught(tmp_path):
    import shutil
    shutil.copytree(FIX, tmp_path / 'c')
    f = tmp_path / 'c' / 'food' / 'meat.yaml'
    f.write_text(f.read_text().replace('hu: Csirkeszárny,', 'hu: Csirke, szárny,'))
    errors = C.validate(C.load(tmp_path / 'c'), icon_ids=ICONS)
    assert any("unknown key" in e and 'szárny' in e for e in errors), errors


def test_a_gf_tile_name_may_equal_its_wheat_twins_alias_but_nothing_else():
    cat = C.load(FIX)
    cat.items['gf-pasta-long'].en = 'Pasta'          # == wheat-pasta's alias, and wheat-pasta swaps to it: fine
    assert C.validate(cat, icon_ids=ICONS) == []
    assert C.match_index(cat)['pasta'] == 'wheat-pasta'   # the alias wins: recipes see the swap
    cat.items['alu-foil'].en = 'Pasta'               # same key, not a swap pair: error
    assert any('Pasta'.lower() in e for e in C.validate(cat, icon_ids=ICONS))


def test_icon_ids():
    assert C.icon_id('om:1F969') == 'om-1f969'
    assert C.icon_id('c:chicken-wing') == 'c-chicken-wing'
    assert C.icon_id('recipes') == 'recipes'


def test_real_catalogue_is_valid():
    if not (REAL / 'categories.yaml').exists():
        pytest.fail('catalogue/ missing')
    cat = C.load(REAL)
    sprite = (REAL.parent / 'web' / 'public' / 'sprite.svg').read_text()
    import re
    ids = set(re.findall(r'<symbol id="i-([^"]+)"', sprite))
    assert C.validate(cat, icon_ids=ids) == []


def test_fold_matches_the_shared_table_used_by_the_web_app():
    import json
    cases = json.loads((pathlib.Path(__file__).resolve().parents[2] / 'web/tests/fixtures/fold_cases.json').read_text())
    for raw, want in cases:
        assert C.fold(raw) == want, raw
