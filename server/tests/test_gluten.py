import pathlib

from kitchen import catalogue as C
from kitchen import gluten
from kitchen.gluten import check_line, gf_name, verdict
from kitchen.ingredients import parse_line

CAT = C.load(pathlib.Path(__file__).resolve().parents[2] / 'catalogue')
EMPTY = {'have': [], 'groups_some': [], 'staples_off': []}


def test_free_item_is_ok():
    assert check_line(CAT, EMPTY, 'onion', False).status == 'ok'


def test_contains_item_swaps_to_its_gf_item_with_a_tip():
    g = check_line(CAT, EMPTY, 'nokedli', False)
    assert g.status == 'swap' and g.swap_id == 'gf-flour-mix'
    assert g.tip_en and g.tip_hu                      # method tweak for GF nokedli
    assert check_line(CAT, EMPTY, 'soy-sauce', False).swap_id == 'tamari'


def test_label_item_in_the_pantry_is_yours_otherwise_check():
    assert check_line(CAT, EMPTY, 'stock-cube', False).status == 'check'
    st = {'have': ['stock-cube'], 'groups_some': [], 'staples_off': []}
    assert check_line(CAT, st, 'stock-cube', False).status == 'yours'


def test_unmatched_is_unknown_unless_marked_ok_by_hand():
    assert check_line(CAT, EMPTY, None, False).status == 'unknown'
    assert check_line(CAT, EMPTY, None, True).status == 'ok'


def test_verdict_priority_unknown_beats_everything():
    v = verdict(['ok', 'ok', 'unknown'])
    assert v == {'state': 'unknown', 'swaps': 0, 'check': 0, 'unknown': 1}
    assert verdict(['ok', 'swap', 'check'])['state'] == 'swaps'
    assert verdict(['ok', 'check', 'yours'])['state'] == 'check'
    assert verdict(['ok', 'yours'])['state'] == 'gf'
    assert verdict([])['state'] == 'empty'          # no lines = nothing checked, never ✓ GF
    assert verdict(iter([]))['state'] == 'empty'


def test_one_unknown_line_blocks_gf_even_if_everything_else_is_free():
    statuses = [check_line(CAT, EMPTY, i, False).status for i in ['onion', 'garlic', 'salt', None]]
    assert verdict(statuses)['state'] != 'gf'


def test_gf_name_is_the_swap_items_name_in_the_language():
    assert gf_name(CAT, 'wheat-flour', 'hu') == 'GM lisztkeverék'
    assert gf_name(CAT, 'wheat-flour', 'en') == 'GF flour mix'
    assert gf_name(CAT, 'onion', 'hu') is None          # not a swap


def test_every_contains_item_has_a_bilingual_tip():
    for it in CAT.items.values():
        assert bool(it.tip_en) == bool(it.tip_hu), it.id
        if it.gluten == 'contains':
            assert it.tip_en and it.tip_hu, f'{it.id}: a swap needs its method tip in both languages'


def test_may_contain_is_never_a_gluten_state():
    assert {it.gluten for it in CAT.items.values()} <= {'free', 'contains', 'label'}


def test_every_gf_swap_text_is_visibly_gf():
    """The GF version of a recipe must SAY GF on every swapped line ("400 g GM Hosszú tészta", never a plain
    "Hosszú tészta" that reads as the wheat pasta) — checked over the whole real catalogue."""
    import pathlib
    from kitchen import catalogue as C
    real = C.load(pathlib.Path(__file__).resolve().parents[2] / 'catalogue')
    for it in real.items.values():
        if it.gluten == 'contains':
            for lang in ('en', 'hu'):
                name = gluten.gf_name(real, it.id, lang)
                assert gluten._MARKED.search(name), (it.id, lang, name)
    assert gluten.gf_name(real, 'wheat-pasta-long', 'hu') == 'GM Hosszú tészta'
    assert gluten.gf_name(real, 'wheat-flour', 'hu') == 'GM lisztkeverék'          # never "GM GM …"
