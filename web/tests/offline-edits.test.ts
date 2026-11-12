// Offline edits: recipe edits, settings, folders queue in the outbox; timers keep a
// local copy and are handed to the server at the next reconnect. Every failing action's toast goes through failKey.
import { describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { createOutbox, type Op } from '../src/lib/outbox';
import { ApiError, failKey, OfflineError } from '../src/lib/api';
import { localDelete, localMoveRecipes, recount } from '../src/lib/folderactions';
import type { Folder } from '../src/lib/folders';
import type { Summary } from '../src/lib/recipes';
import { applyLocal, flushOfflineTimers, merge, offlineTimers, type Override, type Timer, type TimerSender } from '../src/lib/cooktimers';

function mem() {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), m };
}
const body = (title: string) => ({ title, servings: 2, ingredients: ['1 egg'], steps: ['cook'], tags: [] });

describe('outbox: recipe edits and settings', () => {
  it('the last edit of a recipe wins; other recipes keep theirs', () => {
    const ob = createOutbox(mem(), { send: vi.fn() });
    ob.push({ kind: 'recipe-put', id: 3, body: body('a') });
    ob.push({ kind: 'recipe-put', id: 4, body: body('x') });
    ob.push({ kind: 'recipe-put', id: 3, body: body('b') });
    expect(ob.ops().map((o) => (o.kind === 'recipe-put' ? `${o.id}:${o.body.title}` : o.kind))).toEqual(['4:x', '3:b']);
  });
  it('settings changes merge into one patch, the later value winning', () => {
    const ob = createOutbox(mem(), { send: vi.fn() });
    ob.push({ kind: 'settings', patch: { sounds: false, idle_minutes: 5 } });
    ob.push({ kind: 'settings', patch: { sounds: true } });
    expect(ob.ops()).toEqual([{ kind: 'settings', patch: { sounds: true, idle_minutes: 5 } }]);
  });
  it('the queue is visible to screens (pending edits)', () => {
    const ob = createOutbox(mem(), { send: vi.fn() });
    ob.push({ kind: 'recipe-put', id: 3, body: body('a') });
    expect(get(ob.queued)).toHaveLength(1);
  });
});

describe('outbox: folders created offline', () => {
  it('a rename or move of a folder made offline folds into its add', () => {
    const ob = createOutbox(mem(), { send: vi.fn() });
    ob.push({ kind: 'folder-add', tmp: -1, name: 'Levesek', parent_id: null });
    ob.push({ kind: 'folder-patch', id: -1, body: { name: 'Leves' } });
    ob.push({ kind: 'folder-patch', id: -1, body: { parent_id: 7 } });
    expect(ob.ops()).toEqual([{ kind: 'folder-add', tmp: -1, name: 'Leves', parent_id: 7 }]);
  });
  it('deleting it before it was sent forgets it, and what was filed in it moves up — like the server', () => {
    const ob = createOutbox(mem(), { send: vi.fn() });
    ob.push({ kind: 'folder-add', tmp: -1, name: 'A', parent_id: 7 });
    ob.push({ kind: 'folder-add', tmp: -2, name: 'B', parent_id: -1 });
    ob.push({ kind: 'recipes-move', ids: [3], folder_id: -1 });
    ob.push({ kind: 'folder-del', id: -1 });
    expect(ob.ops()).toEqual([
      { kind: 'folder-add', tmp: -2, name: 'B', parent_id: 7 },
      { kind: 'recipes-move', ids: [3], folder_id: 7 },
    ]);
  });
  it('every later op naming it is sent with the server\'s id', async () => {
    const sent: Op[] = [];
    const ob = createOutbox(mem(), { send: async (op) => { sent.push(op); return op.kind === 'folder-add' ? { id: op.name === 'A' ? 41 : 42 } : null; } });
    ob.push({ kind: 'folder-add', tmp: -1, name: 'A', parent_id: null });
    ob.push({ kind: 'recipes-move', ids: [3], folder_id: -1 });
    ob.push({ kind: 'pantry', node: 'eggs', have: true });          // breaks the fold: the next ops are separate
    ob.push({ kind: 'folder-add', tmp: -2, name: 'B', parent_id: -1 });
    expect(await ob.drain()).toBe(true);
    expect(sent).toEqual([
      { kind: 'folder-add', tmp: -1, name: 'A', parent_id: null },
      { kind: 'recipes-move', ids: [3], folder_id: 41 },
      { kind: 'pantry', node: 'eggs', have: true },
      { kind: 'folder-add', tmp: -2, name: 'B', parent_id: 41 },
    ]);
  });
  it('the id map survives a reload mid-drain (the add sent, the move not yet)', async () => {
    const store = mem();
    let calls = 0;
    const first = createOutbox(store, { send: async (op) => {
      calls++;
      if (op.kind === 'folder-add') return { id: 41 };
      throw new OfflineError('down');
    } });
    first.push({ kind: 'folder-add', tmp: -1, name: 'A', parent_id: null });
    first.push({ kind: 'recipes-move', ids: [3], folder_id: -1 });
    expect(await first.drain()).toBe(false);
    const sent: Op[] = [];
    const second = createOutbox(store, { send: async (op) => { sent.push(op); return null; } });
    expect(await second.drain()).toBe(true);
    expect(calls).toBe(2);
    expect(sent).toEqual([{ kind: 'recipes-move', ids: [3], folder_id: 41 }]);
  });
  it('an op naming a folder whose add was refused is dropped with it', async () => {
    const sent: Op[] = [];
    const ob = createOutbox(mem(), { send: async (op) => {
      if (op.kind === 'folder-add') throw new ApiError('taken', 409, { code: 'taken' });
      sent.push(op); return null;
    } });
    ob.push({ kind: 'folder-add', tmp: -1, name: 'A', parent_id: null });
    ob.push({ kind: 'pantry', node: 'eggs', have: true });
    ob.push({ kind: 'recipes-move', ids: [3], folder_id: -1 });
    expect(await ob.drain()).toBe(true);
    expect(sent).toEqual([{ kind: 'pantry', node: 'eggs', have: true }]);
  });
});

describe('folders changed locally the way the server would', () => {
  const f = (id: number, parent_id: number | null): Folder =>
    ({ id, name: `f${id}`, parent_id, recipes: 0, folders: 0, created_at: '', updated_at: '' });
  const r = (id: number, folder_id: number | null) => ({ id, folder_id }) as Summary;
  it('delete: the folder goes, its subfolders and recipes move up into its parent', () => {
    const out = localDelete([f(1, null), f(2, 1), f(3, 2)], [r(10, 2), r(11, 1)], 2);
    expect(out.list.map((x) => [x.id, x.parent_id])).toEqual([[1, null], [3, 1]]);
    expect(out.recipes.map((x) => [x.id, x.folder_id])).toEqual([[10, 1], [11, 1]]);
  });
  it('counts are recounted from the lists', () => {
    const list = recount([f(1, null), f(2, 1)], localMoveRecipes([r(10, null), r(11, null)], [10, 11], 2));
    expect(list.map((x) => [x.id, x.folders, x.recipes])).toEqual([[1, 1, 0], [2, 0, 2]]);
  });
});

describe('timers offline', () => {
  const T0 = 1_000_000;
  const tm = (over: Partial<Timer> = {}): Timer => ({ id: 5, label: 'Tészta', seconds: 600, state: 'running', remaining: 300,
    ends_at: null, recipe_id: 12, step_pos: 2, endsLocal: T0 + 300_000, ...over });

  it('pause / resume / add behave like the server', () => {
    const p = applyLocal(tm(), 'pause', 60, T0 + 100_000);
    expect([p.state, p.remaining, p.endsLocal]).toEqual(['paused', 200, null]);
    const r = applyLocal(p, 'resume', 60, T0 + 500_000);
    expect([r.state, r.endsLocal]).toEqual(['running', T0 + 700_000]);
    expect(applyLocal(tm(), 'add', 60, T0).endsLocal).toBe(T0 + 360_000);
    expect(applyLocal(p, 'add', 60, T0).remaining).toBe(260);
  });
  it('+1 min on a timer that rang (here or on the server) restarts it for that long', () => {
    for (const t of [tm({ endsLocal: T0 - 1 }), tm({ state: 'done', remaining: 0, endsLocal: null })]) {
      const a = applyLocal(t, 'add', 60, T0);
      expect([a.state, a.endsLocal]).toEqual(['running', T0 + 60_000]);
    }
  });
  it('the offline copy hides the server copy; a removed one hides it entirely', () => {
    const server = [tm({ id: 5 }), tm({ id: 6 })];
    const view = merge(server, { '5': { ...tm({ id: 5 }), state: 'paused' }, '6': { ...tm({ id: 6 }), removed: true }, '-9': tm({ id: -9 }) });
    expect(view.map((t) => [t.id, t.state])).toEqual([[5, 'paused'], [-9, 'running']]);
  });
  it('at reconnect each copy goes to the server as it stands then; a rung one waits; a failure stops the run', async () => {
    const calls: string[] = [];
    const send: TimerSender = {
      create: async (b) => { calls.push(`create ${b.label} ${b.seconds}s r${b.recipe_id ?? '-'}`); if (b.label === 'down') throw new OfflineError('x'); return { id: 99 } as never; },
      act: async (id, b) => { calls.push(`act ${id} ${b.action}`); },
      remove: async (id) => { calls.push(`remove ${id}`); if (id === 7) throw new ApiError('gone', 404, null); },
    };
    offlineTimers.set({
      '-1': tm({ id: -1, label: 'new', endsLocal: T0 + 90_000 }),                      // started offline, running
      '5': tm({ id: 5, label: 'paused', state: 'paused', remaining: 120, endsLocal: null }),  // a server timer paused offline
      '7': { ...tm({ id: 7 }), removed: true } as Override,                            // removed offline; gone already
      '-2': tm({ id: -2, label: 'rang', endsLocal: T0 - 5 }),                          // rang here: stays until stopped
      '-3': tm({ id: -3, label: 'down', endsLocal: T0 + 50_000 }),
      '-4': tm({ id: -4, label: 'after', endsLocal: T0 + 50_000 }),
    });
    await flushOfflineTimers(send, () => T0);
    // server timers first (JS orders integer-like keys first), then those started offline in the order made; timers are
    // independent, so the order does not matter — only that the run stops at the first network failure
    expect(calls).toEqual(['remove 5', 'create paused 120s r12', 'act 99 pause', 'remove 7', 'create new 90s r12', 'create down 50s r12']);
    expect(Object.keys(get(offlineTimers)).sort()).toEqual(['-2', '-3', '-4']);
    offlineTimers.set({});
  });
});

describe('every failing action says why (failKey)', () => {
  it('offline → "needs a connection"; anything else → the generic error', () => {
    expect(failKey(new OfflineError('x'))).toBe('toast.needs');
    expect(failKey(new ApiError('x', 422, null))).toBe('toast.error');
    expect(failKey(new Error('x'))).toBe('toast.error');
  });
  it('no screen or module names the generic error itself (it would hide "needs a connection")', () => {
    const src = join(__dirname, '../src');
    const files: string[] = [];
    const walk = (d: string) => { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) walk(p); else if (/\.(ts|svelte)$/.test(f)) files.push(p); } };
    walk(src);
    const hits = files.filter((f) => !f.endsWith('lib/api.ts') && readFileSync(f, 'utf8').includes("'toast.error'")).map((f) => f.slice(src.length + 1));
    expect(files.length).toBeGreaterThan(50);                           // positive control: the walk saw the app
    expect(hits).toEqual([]);
  });
});
