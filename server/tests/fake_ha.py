"""An in-memory Home Assistant good enough for the to-do sync: states, todo services, the shopping_list config flow."""
from __future__ import annotations

import itertools
import json

import httpx


class FakeHA:
    def __init__(self, has_list: bool = True):
        self.has_list = has_list
        self.items: list[dict] = []           # {'uid','summary','status'}
        self.down = False
        self.calls: list[tuple[str, dict]] = []
        self._uid = itertools.count(1)
        self.flows = 0
        self.notified: list[dict] = []         # script.notify_owner calls (the phone notifications)

    # helpers for tests (the "phone" acting in the HA app)
    def phone_add(self, summary):
        self.items.append({'uid': f'u{next(self._uid)}', 'summary': summary, 'status': 'needs_action'})

    def by_summary(self, summary):
        return next(i for i in self.items if i['summary'] == summary)

    def handler(self, req: httpx.Request) -> httpx.Response:
        if self.down:
            return httpx.Response(500)
        path, body = req.url.path, (json.loads(req.content) if req.content else {})
        self.calls.append((path, body))
        if path == '/api/services/script/notify_owner':
            self.notified.append(body)
            return httpx.Response(200, json=[])
        if path == '/api/states/todo.shopping_list':
            if not self.has_list:
                return httpx.Response(404, json={'message': 'Entity not found.'})
            return httpx.Response(200, json={'entity_id': 'todo.shopping_list', 'state': str(len(self.items))})
        if path == '/api/config/config_entries/flow' and body.get('handler') == 'shopping_list':
            self.flows += 1
            return httpx.Response(200, json={'type': 'form', 'flow_id': 'f1', 'step_id': 'user'})
        if path == '/api/config/config_entries/flow/f1':
            self.has_list = True
            return httpx.Response(200, json={'type': 'create_entry', 'title': 'Shopping list'})
        if not self.has_list:
            return httpx.Response(400, json={'message': 'no todo.shopping_list'})
        if path == '/api/services/todo/get_items':
            return httpx.Response(200, json={'changed_states': [], 'service_response': {
                'todo.shopping_list': {'items': [dict(i) for i in self.items]}}})
        if path == '/api/services/todo/add_item':
            self.items.append({'uid': f'u{next(self._uid)}', 'summary': body['item'], 'status': 'needs_action'})
            return httpx.Response(200, json=[])
        if path == '/api/services/todo/update_item':
            it = next((i for i in self.items if i['uid'] == body['item'] or i['summary'] == body['item']), None)
            if it is None:
                return httpx.Response(400, json={'message': 'Unable to find to-do list item'})
            if 'rename' in body:
                it['summary'] = body['rename']
            if 'status' in body:
                it['status'] = body['status']
            return httpx.Response(200, json=[])
        if path == '/api/services/todo/remove_item':
            keys = body['item'] if isinstance(body['item'], list) else [body['item']]
            self.items = [i for i in self.items if i['uid'] not in keys and i['summary'] not in keys]
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    def client(self) -> httpx.AsyncClient:
        # late-bound, so a test can wrap self.handler after the app was built (to inject writes mid-request)
        return httpx.AsyncClient(transport=httpx.MockTransport(lambda req: self.handler(req)))
