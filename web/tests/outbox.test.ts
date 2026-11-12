import { describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { createOutbox, type Op } from '../src/lib/outbox';
import { OfflineError } from '../src/lib/api';

function mem() {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), m };
}

describe('outbox (spec §9: writes made offline are queued and replayed)', () => {
  it('pantry writes coalesce per node: the last one wins', () => {
    const ob = createOutbox(mem(), { send: vi.fn() });
    ob.push({ kind: 'pantry', node: 'eggs', have: true });
    ob.push({ kind: 'pantry', node: 'milk', have: true });
    ob.push({ kind: 'pantry', node: 'eggs', have: false });
    expect(ob.ops()).toEqual([{ kind: 'pantry', node: 'milk', have: true }, { kind: 'pantry', node: 'eggs', have: false }]);
  });

  it('a tick or removal of an item added offline folds into its queued add', () => {
    const ob = createOutbox(mem(), { send: vi.fn() });
    ob.push({ kind: 'shop-add', tmp: -1, body: { text: 'Tej' } });
    ob.push({ kind: 'shop-add', tmp: -2, body: { text: 'Só' } });
    ob.push({ kind: 'shop-patch', id: -1, body: { done: true } });
    ob.push({ kind: 'shop-del', id: -2 });
    expect(ob.ops()).toEqual([{ kind: 'shop-add', tmp: -1, body: { text: 'Tej' }, done: true }]);
  });

  it('replays in order; a network failure keeps the rest; a refused op is dropped', async () => {
    const sent: Op[] = [];
    let down = false;
    const send = vi.fn(async (op: Op) => {
      if (down) throw new OfflineError('down');
      if (op.kind === 'shop-patch' && op.id === 404) throw new Error('PATCH -> 404');
      sent.push(op);
    });
    const store = mem();
    const ob = createOutbox(store, { send });
    ob.push({ kind: 'pantry', node: 'eggs', have: true });
    ob.push({ kind: 'shop-patch', id: 404, body: { done: true } });     // gone on the server: dropped
    ob.push({ kind: 'shop-del', id: 7 });
    down = true;
    expect(await ob.drain()).toBe(false);
    expect(ob.ops()).toHaveLength(3);
    down = false;
    expect(await ob.drain()).toBe(true);
    expect(sent.map((o) => o.kind)).toEqual(['pantry', 'shop-del']);
    expect(ob.ops()).toEqual([]);
    expect(get(ob.pending)).toBe(0);
  });

  it('a drain of an EMPTY queue (every page load) does not block later drains', async () => {
    const send = vi.fn(async () => {});
    const ob = createOutbox(mem(), { send });
    expect(await ob.drain()).toBe(true);              // nothing queued yet: finishes without awaiting anything
    ob.push({ kind: 'pantry', node: 'eggs', have: true });
    expect(await ob.drain()).toBe(true);
    expect(send).toHaveBeenCalledOnce();               // found end-to-end: this second drain used to do nothing
  });

  it('survives a reload (persisted), and a broken store never breaks the app', () => {
    const store = mem();
    createOutbox(store, { send: vi.fn() }).push({ kind: 'pantry', node: 'eggs', have: true });
    expect(createOutbox(store, { send: vi.fn() }).ops()).toHaveLength(1);
    const broken = { getItem: () => { throw new Error('denied'); }, setItem: () => { throw new Error('denied'); } };
    const ob = createOutbox(broken, { send: vi.fn() });
    ob.push({ kind: 'pantry', node: 'eggs', have: true });
    expect(ob.ops()).toHaveLength(1);
  });
});

import { createPantry } from '../src/lib/pantry';
import { createShopping } from '../src/lib/shopping';

describe('screens stay optimistic offline and queue the write', () => {
  it('pantry: an offline tap stays and is queued; a refusal still rolls back', async () => {
    const q = { push: vi.fn() };
    const p = createPantry({ put: vi.fn(() => Promise.reject(new OfflineError('down'))) } as any, q);
    p.accept({ have: [], groups_some: [], staples_off: [], rev: 0 });
    expect(await p.toggle('eggs')).toBe(true);
    expect(get(p.state).have).toEqual(['eggs']);
    expect(q.push).toHaveBeenCalledWith({ kind: 'pantry', node: 'eggs', have: true });
    const p2 = createPantry({ put: vi.fn(() => Promise.reject(new Error('PUT -> 422'))) } as any, q);
    p2.accept({ have: [], groups_some: [], staples_off: [], rev: 0 });
    await expect(p2.toggle('eggs')).rejects.toThrow();
    expect(get(p2.state).have).toEqual([]);
  });

  it('shopping: offline adds get temporary ids; their tick/removal queue against them', async () => {
    const q = { push: vi.fn() };
    const down = () => Promise.reject(new OfflineError('down'));
    const s = createShopping({ post: vi.fn(down), patch: vi.fn(down), del: vi.fn(down), clear: vi.fn(down) } as any, q);
    const a = (await s.add('Tej'))!;
    const b = await s.addItem('eggs', 'Tojás');
    expect(a.id).toBeLessThan(0);
    expect(b).toMatchObject({ text: 'Tojás', item_id: 'eggs' });
    await s.tick(a.id, true);
    await s.remove(b.id);
    expect(q.push.mock.calls.map((c) => c[0])).toEqual([
      { kind: 'shop-add', tmp: a.id, body: { text: 'Tej' } },
      { kind: 'shop-add', tmp: b.id, body: { item_id: 'eggs' } },
      { kind: 'shop-patch', id: a.id, body: { done: true } },
      { kind: 'shop-del', id: b.id },
    ]);
    expect(get(s.items).map((i) => [i.text, i.done])).toEqual([['Tej', true]]);
  });
});
