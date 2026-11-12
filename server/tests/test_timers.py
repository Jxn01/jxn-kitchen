import pytest

from kitchen.timers import detect


@pytest.mark.parametrize('text,want', [
    ('Fedő alatt, alacsony lángon kb. 1 órát főzzük.', [3600]),
    ('25 percig sütjük 180 fokon.', [1500]),
    ('10-15 percig pirítjuk, majd 5 perc pihentetés.', [900, 300]),
    ('Másfél óra alatt puhára pároljuk.', [5400]),
    ('fél óráig kelesztjük', [1800]),
    ('negyed óra múlva megkeverjük', [900]),
    ('1,5 óra', [5400]),
    ('Bake for 25 minutes, then rest 10 mins.', [1500, 600]),
    ('Simmer for 1 hour 30 minutes.', [5400]),
    ('Cook 2–3 minutes per side', [180]),
    ('30 másodpercig keverjük', [30]),
    ('Sózzuk, borsozzuk.', []),
    ('Melegítsünk 2 ek olajat.', []),
])
def test_detect(text, want):
    assert [t.seconds for t in detect(text)] == want


def test_spans_point_at_the_words():
    t = detect('25 percig sütjük')[0]
    assert '25 percig sütjük'[t.start:t.end] == '25 percig'


def test_hostile_input_is_fast():
    import time
    for bad in ['1' * 100000 + ' x', '1 - ' * 30000, ('1,' * 20000) + 'perc', ' ' * 100000 + '5 perc']:
        t0 = time.perf_counter()
        detect(bad)
        assert time.perf_counter() - t0 < 0.5
