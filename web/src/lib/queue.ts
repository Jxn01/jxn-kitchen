// The app-wide outbox (lib/outbox.ts) and how each queued op is sent. Pantry, shopping, recipe edits, settings and
// folder writes use it when the server is away; App.svelte drains it whenever the live connection comes back.
import { createOutbox, type Op } from './outbox';
import { del, patchJSON, postJSON, putJSON } from './api';

async function send(op: Op): Promise<unknown> {
  switch (op.kind) {
    case 'pantry':
      return putJSON(`/api/pantry/${encodeURIComponent(op.node)}`, { have: op.have });
    case 'shop-add': {
      const it = await postJSON<{ id: number }>('/api/shopping', op.body);
      if (op.done) await patchJSON(`/api/shopping/${it.id}`, { done: true });
      return it;
    }
    case 'shop-patch':
      return patchJSON(`/api/shopping/${op.id}`, op.body);
    case 'shop-del':
      return del(`/api/shopping/${op.id}`);
    case 'recipe-put':
      return putJSON(`/api/recipes/${op.id}`, op.body);
    case 'settings':
      return putJSON('/api/settings', op.patch);
    case 'folder-add':
      return postJSON<{ id: number }>('/api/folders', { name: op.name, parent_id: op.parent_id });   // its id maps the temporary one
    case 'folder-patch':
      return patchJSON(`/api/folders/${op.id}`, op.body);
    case 'folder-del':
      return del(`/api/folders/${op.id}`);
    case 'recipes-move':
      return postJSON('/api/recipes/move', { ids: op.ids, folder_id: op.folder_id });
  }
}

let storage: Storage | undefined;
try { storage = globalThis.localStorage; } catch { storage = undefined; }
export const outbox = createOutbox(storage, { send });
