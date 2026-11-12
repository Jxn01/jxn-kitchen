import asyncio

from kitchen.events import Broadcaster, format_sse, sse_stream


def test_format_is_exact():
    assert format_sse('settings', {'a': 1}) == 'event: settings\ndata: {"a": 1}\n\n'
    assert format_sse('x', {'t': 'ő'}) == 'event: x\ndata: {"t": "ő"}\n\n'


def test_publish_reaches_every_subscriber():
    async def go():
        b = Broadcaster()
        q1, q2 = b.subscribe(), b.subscribe()
        b.publish('x', {'a': 1})
        assert (await q1.get()) == ('x', {'a': 1}) and (await q2.get()) == ('x', {'a': 1})
        b.unsubscribe(q1)
        b.publish('y', {})
        assert q1.empty() and (await q2.get()) == ('y', {})
    asyncio.run(go())


def test_full_queue_drops_instead_of_blocking():
    b = Broadcaster(queue_size=2)
    q = b.subscribe()
    for i in range(5):
        b.publish('n', {'i': i})
    assert q.qsize() == 2


def test_stream_yields_events_pings_and_stops_on_disconnect():
    async def go():
        b = Broadcaster()
        state = {'gone': False}
        async def is_disconnected():
            return state['gone']
        gen = sse_stream(b, is_disconnected, ping_every=0.05)
        first = await gen.__anext__()
        assert first.startswith('retry: ')
        b.publish('settings', {'language': 'hu'})
        assert await gen.__anext__() == 'event: settings\ndata: {"language": "hu"}\n\n'
        assert await gen.__anext__() == 'event: ping\ndata: {}\n\n'   # nothing published within ping_every
        state['gone'] = True
        rest = [chunk async for chunk in gen]
        assert rest == [] and b.subscriber_count == 0
    asyncio.run(go())


def test_settings_put_publishes(client):
    b = client.app.state.events
    q = b.subscribe()
    client.put('/api/settings', json={'language': 'hu'})
    assert q.get_nowait()[0] == 'settings'
