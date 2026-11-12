"""The kiosk agent's side of the API: heartbeats (health for Gatus) and the backlight level for right now."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo

from pydantic import BaseModel, StrictBool, StrictInt, StrictStr

from .night import is_night

STALE_AFTER = timedelta(seconds=180)


class Heartbeat(BaseModel):
    agent: StrictStr
    chrome_ok: StrictBool
    free_mb: StrictInt
    overlay_ok: StrictBool | None = None   # the Browse overlay is registered (agent ≥ SP5); None = an older agent


class KioskState:
    def __init__(self, now: Callable[[], datetime]) -> None:
        self.now = now
        self.last: Heartbeat | None = None
        self.at: datetime | None = None

    def beat(self, hb: Heartbeat) -> None:
        self.last, self.at = hb, self.now()

    def health(self) -> tuple[bool, dict[str, Any]]:
        if self.last is None or self.at is None:
            return False, {'age_s': None}
        age = self.now() - self.at
        body = {'age_s': int(age.total_seconds()), **self.last.model_dump()}
        return age < STALE_AFTER, body


def display(now_utc: datetime, tz: str, settings: dict[str, Any]) -> dict[str, Any]:
    local = now_utc.astimezone(ZoneInfo(tz))
    night = is_night(local.time(), settings['night_start'], settings['night_end'])
    return {'night': night, 'brightness': settings['night_brightness' if night else 'day_brightness']}
