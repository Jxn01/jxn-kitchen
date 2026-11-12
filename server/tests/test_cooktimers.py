"""Kitchen timers (spec §6.5): server state every screen shares; when one ends HA notifies the phone, once."""
import pathlib
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from fake_ha import FakeHA
from kitchen.app import create_app
from kitchen.config import Config

FIX = pathlib.Path(__file__).parent / 'fixtures' / 'catalogue'
T0 = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t

    def tick(self, **kw):
        self.t += timedelta(**kw)


def make(tmp_path, ha, clock):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url='http://ha.test' if ha else None,
                 ha_token='t' if ha else None, catalogue_dir=FIX, spices=False)
    return TestClient(create_app(cfg, http=ha.client() if ha else None, now=clock, shopping_sync_every=None,
                                 timers_autorun=False))


def fire(c):
    c.portal.call(c.app.state.timers.fire_due)


def test_create_list_and_count_down(tmp_path):
    clock = Clock()
    with make(tmp_path, None, clock) as c:
        t = c.post('/api/timers', json={'label': 'Tészta', 'seconds': 600}).json()
        assert t['state'] == 'running' and t['remaining'] == 600
        clock.tick(seconds=90)
        assert c.get('/api/timers').json()[0]['remaining'] == 510
        assert c.post('/api/timers', json={'label': 'x', 'seconds': 0}).status_code == 422
        assert c.post('/api/timers', json={'label': 'x' * 61, 'seconds': 5}).status_code == 422
        # security review: a newline in a label could forge log lines (and lands in the phone notification)
        assert c.post('/api/timers', json={'label': 'ok\nFAKE LOG LINE', 'seconds': 5}).status_code == 422


def test_end_marks_done_rings_and_notifies_the_phone_once(tmp_path):
    clock, ha = Clock(), FakeHA()
    with make(tmp_path, ha, clock) as c:
        c.put('/api/settings', json={'language': 'hu'})
        q = c.app.state.events.subscribe()
        c.post('/api/timers', json={'label': 'Tészta', 'seconds': 60})
        clock.tick(seconds=59); fire(c)
        assert ha.notified == []
        clock.tick(seconds=2); fire(c); fire(c)
        assert c.get('/api/timers').json()[0]['state'] == 'done'
        assert len(ha.notified) == 1
        n = ha.notified[0]
        assert n['priority'] == 'urgent' and n['group'] == 'kitchen-timer' and 'Tészta' in n['message']
        events = []
        while not q.empty():
            events.append(q.get_nowait()[0])
        assert 'timers' in events


def test_pause_never_fires_resume_continues_add_extends(tmp_path):
    clock, ha = Clock(), FakeHA()
    with make(tmp_path, ha, clock) as c:
        t = c.post('/api/timers', json={'label': 'Rizs', 'seconds': 100}).json()
        clock.tick(seconds=40)
        assert c.patch(f"/api/timers/{t['id']}", json={'action': 'pause'}).json()['remaining'] == 60
        clock.tick(seconds=500); fire(c)
        assert ha.notified == [] and c.get('/api/timers').json()[0]['state'] == 'paused'
        assert c.patch(f"/api/timers/{t['id']}", json={'action': 'resume'}).json()['remaining'] == 60
        assert c.patch(f"/api/timers/{t['id']}", json={'action': 'add', 'seconds': 60}).json()['remaining'] == 120
        clock.tick(seconds=121); fire(c)
        assert len(ha.notified) == 1


def test_dismiss_hides_it_and_a_done_timer_can_get_more_time(tmp_path):
    clock = Clock()
    with make(tmp_path, None, clock) as c:
        a = c.post('/api/timers', json={'label': 'A', 'seconds': 5}).json()
        clock.tick(seconds=6); fire(c)
        assert c.patch(f"/api/timers/{a['id']}", json={'action': 'add', 'seconds': 60}).json()['state'] == 'running'
        clock.tick(seconds=61); fire(c)
        c.patch(f"/api/timers/{a['id']}", json={'action': 'dismiss'})
        assert c.get('/api/timers').json() == []
        assert c.delete(f"/api/timers/{a['id']}").status_code == 204
        assert c.patch('/api/timers/999', json={'action': 'pause'}).status_code == 404


def test_ha_down_still_rings_without_crashing(tmp_path):
    clock, ha = Clock(), FakeHA()
    ha.down = True
    with make(tmp_path, ha, clock) as c:
        c.post('/api/timers', json={'label': 'Leves', 'seconds': 5})
        clock.tick(seconds=6); fire(c); fire(c)
        assert c.get('/api/timers').json()[0]['state'] == 'done'


def test_after_a_restart_overdue_timers_end_and_long_overdue_ones_stay_quiet(tmp_path):
    clock, ha = Clock(), FakeHA()
    with make(tmp_path, ha, clock) as c:
        c.post('/api/timers', json={'label': 'recent', 'seconds': 60})
        c.post('/api/timers', json={'label': 'ancient', 'seconds': 10})
    clock.tick(minutes=5)                            # down for 5 min: 'ancient' ended 4m50 ago, 'recent' 4 min ago
    with make(tmp_path, ha, clock) as c:
        fire(c)
        assert {t['label']: t['state'] for t in c.get('/api/timers').json()} == {'recent': 'done', 'ancient': 'done'}
        assert len(ha.notified) == 1                  # both < 10 min late: still worth a ping — one, for both
        assert 'recent' in ha.notified[0]['message'] and 'ancient' in ha.notified[0]['message']
    clock.tick(hours=2)
    with make(tmp_path, ha, clock) as c:
        c.post('/api/timers', json={'label': 'missed', 'seconds': 1})
    clock.tick(hours=1)                               # ended an hour ago while the server was down
    with make(tmp_path, ha, clock) as c:
        fire(c)
        assert len(ha.notified) == 1                  # no stale ping an hour late; the kiosk card still shows it


def test_the_scheduler_wakes_by_itself_when_a_timer_ends(tmp_path):
    import time
    ha = FakeHA()
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url='http://ha.test', ha_token='t', catalogue_dir=FIX, spices=False)
    with TestClient(create_app(cfg, http=ha.client(), shopping_sync_every=None)) as c:     # real clock, real loop
        c.post('/api/timers', json={'label': 'long', 'seconds': 3600})                      # the loop sleeps on this…
        c.post('/api/timers', json={'label': 'short', 'seconds': 1})                        # …and must wake for this
        deadline = time.time() + 5
        while time.time() < deadline and not ha.notified:
            time.sleep(0.1)
        assert [n['message'] for n in ha.notified] == ["Time's up: short"]


def test_timers_ending_together_make_one_notification(tmp_path):
    clock, ha = Clock(), FakeHA()
    with make(tmp_path, ha, clock) as c:
        for label in ('Tészta', 'Szósz', 'Sütő'):
            c.post('/api/timers', json={'label': label, 'seconds': 30})
        clock.tick(seconds=31); fire(c)
        assert len(ha.notified) == 1
        assert all(x in ha.notified[0]['message'] for x in ('Tészta', 'Szósz', 'Sütő'))


def test_phone_pings_are_capped_so_nobody_can_spam_the_phone(tmp_path):
    """Security review: no logins (LAN/tailnet by design), so a guest on the Wi-Fi could fire urgent notifications at
    the owner's phone with short timers. At most 6 pings per 10 minutes; past that the kiosk still rings."""
    clock, ha = Clock(), FakeHA()
    with make(tmp_path, ha, clock) as c:
        for i in range(10):
            c.post('/api/timers', json={'label': f'spam {i}', 'seconds': 1})
            clock.tick(seconds=2); fire(c)
        assert len(ha.notified) == 6
        assert sum(t['state'] == 'done' for t in c.get('/api/timers').json()) == 10   # all of them still ring
        clock.tick(minutes=11)
        c.post('/api/timers', json={'label': 'real', 'seconds': 1})
        clock.tick(seconds=2); fire(c)
        assert len(ha.notified) == 7 and 'real' in ha.notified[-1]['message']
