"""Weather for the home and idle screens, from HA's weather entity, cached for ten minutes."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from .ha import HAClient

# HA weather states -> our sprite icon ids (icons/manifest.yaml). Anything unknown falls back to cloudy.
_CONDITIONS = {
    'sunny': 'sunny', 'clear-night': 'clear-night', 'partlycloudy': 'partlycloudy', 'cloudy': 'cloudy',
    'rainy': 'rainy', 'pouring': 'pouring', 'snowy': 'snowy', 'snowy-rainy': 'snowy', 'fog': 'fog',
    'lightning': 'lightning', 'lightning-rainy': 'lightning', 'windy': 'windy', 'windy-variant': 'windy',
    'hail': 'hail', 'exceptional': 'exceptional',
}
TTL = timedelta(minutes=10)
MAX_STALE = timedelta(hours=1)    # through a longer HA outage the chip hides rather than show old weather


def map_condition(ha_state: str) -> str:
    return _CONDITIONS.get(ha_state, 'cloudy')


class WeatherService:
    def __init__(self, ha: HAClient, entity: str, now: Callable[[], datetime]) -> None:
        self.ha, self.entity, self.now = ha, entity, now
        self._cached: dict[str, Any] | None = None
        self._at: datetime | None = None

    async def current(self) -> dict[str, Any]:
        if self._cached is not None and self._at is not None and self.now() - self._at < TTL:
            return self._cached
        state = await self.ha.get_state(self.entity)
        if state is None or state.get('state') in (None, 'unavailable', 'unknown'):
            if self._cached is not None and self._at is not None and self.now() - self._at < MAX_STALE:
                return self._cached                           # keep the last good reading through a short HA outage
            return {'condition': None}
        attrs = state.get('attributes', {})
        self._cached = {'condition': map_condition(state['state']), 'temp': attrs.get('temperature'),
                        'unit': attrs.get('temperature_unit', '°C')}
        self._at = self.now()
        return self._cached
