import { afterEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { createShopping, type ShopItem } from '../src/lib/shopping';

const item = (id: number, text: string, done = false, item_id: string | null = null): ShopItem =>
  ({ id, text, done, item_id, ha_linked: false });

describe('shopping store', () => {
  afterEach(() => vi.restoreAllMocks());
  it('tick is optimistic and calls back with the item (for "put in pantry?")', async () => {
    const api = { patch: vi.fn(async (id: number, body: any) => ({ ...item(id, 'Tej', body.done, 'milk') })),
                  post: vi.fn(), del: vi.fn(), clear: vi.fn() };
    const s = createShopping(api as any);
    s.items.set([item(1, 'Tej', false, 'milk')]);
    const p = s.tick(1);
    expect(get(s.items)[0].done).toBe(true);
    const ticked = await p;
    expect(ticked?.item_id).toBe('milk');
    expect(api.patch).toHaveBeenCalledWith(1, { done: true });
  });
  it('a failed tick rolls back', async () => {
    const api = { patch: vi.fn(() => Promise.reject(new Error('x'))), post: vi.fn(), del: vi.fn(), clear: vi.fn() };
    const s = createShopping(api as any);
    s.items.set([item(1, 'Tej')]);
    await s.tick(1).catch(() => {});
    expect(get(s.items)[0].done).toBe(false);
  });
  it('open and done lists split and count', () => {
    const s = createShopping({} as any);
    s.items.set([item(1, 'a'), item(2, 'b', true), item(3, 'c')]);
    expect(get(s.open).map((i) => i.id)).toEqual([1, 3]);
    expect(get(s.done).map((i) => i.id)).toEqual([2]);
  });
  it('adding blank text does nothing', async () => {
    const api = { post: vi.fn() };
    const s = createShopping(api as any);
    await s.add('   ');
    expect(api.post).not.toHaveBeenCalled();
  });
});
