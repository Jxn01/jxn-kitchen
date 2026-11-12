"""A tiny Home Assistant REST client. Every call degrades to None/False instead of raising: HA being down must
never break a kitchen screen."""
from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


class HAClient:
    def __init__(self, base_url: str | None, token: str | None, http: httpx.AsyncClient) -> None:
        self.base_url = (base_url or '').rstrip('/')
        self.token = token
        self.http = http

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _headers(self) -> dict[str, str]:
        return {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        if not self.configured:
            return None
        try:
            r = await self.http.get(f'{self.base_url}/api/states/{entity_id}', headers=self._headers(), timeout=5)
            if r.status_code != 200:
                log.warning('HA get_state %s -> %s', entity_id, r.status_code)
                return None
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            log.warning('HA get_state %s failed: %s', entity_id, e)
            return None

    async def call_service(self, domain: str, service: str, data: dict[str, Any],
                           return_response: bool = False) -> Any:
        """POST /api/services/<domain>/<service>. Returns the service response (or [] / {}), None on any failure."""
        if not self.configured:
            return None
        url = f'{self.base_url}/api/services/{domain}/{service}' + ('?return_response' if return_response else '')
        try:
            r = await self.http.post(url, headers=self._headers(), json=data, timeout=10)
            if r.status_code != 200:
                log.warning('HA %s.%s -> %s %r', domain, service, r.status_code, r.text[:200])
                return None
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            log.warning('HA %s.%s failed: %s', domain, service, e)
            return None

    async def todo_items(self, entity_id: str) -> list[dict[str, Any]] | None:
        r = await self.call_service('todo', 'get_items', {'entity_id': entity_id}, return_response=True)
        try:
            return r['service_response'][entity_id]['items']
        except (TypeError, KeyError):
            return None

    async def ensure_shopping_list(self) -> bool:
        """Make sure HA has the built-in Shopping List integration (entity todo.shopping_list): create it through the
        config-flow API when missing. Idempotent; False if HA is unreachable or refuses."""
        if not self.configured:
            return False
        if await self.get_state('todo.shopping_list') is not None:
            return True
        try:
            r = await self.http.post(f'{self.base_url}/api/config/config_entries/flow', headers=self._headers(),
                                     json={'handler': 'shopping_list', 'show_advanced_options': False}, timeout=10)
            flow = r.json()
            for _ in range(3):
                if flow.get('type') == 'create_entry':
                    log.info('HA: created the Shopping List integration')
                    return True
                if flow.get('type') != 'form':
                    log.warning('HA shopping_list flow: %r', flow)
                    return False
                r = await self.http.post(f"{self.base_url}/api/config/config_entries/flow/{flow['flow_id']}",
                                         headers=self._headers(), json={}, timeout=10)
                flow = r.json()
            return flow.get('type') == 'create_entry'
        except (httpx.HTTPError, ValueError, KeyError) as e:
            log.warning('HA shopping_list flow failed: %s', e)
            return False
