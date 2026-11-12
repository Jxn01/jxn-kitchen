// The shopping list on the client; the server mirrors it with HA's to-do list (so it's on the phone).
import { derived, get, writable } from 'svelte/store';
import { del, getJSON, OfflineError, patchJSON, postJSON } from './api';
import { outbox } from './queue';

export interface ShopItem { id: number; text: string; item_id: string | null; done: boolean; ha_linked: boolean }
export interface ShoppingApi {
  post(body: { text?: string; item_id?: string }): Promise<ShopItem>;
  patch(id: number, body: { done?: boolean; text?: string }): Promise<ShopItem>;
  del(id: number): Promise<void>;
  clear(): Promise<ShopItem[]>;
}

export const restShoppingApi: ShoppingApi = {
  post: (body) => postJSON<ShopItem>('/api/shopping', body),
  patch: (id, body) => patchJSON<ShopItem>(`/api/shopping/${id}`, body),
  del: (id) => del(`/api/shopping/${id}`),
  clear: () => postJSON<ShopItem[]>('/api/shopping/clear-done', {}),
};

// Offline (spec §9): every action stays optimistic and queues its write (lib/outbox.ts). An item added offline gets a
// NEGATIVE temporary id; its later tick/removal folds into the queued add. After a replay the list is reloaded.
export function createShopping(api: ShoppingApi = restShoppingApi, queue: { push: typeof outbox.push } = outbox) {
  let nextTmp = -1;
  const items = writable<ShopItem[]>([]);
  const open = derived(items, (xs) => xs.filter((i) => !i.done));
  const done = derived(items, (xs) => xs.filter((i) => i.done));
  async function addBody(body: { text?: string; item_id?: string }, label: string, itemId?: string): Promise<ShopItem> {
    try {
      const it = await api.post(body);
      replace(it);
      return it;
    } catch (e) {
      if (!(e instanceof OfflineError)) throw e;
      const it: ShopItem = { id: nextTmp--, text: label, item_id: itemId ?? null, done: false, ha_linked: false };
      queue.push({ kind: 'shop-add', tmp: it.id, body });
      replace(it);
      return it;
    }
  }
  const replace = (it: ShopItem) => items.update((xs) => xs.some((x) => x.id === it.id) ? xs.map((x) => x.id === it.id ? it : x) : [...xs, it]);
  return {
    items, open, done,
    async add(text: string): Promise<ShopItem | null> {
      if (!text.trim()) return null;
      return addBody({ text: text.trim() }, text.trim());
    },
    /** `label` is what the list shows if the server is away (normally the server writes the item's name). */
    async addItem(itemId: string, label?: string): Promise<ShopItem> {
      return addBody({ item_id: itemId }, label ?? itemId, itemId);
    },
    /** Tick (or untick) an item; resolves to the updated item. Optimistic; rolls back on failure. */
    async tick(id: number, to = true): Promise<ShopItem | null> {
      const before = get(items);
      items.update((xs) => xs.map((x) => x.id === id ? { ...x, done: to } : x));
      if (id < 0) { queue.push({ kind: 'shop-patch', id, body: { done: to } }); return get(items).find((x) => x.id === id) ?? null; }
      try {
        const it = await api.patch(id, { done: to });
        replace(it);
        return it;
      } catch (e) {
        if (e instanceof OfflineError) { queue.push({ kind: 'shop-patch', id, body: { done: to } }); return get(items).find((x) => x.id === id) ?? null; }
        items.set(before);
        throw e;
      }
    },
    async remove(id: number): Promise<void> {
      const before = get(items);
      items.update((xs) => xs.filter((x) => x.id !== id));
      if (id < 0) { queue.push({ kind: 'shop-del', id }); return; }
      try { await api.del(id); } catch (e) {
        if (e instanceof OfflineError) { queue.push({ kind: 'shop-del', id }); return; }
        items.set(before); throw e;
      }
    },
    async clearDone(): Promise<void> {
      try { items.set(await api.clear()); } catch (e) {
        if (!(e instanceof OfflineError)) throw e;
        for (const x of get(items).filter((i) => i.done)) queue.push({ kind: 'shop-del', id: x.id });
        items.update((xs) => xs.filter((i) => !i.done));
      }
    },
    /** Undo a removal: the same text (and item) back on the list, ticked state kept. */
    async restore(it: ShopItem): Promise<ShopItem> {
      const back = it.item_id ? await this.addItem(it.item_id, it.text) : (await this.add(it.text))!;
      return it.done ? ((await this.tick(back.id, true)) ?? back) : back;
    },
  };
}

export const shopping = createShopping();
export async function loadShopping(): Promise<void> {
  try { shopping.items.set(await getJSON<ShopItem[]>('/api/shopping')); } catch { /* offline */ }
}
export const openCount = derived(shopping.open, (xs) => xs.length);
