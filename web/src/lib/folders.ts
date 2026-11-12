// Recipe folders on the client (server: folders.py). The server keeps the rules (unique sibling names, no cycles, depth
// cap, deleting never deletes a recipe); this holds the list and the pure tree helpers the screens share (folders.test.ts).
import { writable } from 'svelte/store';
import { ApiError, del, failKey, getJSON, patchJSON, postJSON } from './api';

export interface Folder {
  id: number; name: string; parent_id: number | null; recipes: number; folders: number; created_at: string; updated_at: string;
}
/** One line of the folder picker: a folder with its depth (0 = top-level folder) in tree order. */
export interface TreeRow { folder: Folder; depth: number }

export const MAX_NAME = 60;

export const folderApi = {
  list: () => getJSON<Folder[]>('/api/folders'),
  create: (name: string, parent_id: number | null) => postJSON<Folder>('/api/folders', { name, parent_id }),
  rename: (id: number, name: string) => patchJSON<Folder>(`/api/folders/${id}`, { name }),
  move: (id: number, parent_id: number | null) => patchJSON<Folder>(`/api/folders/${id}`, { parent_id }),
  remove: (id: number) => del(`/api/folders/${id}`),
  /** File recipes into a folder; null = the top level. */
  moveRecipes: (ids: number[], folder_id: number | null) => postJSON<{ moved: number }>('/api/recipes/move', { ids, folder_id }),
};

/** Why the server refused a folder write: 'taken' | 'cycle' | 'depth' | 'name', or null (offline, anything else). */
export function refusal(e: unknown): 'taken' | 'cycle' | 'depth' | 'name' | null {
  if (!(e instanceof ApiError)) return null;
  if (e.status === 422) return 'name';
  const c = e.code;
  return c === 'taken' || c === 'cycle' || c === 'depth' ? c : null;
}

/** The message key for a failed folder write: the server's reason when it gave one, else failKey (offline: "needs a
 *  connection"; anything else: the generic error). */
export function refusalKey(e: unknown): string {
  const r = refusal(e);
  return r ? `folders.err.${r}` : failKey(e);
}

export const folderList = writable<Folder[]>([]);
/** True once the list has come from the server at least once: before that, an unknown folder id proves nothing. */
export const foldersLoaded = writable(false);
export async function loadFolders(): Promise<void> {
  try { folderList.set(await folderApi.list()); foldersLoaded.set(true); } catch { /* offline: keep */ }
}

/** Folders directly inside `parent` (null = the top level), in the server's name order. */
export function childrenOf(list: Folder[], parent: number | null): Folder[] {
  return list.filter((f) => f.parent_id === parent);
}

/** Top level down to `id` itself: [] for the top level, [] for an unknown id. */
export function pathOf(list: Folder[], id: number | null): Folder[] {
  const by = new Map(list.map((f) => [f.id, f]));
  const out: Folder[] = [];
  let cur = id === null ? undefined : by.get(id);
  while (cur && out.length <= list.length) { out.unshift(cur); cur = cur.parent_id === null ? undefined : by.get(cur.parent_id); }
  return out;
}

/** `id` and every folder below it — where `id` itself may not be moved. */
export function subtree(list: Folder[], id: number): Set<number> {
  const out = new Set<number>([id]);
  for (let grew = true; grew;) {
    grew = false;
    for (const f of list) if (f.parent_id !== null && out.has(f.parent_id) && !out.has(f.id)) { out.add(f.id); grew = true; }
  }
  return out;
}

/** Every folder, depth first, siblings in name order: the picker's rows. */
export function treeRows(list: Folder[]): TreeRow[] {
  const out: TreeRow[] = [];
  const walk = (parent: number | null, depth: number) => {
    for (const f of childrenOf(list, parent)) { out.push({ folder: f, depth }); walk(f.id, depth + 1); }
  };
  walk(null, 0);
  return out;
}

/** "Levesek › Magyar": a folder's place, for a recipe found by search outside the folder being looked at. */
export function pathLabel(list: Folder[], id: number | null): string {
  return pathOf(list, id).map((f) => f.name).join(' › ');
}
