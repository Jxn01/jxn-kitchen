import httpx
import pytest
from fastapi.testclient import TestClient

from kitchen.app import create_app
from kitchen.config import Config
from kitchen.weather import map_condition


def make_client(tmp_path, handler, now=None):
    cfg = Config(data_dir=tmp_path, static_dir=None, ha_url='http://ha.test', ha_token='t')
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(create_app(cfg, http=http, now=now))


@pytest.mark.parametrize('ha,ours', [('sunny', 'sunny'), ('partlycloudy', 'partlycloudy'), ('lightning-rainy', 'lightning'),
                                     ('snowy-rainy', 'snowy'), ('windy-variant', 'windy'), ('foo', 'cloudy'), ('', 'cloudy')])
def test_map_condition(ha, ours):
    assert map_condition(ha) == ours


def test_weather_from_ha(tmp_path):
    calls = []
    def handler(req):
        if req.url.path != '/api/states/weather.forecast_home':
            return httpx.Response(404)                       # other background HA traffic (shopping sync)
        calls.append(req)
        assert req.headers['authorization'] == 'Bearer t'
        return httpx.Response(200, json={'state': 'partlycloudy', 'attributes': {'temperature': 19.1, 'temperature_unit': '°C'}})
    with make_client(tmp_path, handler) as c:
        assert c.get('/api/weather').json() == {'condition': 'partlycloudy', 'temp': 19.1, 'unit': '°C'}
        c.get('/api/weather')
        assert len(calls) == 1                                   # cached


def test_weather_ha_down_is_not_an_error(tmp_path):
    with make_client(tmp_path, lambda req: httpx.Response(500)) as c:  # HA down for everything
        r = c.get('/api/weather')
        assert r.status_code == 200 and r.json() == {'condition': None}


def test_weather_without_ha_config(client):
    assert client.get('/api/weather').json() == {'condition': None}


def test_an_old_reading_is_hidden_after_an_hour_of_ha_outage():
    import asyncio
    from datetime import datetime, timedelta
    from kitchen.weather import WeatherService
    t = [datetime(2026, 10, 10, 12, 0)]
    class HA:
        up = True
        async def get_state(self, e):
            return {'state': 'sunny', 'attributes': {'temperature': 21}} if self.up else None
    ha = HA()
    w = WeatherService(ha, 'weather.home', lambda: t[0])
    assert asyncio.run(w.current())['condition'] == 'sunny'
    ha.up = False
    t[0] += timedelta(minutes=30)
    assert asyncio.run(w.current())['condition'] == 'sunny'
    t[0] += timedelta(minutes=31)
    assert asyncio.run(w.current())['condition'] is None
