// Folder writes that keep working offline. Each tries the server first; when it is
// away (OfflineError) the change is made to the local lists at once — the same way the server would make it — and
// queued in the outbox (lib/outbox.ts), which replays it at the next reconnect; App.svelte then reloads the truth.
// A folder created offline has a temporary negative id until then (the outbox rewrites it in every later op).
// Any other refusal (a name taken, a cycle, too deep) still throws, for the screen's message (folders.ts refusalKey).
import { get } from 'svelte/store';
import { OfflineError } from './api';
import { folderApi, folderList, type Folder } from './folders';
import { outbox } from './queue';
import { tmpId, type FolderBody } from './outbox';
import { loadRecipes, recipeList, type Summary } from './recipes';

/** 'done' = the server has it; 'queued' = saved here, sent at the next reconnect. */
export type Outcome = 'done' | 'queued';

/** `recipes` and `folders` (direct children) recounted from the lists — what the server would answer. */
export function recount(list: Folder[], recipes: Pick<Summary, 'folder_id'>[]): Folder[] {
  return list.map((f) => ({
    ...f,
    folders: list.filter((x) => x.parent_id === f.id).length,
    recipes: recipes.filter((r) => r.folder_id === f.id).length,
  }));
}

export function localCreate(list: Folder[], id: number, name: string, parent_id: number | null, now: string): Folder[] {
  return [...list, { id, name, parent_id, recipes: 0, folders: 0, created_at: now, updated_at: now }];
}

export function localPatch(list: Folder[], id: number, body: FolderBody, now: string): Folder[] {
  return list.map((f) => (f.id === id ? { ...f, ...body, updated_at: now } : f));
}

/** The server's delete: the folder goes, its recipes and subfolders move up into its parent. */
export function localDelete(list: Folder[], recipes: Summary[], id: number): { list: Folder[]; recipes: Summary[] } {
  const gone = list.find((f) => f.id === id);
  if (!gone) return { list, recipes };
  const parent = gone.parent_id;
  return {
    list: list.filter((f) => f.id !== id).map((f) => (f.parent_id === id ? { ...f, parent_id: parent } : f)),
    recipes: recipes.map((r) => (r.folder_id === id ? { ...r, folder_id: parent } : r)),
  };
}

export function localMoveRecipes(recipes: Summary[], ids: number[], folder_id: number | null): Summary[] {
  const set = new Set(ids);
  return recipes.map((r) => (set.has(r.id) ? { ...r, folder_id } : r));
}

function commit(list: Folder[], recipes: Summary[] = get(recipeList)): void {
  recipeList.set(recipes);
  folderList.set(recount(list, recipes));
}

/** Online first — unless writes are already waiting: then this one joins the back of the queue and the queue is
 *  drained at once, so the server always gets them in the order they were made (an online write must never be
 *  overtaken later by an older one replayed from the queue). */
async function attempt(online: () => Promise<unknown>, offline: () => void): Promise<Outcome> {
  if (get(outbox.pending) > 0) {
    offline();
    if (!(await outbox.drain())) return 'queued';
    await loadRecipes();
    return 'done';
  }
  try {
    await online();
  } catch (e) {
    if (!(e instanceof OfflineError)) throw e;
    offline();
    return 'queued';
  }
  await loadRecipes();
  return 'done';
}

const nowIso = () => new Date().toISOString();

export const folders = {
  /** Returns the new folder's id: the server's, or a temporary one while offline. */
  async create(name: string, parent_id: number | null): Promise<{ outcome: Outcome; id: number }> {
    let id = 0;
    const outcome = await attempt(
      async () => { id = (await folderApi.create(name, parent_id)).id; },
      () => {
        id = tmpId();
        outbox.push({ kind: 'folder-add', tmp: id, name, parent_id });
        commit(localCreate(get(folderList), id, name, parent_id, nowIso()));
      },
    );
    return { outcome, id };
  },
  rename: (id: number, name: string) => attempt(() => folderApi.rename(id, name), () => {
    outbox.push({ kind: 'folder-patch', id, body: { name } });
    commit(localPatch(get(folderList), id, { name }, nowIso()));
  }),
  move: (id: number, parent_id: number | null) => attempt(() => folderApi.move(id, parent_id), () => {
    outbox.push({ kind: 'folder-patch', id, body: { parent_id } });
    commit(localPatch(get(folderList), id, { parent_id }, nowIso()));
  }),
  remove: (id: number) => attempt(() => folderApi.remove(id), () => {
    outbox.push({ kind: 'folder-del', id });
    const next = localDelete(get(folderList), get(recipeList), id);
    commit(next.list, next.recipes);
  }),
  moveRecipes: (ids: number[], folder_id: number | null) => attempt(() => folderApi.moveRecipes(ids, folder_id), () => {
    outbox.push({ kind: 'recipes-move', ids, folder_id });
    commit(get(folderList), localMoveRecipes(get(recipeList), ids, folder_id));
  }),
};

