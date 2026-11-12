// What both engines' screens share: the fixed pool every engine-filled list is drawn
// through, and the editor's evaluator (debounced, sequenced, stale answers dropped). Tested in spices.test.ts and
// sauces.test.ts.
import { writable } from 'svelte/store';
import { OfflineError } from './api';
import type { Lang } from './i18n';

/**
 * A list as a FIXED POOL of slots: the list, then nulls up to `n` (never shorter than the list — nothing is dropped).
 * Every list the engine fills is drawn through one: the screen renders every slot, keyed by its place, and hides the
 * empty ones, so an answer only fills slots and never builds a row. Rows built on a tap — the first time a list grew
 * past its longest yet — were the kiosk's slowest frames (84 ms).
 */
export function pool<T>(list: readonly T[], n: number): (T | null)[] {
  return list.length >= n ? [...list] : [...list, ...Array<null>(n - list.length).fill(null)];
}
/**
 * The editor's evaluator: the request goes 300 ms after the last change, each carries a rising `seq`, and an answer
 * older than the newest request is dropped (a slow answer must never overwrite a newer blend or sauce). An empty tray
 * answers null at once.
 */
export function createEvaluator<P extends object, E>(
  send: (parts: P[], seq: number) => Promise<E>,
  onResult: (e: E | null) => void,
  opts: { delay?: number; setTimeout?: (fn: () => void, ms: number) => unknown; clearTimeout?: (h: unknown) => void } = {},
) {
  const delay = opts.delay ?? 300;
  const set = opts.setTimeout ?? ((fn: () => void, ms: number) => setTimeout(fn, ms));
  const clear = opts.clearTimeout ?? ((h: unknown) => clearTimeout(h as ReturnType<typeof setTimeout>));
  let seq = 0, latest = 0, timer: unknown = null, inflight = 0;
  const state = writable(false);
  return {
    busy: { subscribe: state.subscribe },
    schedule(parts: P[]) {
      if (timer !== null) clear(timer);
      timer = null;
      if (!parts.length) { latest = ++seq; onResult(null); return; }
      const snapshot = parts.map((p) => ({ ...p }));
      timer = set(() => {
        timer = null;
        const s = ++seq;
        latest = s;
        inflight++; state.set(true);
        send(snapshot, s).then((e) => { if (s === latest) onResult(e); })
          // offline: the last good answer stays on screen. Refused (a 4xx — a sauce whose lines are all typed weighs
          // nothing, 422): there is nothing to say about this tray, so the panel clears instead of showing an old verdict
          .catch((err) => { if (s === latest && !(err instanceof OfflineError)) onResult(null); })
          .finally(() => { inflight--; if (!inflight) state.set(false); });
      }, delay);
    },
    cancel() { if (timer !== null) clear(timer); timer = null; latest = ++seq; },
  };
}

/** The verdict words both engines use. */
export type Word = 'sings' | 'good' | 'muddled' | 'fighting';
/** The verdict word's colour (ink text on all of them, palette ≥ 7:1). */
export const WORD_COLOR: Record<Word, string> = { sings: 'herb', good: 'leaf', muddled: 'butter', fighting: 'tomato' };
/** The mascot's face for a word, and the one reaction it plays when the word changes. */
export const WORD_FACE: Record<Word, { expr: 'proud' | 'happy' | 'focus' | 'worried'; act: string }> = {
  sings: { expr: 'proud', act: 'celebrate' }, good: { expr: 'happy', act: 'nod' },
  muddled: { expr: 'focus', act: 'think' }, fighting: { expr: 'worried', act: 'worried' },
};

/** A ledger line, as both engines write it: the points it moves and the ids it is about. */
export interface LedgerLine { id: string; weight: number; about: string[] }
/** The ledger as the editor shows it: optionally only the lines about one jar or item (a tapped tray line). */
export function ledgerFor<F extends LedgerLine>(findings: F[], about: string | null): F[] {
  return about ? findings.filter((f) => f.about.includes(about)) : findings;
}
/** The sum the ring shows is the ledger's: base 50 + every weight, clamped (the server's rule, checked here too). */
export function ledgerTotal(e: { base: number; findings: LedgerLine[] }): number {
  return Math.max(0, Math.min(100, e.base + e.findings.reduce((n, f) => n + f.weight, 0)));
}

const VULGAR: [number, string][] = [[0.25, '¼'], [0.5, '½'], [0.75, '¾']];
/** A spoon amount as a cook writes it: 1, 1½, ¼, 2¾ — anything off the quarters keeps one decimal, with the language's
 *  decimal mark (0.3 / 0,3). */
export function fmtFrac(n: number, l: Lang = 'en'): string {
  const whole = Math.floor(n + 1e-9), frac = n - whole;
  if (Math.abs(frac) < 1e-6) return String(whole);
  const v = VULGAR.find(([x]) => Math.abs(frac - x) < 1e-6);
  if (v) return whole ? `${whole}${v[1]}` : v[1];
  return n.toLocaleString(l === 'hu' ? 'hu-HU' : 'en', { maximumFractionDigits: 1 });
}
