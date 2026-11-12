"""ASGI entry point: `uvicorn kitchen.main:app` (the container's command). Configuration comes from the env."""
from .app import create_app
from .config import Config

_cfg = Config.from_env()
app = create_app(_cfg, shopping_sync_every=_cfg.shopping_sync_seconds or None)
