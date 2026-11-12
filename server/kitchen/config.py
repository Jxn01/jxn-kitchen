"""Runtime configuration, read from the environment (see README → Environment)."""
from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    data_dir: pathlib.Path                 # KITCHEN_DATA_DIR   — SQLite DB + uploads (default /data)
    static_dir: pathlib.Path | None        # KITCHEN_STATIC_DIR — the built web app (default /app/static, if present)
    ha_url: str | None                     # HA_URL             — e.g. http://192.168.1.2:8123
    ha_token: str | None                   # HA_TOKEN           — long-lived token (only in /etc/kitchen/kitchen.env)
    catalogue_dir: pathlib.Path | None = None        # KITCHEN_CATALOGUE_DIR — default: /app/catalogue or the repo's
    weather_entity: str = 'weather.forecast_home'   # KITCHEN_WEATHER_ENTITY
    timezone: str = 'Europe/Budapest'               # KITCHEN_TZ
    shopping_sync_seconds: float = 20.0             # KITCHEN_SHOPPING_SYNC_SECONDS — 0 disables the HA to-do mirror
    build: str = 'dev'                              # KITCHEN_BUILD — set at image build; the web app reloads on change
    scans_dir: pathlib.Path | None = None           # KITCHEN_SCANS_DIR — the scan inbox (the share's scans/, read-only)
    spices: bool = True                             # serve Spices & Sauces: engine/ must sit next to the catalogue and
                                                    # validate, or the server refuses to start (only tests that boot
                                                    # on the small fixture catalogue switch it off)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> 'Config':
        env = dict(os.environ if env is None else env)
        static = env.get('KITCHEN_STATIC_DIR', '/app/static')
        static_path = pathlib.Path(static) if static and pathlib.Path(static).is_dir() else None
        return cls(
            data_dir=pathlib.Path(env.get('KITCHEN_DATA_DIR', '/data')),
            static_dir=static_path,
            ha_url=env.get('HA_URL') or None,
            ha_token=env.get('HA_TOKEN') or None,
            catalogue_dir=pathlib.Path(env['KITCHEN_CATALOGUE_DIR']) if env.get('KITCHEN_CATALOGUE_DIR') else None,
            weather_entity=env.get('KITCHEN_WEATHER_ENTITY', 'weather.forecast_home'),
            timezone=env.get('KITCHEN_TZ', 'Europe/Budapest'),
            shopping_sync_seconds=float(env.get('KITCHEN_SHOPPING_SYNC_SECONDS', '20')),
            build=env.get('KITCHEN_BUILD', 'dev'),
            scans_dir=pathlib.Path(env['KITCHEN_SCANS_DIR']) if env.get('KITCHEN_SCANS_DIR') else None,
        )

    @property
    def db_path(self) -> pathlib.Path:
        return self.data_dir / 'kitchen.db'

    @property
    def knowhow_path(self) -> pathlib.Path:
        """The know-how library (knowhow/*.yaml): next to the catalogue, in the image and in the repo."""
        return self.catalogue_path.parent / 'knowhow'

    @property
    def engine_path(self) -> pathlib.Path:
        """The spice and sauce engines' knowledge (engine/spices, engine/sauces): next to the catalogue, like knowhow."""
        return self.catalogue_path.parent / 'engine'

    @property
    def catalogue_path(self) -> pathlib.Path:
        if self.catalogue_dir is not None:
            return self.catalogue_dir
        for candidate in (pathlib.Path('/app/catalogue'), pathlib.Path(__file__).resolve().parents[2] / 'catalogue'):
            if (candidate / 'categories.yaml').exists():
                return candidate
        raise RuntimeError('no catalogue found (set KITCHEN_CATALOGUE_DIR)')
