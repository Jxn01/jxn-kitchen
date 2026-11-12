// Hash router: #/, #/idle, #/settings, #/recipes[/<folder id>], #/recipe/new[?folder=<id>], #/soon/<section>, #/spices[/new | /<id>[/edit]], #/sauces[/new | /<id>[/edit]],
// #/cook/<recipe id>, #/cook/sauce/<id> … Unknown routes fall back to home.
import { writable } from 'svelte/store';

export type Route =
  | { name: 'home' }
  | { name: 'idle' }
  | { name: 'settings' }
  | { name: 'mascot-lab'; query: string }
  | { name: 'soon'; param: string }
  | { name: 'pantry' }
  | { name: 'pantry-cat'; param: string; sub?: string }
  | { name: 'pantry-have' }
  | { name: 'shopping' }
  | { name: 'recipes'; folder: number | null }
  | { name: 'recipe'; id: number }
  | { name: 'recipe-edit'; id: number | null; folder?: number | null }
  | { name: 'cook'; id: number; servings: number | null }
  | { name: 'browse' }
  | { name: 'timers' }
  | { name: 'knowhow' }
  | { name: 'knowhow-section'; sid: string; pid: string | null }
  | { name: 'add'; url: string }
  | { name: 'spices' }
  | { name: 'blend'; id: number }
  | { name: 'blend-edit'; id: number | null }
  | { name: 'sauces' }
  | { name: 'sauce'; id: number }
  | { name: 'sauce-edit'; id: number | null }
  | { name: 'cook-sauce'; id: number };

export function parse(hash: string): Route {
  const [path, query = ''] = hash.replace(/^#\/?/, '').split('?');
  const parts = path.split('/').filter(Boolean);
  if (parts[0] === 'browse' && parts.length === 1) return { name: 'browse' };
  if (parts[0] === 'spices' && parts.length === 1) return { name: 'spices' };
  if (parts[0] === 'spices' && parts[1] === 'new' && parts.length === 2) return { name: 'blend-edit', id: null };
  const bid = Number(parts[1]);
  if (parts[0] === 'spices' && Number.isInteger(bid) && bid > 0) {
    if (parts.length === 2) return { name: 'blend', id: bid };
    if (parts.length === 3 && parts[2] === 'edit') return { name: 'blend-edit', id: bid };
  }
  if (parts[0] === 'sauces' && parts.length === 1) return { name: 'sauces' };
  if (parts[0] === 'sauces' && parts[1] === 'new' && parts.length === 2) return { name: 'sauce-edit', id: null };
  if (parts[0] === 'sauces' && Number.isInteger(bid) && bid > 0) {
    if (parts.length === 2) return { name: 'sauce', id: bid };
    if (parts.length === 3 && parts[2] === 'edit') return { name: 'sauce-edit', id: bid };
  }
  const sid = Number(parts[2]);
  if (parts[0] === 'cook' && parts[1] === 'sauce' && parts.length === 3 && Number.isInteger(sid) && sid > 0) return { name: 'cook-sauce', id: sid };
  if (parts[0] === 'timers' && parts.length === 1) return { name: 'timers' };
  if (parts[0] === 'knowhow' && parts.length === 1) return { name: 'knowhow' };
  if (parts[0] === 'knowhow' && (parts.length === 2 || parts.length === 3)) return { name: 'knowhow-section', sid: parts[1], pid: parts[2] ?? null };
  if (parts[0] === 'add' && parts.length === 1) return { name: 'add', url: new URLSearchParams(query).get('url') ?? '' };
  if (parts[0] === 'idle' && parts.length === 1) return { name: 'idle' };
  if (parts[0] === 'settings' && parts.length === 1) return { name: 'settings' };
  if (parts[0] === 'lab' && parts[1] === 'mascot' && parts.length === 2) return { name: 'mascot-lab', query };
  if (parts[0] === 'soon' && parts.length === 2) return { name: 'soon', param: parts[1] };
  if (parts[0] === 'pantry' && parts.length === 1) return { name: 'pantry' };
  if (parts[0] === 'pantry' && parts.length === 2) return { name: 'pantry-cat', param: parts[1] };
  if (parts[0] === 'pantry' && parts.length === 3) return { name: 'pantry-cat', param: parts[1], sub: parts[2] };
  if (parts[0] === 'pantry-have' && parts.length === 1) return { name: 'pantry-have' };
  if (parts[0] === 'shopping' && parts.length === 1) return { name: 'shopping' };
  if (parts[0] === 'recipes' && parts.length === 1) return { name: 'recipes', folder: null };
  const fid = Number(parts[1]);
  if (parts[0] === 'recipes' && parts.length === 2 && Number.isInteger(fid) && fid > 0) return { name: 'recipes', folder: fid };
  if (parts[0] === 'recipe' && parts[1] === 'new' && parts.length === 2) {
    const f = Number(new URLSearchParams(query).get('folder'));
    return { name: 'recipe-edit', id: null, folder: Number.isInteger(f) && f > 0 ? f : null };
  }
  const id = Number(parts[1]);
  if (parts[0] === 'recipe' && Number.isInteger(id) && id > 0) {
    if (parts.length === 2) return { name: 'recipe', id };
    if (parts.length === 3 && parts[2] === 'edit') return { name: 'recipe-edit', id };
  }
  if (parts[0] === 'cook' && parts.length === 2 && Number.isInteger(id) && id > 0) {
    const sv = Number(new URLSearchParams(query).get('servings'));
    return { name: 'cook', id, servings: Number.isInteger(sv) && sv > 0 && sv <= 50 ? sv : null };
  }
  return { name: 'home' };
}

const hasWindow = typeof window !== 'undefined';
export const route = writable<Route>(parse(hasWindow ? window.location.hash : ''));
if (hasWindow) window.addEventListener('hashchange', () => route.set(parse(window.location.hash)));

/** Navigate. `replace` swaps the current history entry (no hashchange fires for that, so the route is set here). */
export function go(path: string, opts: { replace?: boolean } = {}): void {
  if (!hasWindow) return;
  const hash = path.startsWith('#') ? path : `#${path}`;
  if (opts.replace) {
    history.replaceState(history.state, '', hash);
    route.set(parse(hash));
  } else {
    window.location.hash = hash;
  }
}
