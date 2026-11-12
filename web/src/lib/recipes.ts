// Recipes on the client: types, API calls, and the small pure helpers the screens share (tested in recipes.test.ts).
import { derived, get, writable } from 'svelte/store';
import { getJSON, OfflineError, postJSON, putJSON } from './api';
import { outbox } from './queue';
import { loadFolders } from './folders';

export interface Verdict { state: 'gf' | 'swaps' | 'check' | 'unknown' | 'empty'; swaps: number; check: number; unknown: number }
export interface Summary {
  id: number; title: string; image: string | null; minutes: number | null; servings: number | null; tags: string[];
  source_site: string | null; verdict: Verdict; have: number; total: number; missing: number; origin: string; created_at: string;
  missing_names?: string[]; folder_id: number | null;
}
export interface Line {
  pos: number; raw: string; qty_text: string; name: string; note: string | null; item_id: string | null;
  item_name: string | null; how: string | null; gluten: 'ok' | 'yours' | 'swap' | 'check' | 'unknown'; ok_gf: boolean;
  gf_text: string | null; tip: string | null; have: boolean | null; pantry_id: string | null;
}
export interface Step { pos: number; text: string; timers: { start: number; end: number; seconds: number }[] }
export interface Recipe {
  id: number; title: string; lang: string; source_url: string | null; source_site: string | null; image: string | null;
  servings: number; base_servings: number; prep_min: number | null; cook_min: number | null; total_min: number | null;
  notes: string | null; origin: string; tags: string[]; verdict: Verdict; have: number; total: number;
  missing: { item_id: string; name: string }[]; lines: Line[]; steps: Step[]; folder_id: number | null;
}
export interface RecipeIn {
  title: string; servings: number; prep_min?: number | null; cook_min?: number | null; total_min?: number | null;
  ingredients: string[]; steps: string[]; tags: string[]; notes?: string | null; source_url?: string | null;
  folder_id?: number | null;   // create only: the folder the new recipe is filed in (an update keeps its folder)
}

export const api = {
  list: (q = '') => getJSON<Summary[]>(`/api/recipes${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  cookable: () => getJSON<Summary[]>('/api/cookable'),
  get: (id: number, servings?: number) => getJSON<Recipe>(`/api/recipes/${id}${servings ? `?servings=${servings}` : ''}`),
  create: (r: RecipeIn) => postJSON<{ id: number }>('/api/recipes', r),
  update: (id: number, r: RecipeIn) => putJSON<Recipe>(`/api/recipes/${id}`, r),
  remove: async (id: number) => { const res = await fetch(`/api/recipes/${id}`, { method: 'DELETE' }); if (!res.ok) throw new Error(String(res.status)); },
  fixLine: (id: number, pos: number, item_id: string | null, ok_gf: boolean) => putJSON<Recipe>(`/api/recipes/${id}/lines/${pos}`, { item_id, ok_gf }),
  missingToShopping: (id: number) => postJSON<unknown[]>(`/api/recipes/${id}/missing-to-shopping`, {}),
  /** -> {id, draft, code?}; a refused URL throws ImportRefusedError with its code. */
  importUrl: async (url: string): Promise<{ id: number; draft: boolean; code?: string }> => {
    const res = await fetch('/api/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) });
    if (res.status === 422) {
      const d = await res.json().catch(() => ({}));
      throw new ImportRefusedError(typeof d.detail === 'object' && d.detail?.code ? d.detail.code : 'scheme');
    }
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  },
  parse: (lines: string[]) => postJSON<{ raw: string; name: string; qty_text: string; item_id: string | null; item_name: string | null; gluten: Line['gluten']; gf_name: string | null }[]>('/api/parse', { lines }),
  /** A photo or a scanned PDF of a printed recipe -> OCR -> draft(s) (one per PDF page). */
  scan: async (file: Blob): Promise<number[]> => {
    const res = await fetch('/api/scan', { method: 'POST', body: file, headers: { 'Content-Type': file.type || 'application/octet-stream' } });
    if (!res.ok) throw new Error(String(res.status));
    return (await res.json()).ids as number[];
  },
  uploadImage: async (id: number, file: Blob) => {
    const res = await fetch(`/api/recipes/${id}/image`, { method: 'PUT', body: file, headers: { 'Content-Type': file.type || 'application/octet-stream' } });
    if (!res.ok) throw new Error(String(res.status));
    return (await res.json()) as { image: string };
  },
};

/** The line as shown: in the GF view a swapped line shows the GF item, with the original struck through. */
export function lineText(l: Line, gfView: boolean): { text: string; struck: string | null } {
  const original = [l.qty_text, l.name].filter(Boolean).join(' ');
  if (gfView && l.gluten === 'swap' && l.gf_text) return { text: l.gf_text, struck: original };
  return { text: original, struck: null };
}

/** The recipe's gluten badge. "unknown" is never green (spec §7: an unmatched line blocks ✓ GF). */
export function badge(v: Verdict): { kind: Verdict['state']; tone: 'ok' | 'swap' | 'warn' | 'unknown'; n: number } {
  switch (v.state) {
    case 'gf': return { kind: 'gf', tone: 'ok', n: 0 };
    case 'swaps': return { kind: 'swaps', tone: 'swap', n: v.swaps };
    case 'check': return { kind: 'check', tone: 'warn', n: v.check };
    case 'empty': return { kind: 'empty', tone: 'unknown', n: 0 };   // nothing checked: never the ✓ tone
    default: return { kind: 'unknown', tone: 'unknown', n: v.unknown };
  }
}

export type FilterMode = 'all' | 'cook' | 'cookable' | 'quick';
export function filterRecipes(list: Summary[], f: { mode: FilterMode; tag?: string | null }): Summary[] {
  return list.filter((r) =>
    (f.mode !== 'cookable' || (r.total > 0 && r.missing === 0)) &&
    (f.mode !== 'quick' || (r.minutes !== null && r.minutes <= 30)) &&
    (!f.tag || r.tags.includes(f.tag)));
}

export class ImportRefusedError extends Error { constructor(public code: string) { super(code); } }

/** A draft import hands its reason to the editor it opens (spec §9: "the editor opens with the reason shown"). */
export const importDraft = writable<{ id: number; code: string } | null>(null);

export const recipeList = writable<Summary[]>([]);

/** Recipe edits saved on this device and not on the server yet (id → the edit): the editor starts from it, the recipe
 *  screen says so. */
export const pendingEdits = derived(outbox.queued, (ops) =>
  new Map(ops.flatMap((o) => (o.kind === 'recipe-put' ? [[o.id, o.body] as const] : []))));

/** Save an existing recipe: 'done' (the server has it) or 'queued' (saved here, sent at the next reconnect; the last
 *  edit wins). While writes are waiting it joins the queue, which is drained at once — never overtaking them. */
export async function saveRecipe(id: number, body: RecipeIn): Promise<'done' | 'queued'> {
  if (get(outbox.pending) > 0) {
    outbox.push({ kind: 'recipe-put', id, body });
    return (await outbox.drain()) ? 'done' : 'queued';
  }
  try {
    await api.update(id, body);
    return 'done';
  } catch (e) {
    if (!(e instanceof OfflineError)) throw e;
    outbox.push({ kind: 'recipe-put', id, body });
    return 'queued';
  }
}
/** Recipes AND folders: one SSE `recipes` event covers both, so every caller gets both fresh. */
export async function loadRecipes(): Promise<void> {
  await Promise.all([(async () => { try { recipeList.set(await api.list()); } catch { /* offline: keep */ } })(), loadFolders()]);
}
