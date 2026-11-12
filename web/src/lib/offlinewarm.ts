// The kiosk keeps the whole library ready for offline use.
//
// The service worker only ever caches what a screen asked for, so after a long outage a
// recipe nobody had opened since the last deploy would have no steps to show. So the kiosk asks the worker, now and then,
// to fetch every read a screen can make: the start-up lists, every recipe, sauce and blend, every recipe photo. The
// worker does the fetching itself (the 'warm' message, public/sw.js) into its deploy-proof data cache; the page only
// builds the list. Kiosk only: it is the screen on the wall; a phone opens the app through the tailnet anyway.
import { getJSON } from './api';

type WithId = { id: number };
type WithImage = WithId & { image: string | null };

/** Every read a screen makes without parameters. tests/offlinewarm.test.ts fails the build when a screen starts
 *  reading a new `getJSON('/api/…')` path that is neither here nor in UNWARMED. */
export const BASE_READS = [
  '/api/settings', '/api/catalogue', '/api/pantry', '/api/shopping', '/api/timers', '/api/folders', '/api/recipes',
  '/api/cookable', '/api/knowhow', '/api/sauces', '/api/sauces/shelves', '/api/blends', '/api/spices', '/api/weather',
] as const;

/** Reads deliberately left out: live-only answers the worker never caches (strategyFor bypasses them). */
export const UNWARMED = ['/api/health', '/api/kiosk/health', '/api/events'] as const;

/** The URLs one warm-up fetches, in order: the start-up reads, every detail, then the photos (largest, last). */
export function warmUrls(recipes: WithImage[], sauces: WithId[], blends: WithId[]): string[] {
  return [
    ...BASE_READS,
    ...recipes.map((r) => `/api/recipes/${r.id}`),
    ...sauces.map((s) => `/api/sauces/${s.id}`),
    ...blends.map((b) => `/api/blends/${b.id}`),
    ...recipes.flatMap((r) => (r.image ? [r.image] : [])),
  ];
}

export interface WarmOptions {
  /** First run after start (the screens' own loads go first). */
  firstMs?: number;
  /** A run at least this often, to pick up changes made while no event said so. */
  everyMs?: number;
  /** poke() waits this long, so a burst of edits on a phone becomes one run. */
  debounceMs?: number;
}

export interface WarmDeps {
  /** The three lists the URLs are built from. Throws when the server is away (no run then). */
  lists?: () => Promise<[WithImage[], WithId[], WithId[]]>;
  /** Hands the list to the service worker; false when no worker controls the page yet. */
  post?: (msg: { type: 'warm'; urls: string[] }) => boolean;
}

export function startOfflineWarm(opts: WarmOptions = {}, deps: WarmDeps = {}) {
  const { firstMs = 20_000, everyMs = 30 * 60_000, debounceMs = 10_000 } = opts;
  const lists = deps.lists ?? (() => Promise.all([
    getJSON<WithImage[]>('/api/recipes'), getJSON<WithId[]>('/api/sauces'), getJSON<WithId[]>('/api/blends'),
  ]));
  const post = deps.post ?? ((msg) => {
    const sw = typeof navigator !== 'undefined' ? navigator.serviceWorker?.controller : null;
    if (!sw) return false;
    sw.postMessage(msg);
    return true;
  });

  let timer: ReturnType<typeof setTimeout> | null = null;
  async function run(): Promise<void> {
    let got: [WithImage[], WithId[], WithId[]];
    try { got = await lists(); } catch { return; }   // the server is away: the next poke or interval tries again
    post({ type: 'warm', urls: warmUrls(...got) });
  }
  const poke = (ms: number) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { timer = null; void run(); }, ms);
  };
  poke(firstMs);
  const every = setInterval(() => poke(0), everyMs);
  return {
    /** Something changed (a reconnect, an edit elsewhere): warm again soon. */
    poke: () => poke(debounceMs),
    stop: () => { if (timer) clearTimeout(timer); clearInterval(every); },
  };
}
