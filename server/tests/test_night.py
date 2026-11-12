from datetime import time

from kitchen.night import is_night


def test_wraps_midnight():
    assert is_night(time(23, 0), 23, 6)
    assert is_night(time(2, 30), 23, 6)
    assert is_night(time(5, 59), 23, 6)
    assert not is_night(time(6, 0), 23, 6)
    assert not is_night(time(12, 0), 23, 6)
    assert not is_night(time(22, 59), 23, 6)


def test_same_day_window():
    assert is_night(time(1, 0), 0, 6)
    assert not is_night(time(7, 0), 0, 6)


def test_equal_means_never():
    assert not any(is_night(time(h, 0), 5, 5) for h in range(24))
