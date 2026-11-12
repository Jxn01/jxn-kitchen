from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from kitchen.app import create_app
from kitchen.config import Config


class Clock:
    def __init__(self, t): self.t = t
    def __call__(self): return self.t


def make(tmp_path, t):
    clock = Clock(t)
    return TestClient(create_app(Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None), now=clock)), clock


def test_health_follows_heartbeat(tmp_path):
    c, clock = make(tmp_path, datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc))
    with c:
        assert c.get('/api/kiosk/health').status_code == 503
        assert c.post('/api/kiosk/heartbeat', json={'agent': '0.1.0', 'chrome_ok': True, 'free_mb': 900}).status_code == 204
        r = c.get('/api/kiosk/health')
        assert r.status_code == 200 and r.json()['age_s'] == 0 and r.json()['free_mb'] == 900
        clock.t += timedelta(seconds=181)
        assert c.get('/api/kiosk/health').status_code == 503


def test_heartbeat_rejects_garbage(tmp_path):
    c, _ = make(tmp_path, datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc))
    with c:
        assert c.post('/api/kiosk/heartbeat', json={'agent': 1}).status_code == 422


def test_display_follows_night_window_in_budapest(tmp_path):
    # 21:30 UTC = 23:30 CEST (night); 10:00 UTC = 12:00 CEST (day)
    c, clock = make(tmp_path, datetime(2026, 10, 10, 21, 30, tzinfo=timezone.utc))
    with c:
        assert c.get('/api/kiosk/display').json() == {'night': True, 'brightness': 20}
        clock.t = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
        assert c.get('/api/kiosk/display').json() == {'night': False, 'brightness': 80}
        c.put('/api/settings', json={'day_brightness': 55})
        assert c.get('/api/kiosk/display').json()['brightness'] == 55


def test_display_across_dst_change(tmp_path):
    # 2026-10-25 04:30 UTC = 05:30 CET (after the 03:00→02:00 change): still night (ends 06:00)
    c, _ = make(tmp_path, datetime(2026, 10, 25, 4, 30, tzinfo=timezone.utc))
    with c:
        assert c.get('/api/kiosk/display').json()['night'] is True


def test_heartbeat_carries_overlay_ok_and_older_agents_still_fit(tmp_path):
    from fastapi.testclient import TestClient
    from kitchen.app import create_app
    from kitchen.config import Config
    import pathlib
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None,
                 catalogue_dir=pathlib.Path(__file__).parent / 'fixtures' / 'catalogue', spices=False)
    with TestClient(create_app(cfg, shopping_sync_every=None)) as c:
        assert c.post('/api/kiosk/heartbeat', json={'agent': 'old', 'chrome_ok': True, 'free_mb': 900}).status_code == 204
        assert c.get('/api/kiosk/health').json()['overlay_ok'] is None
        c.post('/api/kiosk/heartbeat', json={'agent': 'new', 'chrome_ok': True, 'free_mb': 900, 'overlay_ok': True})
        assert c.get('/api/kiosk/health').json()['overlay_ok'] is True


def test_fonts_and_overlay_are_shared_cross_origin_and_nothing_else(tmp_path):
    from fastapi.testclient import TestClient
    from kitchen.app import create_app
    from kitchen.config import Config
    import pathlib
    static = tmp_path / 'static'
    (static / 'fonts').mkdir(parents=True)
    (static / 'fonts' / 'a.woff2').write_bytes(b'x')
    (static / 'overlay.js').write_text('1')
    (static / 'index.html').write_text('<html></html>')
    cfg = Config(data_dir=tmp_path, static_dir=static, ha_url=None, ha_token=None,
                 catalogue_dir=pathlib.Path(__file__).parent / 'fixtures' / 'catalogue', spices=False)
    with TestClient(create_app(cfg, shopping_sync_every=None)) as c:
        assert c.get('/fonts/a.woff2').headers.get('access-control-allow-origin') == '*'
        assert c.get('/overlay.js').headers.get('access-control-allow-origin') == '*'
        assert 'access-control-allow-origin' not in c.get('/api/settings').headers
        assert 'access-control-allow-origin' not in c.get('/').headers
