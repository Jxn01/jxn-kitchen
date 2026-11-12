import pathlib

from fastapi.testclient import TestClient

from kitchen.app import create_app
from kitchen.config import Config
from fake_ha import FakeHA

FIX = pathlib.Path(__file__).parent / 'fixtures' / 'catalogue'


def make(tmp_path, ha: FakeHA | None):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url='http://ha.test' if ha else None,
                 ha_token='t' if ha else None, catalogue_dir=FIX, spices=False)
    app = create_app(cfg, http=ha.client() if ha else None, shopping_sync_every=None)   # rounds driven by the test
    return TestClient(app)


def sync(c):
    c.portal.call(c.app.state.shopping_sync.round)


def texts(c):
    return sorted(i['text'] for i in c.get('/api/shopping').json() if not i['done'])


def test_add_here_appears_in_ha_once(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        c.post('/api/shopping', json={'text': 'Tejföl'})
        sync(c); sync(c)
        assert [i['summary'] for i in ha.items] == ['Tejföl']
        assert c.get('/api/shopping').json()[0]['ha_linked'] is True


def test_dedupe_on_post(tmp_path):
    with make(tmp_path, None) as c:
        a = c.post('/api/shopping', json={'text': 'tejföl'}).json()
        b = c.post('/api/shopping', json={'text': 'Tejföl '}).json()
        assert a['id'] == b['id'] and len(c.get('/api/shopping').json()) == 1


def test_item_id_text_follows_language_and_gf_prefix(tmp_path):
    with make(tmp_path, None) as c:
        assert c.post('/api/shopping', json={'item_id': 'chicken-wings'}).json()['text'] == 'Wings'
        c.put('/api/settings', json={'language': 'hu'})
        assert c.post('/api/shopping', json={'item_id': 'smoked-sausage'}).json()['text'] == 'GM Füstölt kolbász'
        # a wheat word lands on the list as its GF swap, MARKED: a plain "Hosszú tészta" on a shared list buys wheat
        r = c.post('/api/shopping', json={'item_id': 'wheat-pasta'}).json()
        assert r['text'] == 'GM Hosszú tészta' and r['item_id'] == 'gf-pasta-long'   # never the hidden wheat id
        assert c.post('/api/shopping', json={'item_id': 'nope'}).status_code == 404
        assert c.post('/api/shopping', json={}).status_code == 422


def test_add_in_ha_appears_here(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        ha.phone_add('Kenyér')
        sync(c)
        assert texts(c) == ['Kenyér']


def test_rename_and_complete_in_ha_flow_back(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        c.post('/api/shopping', json={'text': 'Tej'})
        sync(c)
        ha.by_summary('Tej')['summary'] = 'Laktózmentes tej'
        sync(c)
        assert texts(c) == ['Laktózmentes tej']
        ha.by_summary('Laktózmentes tej')['status'] = 'completed'
        sync(c)
        assert c.get('/api/shopping').json() == []          # ticked off in HA -> gone here


def test_tick_and_delete_here_flow_to_ha(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        a = c.post('/api/shopping', json={'text': 'Alufólia'}).json()
        b = c.post('/api/shopping', json={'text': 'Szivacs'}).json()
        sync(c)
        c.patch(f"/api/shopping/{a['id']}", json={'done': True})
        c.delete(f"/api/shopping/{b['id']}")
        sync(c)
        assert ha.by_summary('Alufólia')['status'] == 'completed'
        assert [i['summary'] for i in ha.items] == ['Alufólia']
        c.post('/api/shopping/clear-done')
        sync(c)
        assert ha.items == [] and c.get('/api/shopping').json() == []


def test_removed_in_ha_is_removed_here(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        c.post('/api/shopping', json={'text': 'Mák'})
        sync(c)
        ha.items.clear()
        sync(c)
        assert c.get('/api/shopping').json() == []


def test_ha_down_two_rounds_then_ok_no_duplicates(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        c.post('/api/shopping', json={'text': 'Rizs'})
        ha.down = True
        sync(c); sync(c)
        assert texts(c) == ['Rizs']                         # still works locally
        ha.down = False
        sync(c); sync(c); sync(c)
        assert [i['summary'] for i in ha.items] == ['Rizs']


def test_works_without_ha_at_all(tmp_path):
    with make(tmp_path, None) as c:
        i = c.post('/api/shopping', json={'text': 'Só'}).json()
        sync(c)
        assert c.patch(f"/api/shopping/{i['id']}", json={'done': True}).json()['done'] is True


def test_ensure_shopping_list_creates_the_integration_once(tmp_path):
    ha = FakeHA(has_list=False)
    with make(tmp_path, ha) as c:
        assert c.portal.call(c.app.state.ha.ensure_shopping_list) is True
        assert ha.flows == 1 and ha.has_list
        assert c.portal.call(c.app.state.ha.ensure_shopping_list) is True
        assert ha.flows == 1                                 # no-op when it exists


def test_every_change_is_an_sse_event(tmp_path):
    with make(tmp_path, None) as c:
        q = c.app.state.events.subscribe()
        i = c.post('/api/shopping', json={'text': 'Bors'}).json()
        c.patch(f"/api/shopping/{i['id']}", json={'text': 'Fekete bors'})
        c.delete(f"/api/shopping/{i['id']}")
        assert [q.get_nowait()[0] for _ in range(3)] == ['shopping'] * 3


# --- writes landing while the sync awaits HA ---------------------------------------------------------

import httpx  # noqa: E402

from kitchen import shopping as shop  # noqa: E402


def rows(c):
    async def read():                                   # on the app's loop thread: the connection is single-thread
        return [dict(r) for r in c.app.state.db.execute('SELECT * FROM shopping_item ORDER BY id')]
    return c.portal.call(read)


def hook_ha(ha, path, action, *, lose=False):
    """Run `action()` (a user write) while the sync awaits HA's answer to `path`; optionally lose that answer."""
    orig, armed = ha.handler, {'on': True}
    def handler(req):
        res = orig(req)
        if req.url.path == path and armed['on']:
            armed['on'] = False
            action()
            if lose:
                raise httpx.ReadTimeout('lost', request=req)
        return res
    ha.handler = handler


def test_lost_add_response_never_duplicates(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        hook_ha(ha, '/api/services/todo/add_item', lambda: None, lose=True)
        c.post('/api/shopping', json={'text': 'Rizs'})
        sync(c); sync(c); sync(c)
        assert [i['summary'] for i in ha.items] == ['Rizs']
        assert texts(c) == ['Rizs'] and all(r['pending'] is None and r['ha_uid'] for r in rows(c))


def test_delete_during_add_stays_deleted(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        it = c.post('/api/shopping', json={'text': 'Tej'}).json()
        hook_ha(ha, '/api/services/todo/add_item',
                lambda: shop.delete(c.app.state.db, it['id'], c.app.state.shopping_sync.now()))
        sync(c); sync(c); sync(c)
        assert ha.items == [] and texts(c) == [] and rows(c) == []


def test_rename_during_add_reaches_ha_once(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        it = c.post('/api/shopping', json={'text': 'Tej'}).json()
        hook_ha(ha, '/api/services/todo/add_item',
                lambda: shop.update(c.app.state.db, it['id'], c.app.state.shopping_sync.now(), text='Laktózmentes tej'))
        sync(c); sync(c); sync(c)
        assert [i['summary'] for i in ha.items] == ['Laktózmentes tej']
        assert texts(c) == ['Laktózmentes tej'] and len(rows(c)) == 1 and rows(c)[0]['ha_uid']


def test_untick_during_update_wins(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        it = c.post('/api/shopping', json={'text': 'Tej'}).json()
        sync(c)
        c.patch(f"/api/shopping/{it['id']}", json={'done': True})
        hook_ha(ha, '/api/services/todo/update_item',
                lambda: shop.update(c.app.state.db, it['id'], c.app.state.shopping_sync.now(), done=False))
        sync(c); sync(c); sync(c)
        assert [(i['summary'], i['status']) for i in ha.items] == [('Tej', 'needs_action')]
        assert texts(c) == ['Tej']


def test_delete_after_a_lost_add_is_not_resurrected(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        hook_ha(ha, '/api/services/todo/add_item', lambda: None, lose=True)
        it = c.post('/api/shopping', json={'text': 'Só'}).json()
        sync(c)                                        # HA has "Só", we never heard back
        c.delete(f"/api/shopping/{it['id']}")
        sync(c); sync(c)
        assert ha.items == [] and rows(c) == []


def test_two_rounds_at_once_add_once(tmp_path):
    import asyncio
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        c.post('/api/shopping', json={'text': 'Só'})
        async def both():
            s = c.app.state.shopping_sync
            await asyncio.gather(s.round(), s.round())
        c.portal.call(both)
        assert [i['summary'] for i in ha.items] == ['Só']


def test_ticked_in_ha_disappears_here_and_comes_back_if_unticked(tmp_path):
    ha = FakeHA()
    with make(tmp_path, ha) as c:
        c.post('/api/shopping', json={'text': 'Tej'})
        sync(c)
        ha.by_summary('Tej')['status'] = 'completed'
        sync(c)
        assert c.get('/api/shopping').json() == []          # ticked off in HA -> gone here
        ha.by_summary('Tej')['status'] = 'needs_action'
        sync(c)
        assert texts(c) == ['Tej']


def test_free_text_gluten_words_get_the_marker_and_item(tmp_path):
    with make(tmp_path, None) as c:
        c.put('/api/settings', json={'language': 'hu'})
        r = c.post('/api/shopping', json={'text': 'spagetti'}).json()
        assert r['text'] == 'GM spagetti' and r['item_id'] == 'gf-pasta-long'
        r = c.post('/api/shopping', json={'text': 'tészta'}).json()           # the wheat word -> its GF twin
        assert r['item_id'] == 'gf-pasta-long'                                  # (deduped onto the same row)
        r = c.post('/api/shopping', json={'text': 'GM kolbász'}).json()
        assert r['text'] == 'GM kolbász'                                         # never "GM GM …"
        assert c.post('/api/shopping', json={'text': '   '}).status_code == 422
        r = c.post('/api/shopping', json={'text': 'Fehér rizs'}).json()
        assert r['text'] == 'Fehér rizs' and r['item_id'] == 'rice-white'       # gluten-free: typed text kept


def test_empty_rename_is_refused(tmp_path):
    with make(tmp_path, None) as c:
        it = c.post('/api/shopping', json={'text': 'Tej'}).json()
        assert c.patch(f"/api/shopping/{it['id']}", json={'text': '  '}).status_code == 422
