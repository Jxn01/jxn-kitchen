// Writes made while the server is unreachable (spec §9): kept, queued in localStorage and replayed in order when the
// connection comes back. The screens stay optimistic meanwhile; the offline badge shows how many are waiting.
//
// What is queued: pantry toggles (coalesced per node — only the last one matters), shopping-list changes, and since
// 2026-11-12 (owner's list item 5) recipe edits (`recipe-put`, last edit per recipe wins), settings (one merged patch),
// folder create / rename / move / delete and filing recipes into a folder. A tick or removal of an item that was itself
// added offline (negative temporary id) folds into its queued add, so nothing ever refers to an id the server has not
// given out; a folder created offline also gets a temporary id, and every later op that names it is rewritten to the
// server's id once its add has been sent (the map is kept in localStorage, so a drain cut short by a reload still
// knows it). Edits made here and elsewhere meanwhile: the last write wins (the owner: "very very small edge case").
// A network failure or a 5xx (OfflineError) keeps the rest of the queue for the next drain; any other refusal (a 404 for
// an item deleted meanwhile, a 422, a folder name taken) drops that op — and an op naming a folder whose add was dropped
// is dropped with it.
import { writable } from 'svelte/store';
import { OfflineError } from './api';
import type { RecipeIn } from './recipes';

export type FolderBody = { name?: string; parent_id?: number | null };
export type Op =
  | { kind: 'pantry'; node: string; have: boolean }
  | { kind: 'shop-add'; tmp: number; body: { text?: string; item_id?: string }; done?: boolean }
  | { kind: 'shop-patch'; id: number; body: { done?: boolean; text?: string } }
  | { kind: 'shop-del'; id: number }
  | { kind: 'recipe-put'; id: number; body: RecipeIn }
  | { kind: 'settings'; patch: Record<string, unknown> }
  | { kind: 'folder-add'; tmp: number; name: string; parent_id: number | null }
  | { kind: 'folder-patch'; id: number; body: FolderBody }
  | { kind: 'folder-del'; id: number }
  | { kind: 'recipes-move'; ids: number[]; folder_id: number | null };

/** A temporary id for something created offline: negative (the server's are positive) and unique across reloads. */
let tmpSeq = 0;
export function tmpId(): number { tmpSeq = (tmpSeq + 1) % 1000; return -(Date.now() * 1000 + tmpSeq); }

export interface Sender { send(op: Op): Promise<unknown> }
interface Store { getItem(k: string): string | null; setItem(k: string, v: string): void }

const KEY = 'kitchen.outbox';
const IDS_KEY = 'kitchen.outbox.ids';   // temporary folder id -> the server's, while ops may still name it

export function createOutbox(storage: Store | undefined, sender: Sender) {
  let ops: Op[] = [];
  try { ops = JSON.parse(storage?.getItem(KEY) ?? '[]'); } catch { ops = []; }
  if (!Array.isArray(ops)) ops = [];
  let ids: Record<string, number> = {};
  try { ids = JSON.parse(storage?.getItem(IDS_KEY) ?? '{}') ?? {}; } catch { ids = {}; }
  const pending = writable(ops.length);
  /** The queue itself, for screens that show what is waiting (a recipe edited offline). */
  const queued = writable<Op[]>(ops.map((o) => ({ ...o })));
  let draining: Promise<boolean> | null = null;

  function save() {
    if (!ops.length) ids = {};   // nothing can name a temporary id any more
    try {
      storage?.setItem(KEY, JSON.stringify(ops));
      storage?.setItem(IDS_KEY, JSON.stringify(ids));
    } catch { /* private mode / full: in-memory still works */ }
    pending.set(ops.length);
    queued.set(ops.map((o) => ({ ...o })));
  }

  const folderAdd = (tmp: number) =>
    ops.find((o): o is Extract<Op, { kind: 'folder-add' }> => o.kind === 'folder-add' && o.tmp === tmp);

  function push(op: Op): void {
    if (op.kind === 'pantry') {
      ops = ops.filter((o) => !(o.kind === 'pantry' && o.node === op.node));
    } else if (op.kind === 'recipe-put') {
      ops = ops.filter((o) => !(o.kind === 'recipe-put' && o.id === op.id));
    } else if (op.kind === 'settings') {
      const prev = ops.find((o): o is Extract<Op, { kind: 'settings' }> => o.kind === 'settings');
      if (prev) { prev.patch = { ...prev.patch, ...op.patch }; save(); return; }
    } else if ((op.kind === 'shop-patch' || op.kind === 'shop-del') && op.id < 0) {
      const add = ops.find((o): o is Extract<Op, { kind: 'shop-add' }> => o.kind === 'shop-add' && o.tmp === op.id);
      if (op.kind === 'shop-del') ops = ops.filter((o) => o !== add);
      else if (add) {
        if (op.body.done !== undefined) add.done = op.body.done;
        if (op.body.text !== undefined) add.body = { text: op.body.text };
      }
      save();
      return;
    } else if (op.kind === 'folder-patch' && op.id < 0 && folderAdd(op.id)) {
      const add = folderAdd(op.id)!;
      if (op.body.name !== undefined) add.name = op.body.name;
      if (op.body.parent_id !== undefined) add.parent_id = op.body.parent_id;
      save();
      return;
    } else if (op.kind === 'folder-del' && op.id < 0 && folderAdd(op.id)) {
      // never sent: forget it, and move what was filed in it up into its parent — what the server's delete does
      const parent = folderAdd(op.id)!.parent_id;
      ops = ops.filter((o) => !((o.kind === 'folder-add' && o.tmp === op.id) || (o.kind === 'folder-patch' && o.id === op.id)));
      for (const o of ops) {
        if (o.kind === 'recipes-move' && o.folder_id === op.id) o.folder_id = parent;
        if (o.kind === 'folder-add' && o.parent_id === op.id) o.parent_id = parent;
        if (o.kind === 'folder-patch' && o.body.parent_id === op.id) o.body.parent_id = parent;
      }
      save();
      return;
    }
    ops.push(op);
    save();
  }

  /** The op as the server must see it: temporary folder ids replaced by the server's. null = it names a temporary
   *  folder whose add never reached the server (refused), so the op is dropped too. */
  function resolve(op: Op): Op | null {
    const map = (id: number | null): number | null | undefined => (id === null || id >= 0 ? id : ids[String(id)]);
    switch (op.kind) {
      case 'folder-add': { const p = map(op.parent_id); return p === undefined ? null : { ...op, parent_id: p }; }
      case 'folder-patch': {
        const id = map(op.id);
        const body = { ...op.body };
        if (body.parent_id !== undefined) { const p = map(body.parent_id); if (p === undefined) return null; body.parent_id = p; }
        return id == null ? null : { ...op, id, body };
      }
      case 'folder-del': { const id = map(op.id); return id == null ? null : { ...op, id }; }
      case 'recipes-move': { const f = map(op.folder_id); return f === undefined ? null : { ...op, folder_id: f }; }
      default: return op;
    }
  }

  async function run(): Promise<boolean> {
    while (ops.length) {
      const op = ops[0];
      const ready = resolve(op);
      if (ready) {
        try {
          const res = await sender.send(ready);
          if (op.kind === 'folder-add') {
            const id = (res as { id?: unknown } | null)?.id;
            if (typeof id === 'number') ids[String(op.tmp)] = id;
          }
        } catch (e) {
          if (e instanceof OfflineError) return false;
          // refused for good (the item is gone, the body is stale): drop it, never block the queue on it
        }
      }
      ops.shift();
      save();
    }
    return true;
  }

  /** Send the queue in order, one drain at a time. true = empty now; false = still offline (the rest stays queued).
   *  The guard is cleared in .finally() on the OUTER promise: inside an async function an empty queue finishes
   *  synchronously, and a `finally` there ran before the guard was even set — leaving it stuck forever (found
   *  end-to-end 2026-10-10: after the page's first, empty drain nothing was ever replayed). */
  function drain(): Promise<boolean> {
    if (!draining) draining = run().finally(() => { draining = null; });
    return draining;
  }

  return { push, drain, pending, queued, ops: () => ops.map((o) => ({ ...o })) as Op[] };
}
