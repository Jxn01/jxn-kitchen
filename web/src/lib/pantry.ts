// Pantry state on the client: optimistic one-tap toggles, reconciled by the server's echo and SSE "pantry" events.
import { derived, get, writable } from 'svelte/store';
import { getJSON, OfflineError, putJSON } from './api';
import { outbox } from './queue';
import type { Cat } from './search';

/** `rev` grows with every write on the server: state with a lower rev than what we hold is stale and dropped. */
export interface PantryState { have: string[]; groups_some: string[]; staples_off: string[]; rev: number }
export interface PantryApi { put(node: string, have: boolean): Promise<PantryState> }

export const restApi: PantryApi = {
  put: (node, have) => putJSON<PantryState>(`/api/pantry/${encodeURIComponent(node)}`, { have }),
};

export function isOn(state: PantryState, node: string): boolean {
  return node.startsWith('group:') ? state.groups_some.includes(node.slice(6)) : state.have.includes(node);
}

function flip(state: PantryState, node: string, have: boolean): PantryState {
  if (node.startsWith('group:')) {
    const g = node.slice(6);
    const groups = state.groups_some.filter((x) => x !== g);
    return { ...state, groups_some: have ? [...groups, g] : groups };
  }
  const items = state.have.filter((x) => x !== node);
  return { ...state, have: have ? [...items, node].sort() : items };
}

export function createPantry(api: PantryApi = restApi, queue: { push: typeof outbox.push } = outbox) {
  const state = writable<PantryState>({ have: [], groups_some: [], staples_off: [], rev: -1 });
  let rev = -1;
  /** The ONE way server state gets in (load, PUT answers, SSE): an answer or event older than what we hold is
   *  dropped — a slow PUT answer must not undo a change the phone made meanwhile. */
  function accept(s: PantryState): void {
    if (typeof s.rev === 'number' && s.rev < rev) return;
    rev = s.rev ?? rev;
    state.set(s);
  }
  return {
    state,
    accept,
    /** Flip one node; resolves to the new `have` value. Rolls back if the write fails. */
    async toggle(node: string, to?: boolean): Promise<boolean> {
      const before = get(state);
      const have = to ?? !isOn(before, node);
      state.set(flip(before, node, have));            // optimistic (rev unchanged)
      try {
        accept(await api.put(node, have));
      } catch (e) {
        if (e instanceof OfflineError) {              // server away: keep the tap, send it when it's back (spec §9)
          queue.push({ kind: 'pantry', node, have });
          return have;
        }
        if (get(state) !== before) state.set(before);
        throw e;
      }
      return have;
    },
  };
}

// the app-wide instances
export const pantry = createPantry();
export const catalogue = writable<Cat | null>(null);

export async function loadPantry(): Promise<void> {
  try {
    const [cat, st] = await Promise.all([getJSON<Cat>('/api/catalogue'), getJSON<PantryState>('/api/pantry')]);
    catalogue.set(cat);
    pantry.accept(st);
  } catch { /* offline: keep what we have (the service worker may have served cached copies) */ }
}

/** "37 things in": items that are in (staples included), plus the "some … somewhere" switches. */
export const haveCount = derived(pantry.state, (s) => s.have.length + s.groups_some.length);
