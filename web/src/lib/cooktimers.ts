// Kitchen timers on the client. The server owns them (every screen and the phone see the same ones);
// this mirrors its list (load + SSE "timers") and counts down locally from the server's `remaining` at the moment the
// list arrived — so a device whose clock is off still shows the right time. The 1 s tick only runs while a timer does.
//
// Offline: a timer RINGS when its local countdown passes zero, not only when the server says `done` —
// until then a timer running when the network dropped reached 0:00 on the kiosk and stayed silent. Stop silences at
// once and is remembered (localStorage) until the server has it, replayed at the next reconnect (App.svelte). A list
// the service worker served from its cache counts down from `ends_at` (its `remaining` is as old as the copy).
import { derived, get, readable, writable, type Readable } from 'svelte/store';
import { tmpId } from './outbox';
import { ApiError, del, getJSONWithAge, OfflineError, patchJSON, postJSON } from './api';

export interface ServerTimer {
  id: number; label: string; seconds: number; state: 'running' | 'paused' | 'done'; remaining: number;
  ends_at: string | null; recipe_id: number | null; step_pos: number | null;
}
export interface Timer extends ServerTimer { endsLocal: number | null }

/** `stale`: the list is the worker's cached copy, so `remaining` is as old as that copy — count down from `ends_at`
 *  on this device's clock instead (offline there is no other clock). A fresh list ignores `ends_at`: the device's
 *  clock may be off, the server's `remaining` is not. */
export function localTimers(list: ServerTimer[], receivedAt: number, stale = false): Timer[] {
  return list.map((t) => {
    if (t.state !== 'running') return { ...t, endsLocal: null };
    const fromEnd = stale && t.ends_at ? Date.parse(t.ends_at) : NaN;
    return { ...t, endsLocal: Number.isFinite(fromEnd) ? fromEnd : receivedAt + t.remaining * 1000 };
  });
}

/** Seconds left, as of `nowMs`. */
export function left(t: Timer, nowMs: number): number {
  if (t.state !== 'running' || t.endsLocal === null) return t.remaining;
  return Math.max(0, Math.ceil((t.endsLocal - nowMs) / 1000));
}

export function fmtTime(s: number): string {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  return h ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
}

// ---- offline timers ------------------------------------------------------------------------------------
// Starting, pausing, resuming, "+ time" and removing work with the server away: the change is made to a LOCAL copy of
// the timer (an override, kept in localStorage), which counts down and rings here like any other. A timer started
// offline has a temporary negative id. At the next reconnect `flushOfflineTimers` hands each override to the server as
// it stands THEN: a server timer changed offline is replaced (deleted, then created again with what is left, paused
// again if it was), so it ends when it ended here; a timer that already rang here is not created again. The phone's
// push for a timer started offline therefore comes only once the kiosk is back online.
export interface Override extends Timer { removed?: boolean }
const OVERRIDES_KEY = 'kitchen.timers.offline';
function readOverrides(): Record<string, Override> {
  try { const o = JSON.parse(localStorage.getItem(OVERRIDES_KEY) ?? '{}'); return o && typeof o === 'object' ? o : {}; }
  catch { return {}; }
}
export const offlineTimers = writable<Record<string, Override>>(readOverrides());
function setOverrides(next: Record<string, Override>): void {
  offlineTimers.set(next);
  try { localStorage.setItem(OVERRIDES_KEY, JSON.stringify(next)); } catch { /* storage off: this session only */ }
}

/** The server's list with this device's offline changes on top. */
export function merge(server: Timer[], over: Record<string, Override>): Timer[] {
  return [
    ...server.filter((t) => !(String(t.id) in over)),
    ...Object.values(over).filter((o) => !o.removed).map(({ removed: _r, ...t }) => t),
  ];
}

/** What an action does to a timer, the server's way (cooktimers.py act): `add` on a done timer — or one that rang
 *  here while offline — restarts it for that long. */
export function applyLocal(t: Timer, action: 'pause' | 'resume' | 'add', seconds: number, now: number): Timer {
  const rem = left(t, now);
  const rang = t.state === 'done' || (t.state === 'running' && rem <= 0);
  if (action === 'pause') return t.state === 'running' && !rang ? { ...t, state: 'paused', remaining: rem, endsLocal: null, ends_at: null } : t;
  if (action === 'resume') return t.state === 'paused' ? { ...t, state: 'running', endsLocal: now + t.remaining * 1000, ends_at: new Date(now + t.remaining * 1000).toISOString() } : t;
  if (rang) return { ...t, state: 'running', remaining: seconds, endsLocal: now + seconds * 1000, ends_at: new Date(now + seconds * 1000).toISOString() };
  if (t.state === 'paused') return { ...t, remaining: t.remaining + seconds };
  const ends = (t.endsLocal ?? now) + seconds * 1000;
  return { ...t, endsLocal: ends, ends_at: new Date(ends).toISOString() };
}

const serverTimers = writable<Timer[]>([]);
export const timers: Readable<Timer[]> = derived([serverTimers, offlineTimers], ([s, o]) => merge(s, o));
export function acceptTimers(list: ServerTimer[], stale = false): void { serverTimers.set(localTimers(list, Date.now(), stale)); }
export async function loadTimers(): Promise<void> {
  try {
    const { data, stale } = await getJSONWithAge<ServerTimer[]>('/api/timers');
    acceptTimers(data, stale);
  } catch { /* offline with nothing cached: keep */ }
}

const anyRunning = derived(timers, (ts) => ts.some((t) => t.state === 'running'));
/** Now, ticking once a second — but only while a timer runs (the kiosk's CPU budget). */
export const tick: Readable<number> = readable(Date.now(), (set) => {
  let id: ReturnType<typeof setInterval> | null = null;
  const stop = anyRunning.subscribe((on) => {
    if (on && !id) id = setInterval(() => set(Date.now()), 1000);
    if (!on && id) { clearInterval(id); id = null; }
    set(Date.now());
  });
  return () => { stop(); if (id) clearInterval(id); };
});
/** Timers stopped on this device that the server has not been told about yet (it may be away). */
const DISMISSED_KEY = 'kitchen.timers.dismissed';
function readDismissed(): Set<number> {
  try { return new Set((JSON.parse(localStorage.getItem(DISMISSED_KEY) ?? '[]') as unknown[]).filter((x): x is number => typeof x === 'number')); }
  catch { return new Set(); }
}
export const pendingDismiss = writable<Set<number>>(readDismissed());
function setDismissed(next: Set<number>): void {
  pendingDismiss.set(next);
  try { localStorage.setItem(DISMISSED_KEY, JSON.stringify([...next])); } catch { /* storage off: this session only */ }
}

/** The alarm: what the server says is done, AND what this device counted down past zero (the server may be away),
 *  minus what was stopped here. */
export function due(ts: Timer[], now: number, stopped: Set<number>): Timer[] {
  return ts.filter((t) => !stopped.has(t.id)
    && (t.state === 'done' || (t.state === 'running' && t.endsLocal !== null && t.endsLocal <= now)));
}
// Recomputed every second while a timer runs, but only PUBLISHED when the set of ringing timers changes: the alarm
// screen re-renders on every publish, and the kiosk's CPU budget is small.
export const doneTimers: Readable<Timer[]> = readable<Timer[]>([], (set) => {
  let key: string | null = null;   // null: the first computation after (re)subscribing always publishes
  return derived([timers, tick, pendingDismiss], (v) => v).subscribe(([ts, now, stopped]) => {
    const next = due(ts, now, stopped);
    const k = next.map((t) => `${t.id}:${t.state}:${t.label}`).join(',');
    if (k !== key) { key = k; set(next); }
  });
});

/** Stop ringing now; tell the server now or at the next reconnect. A timer changed or started offline is settled in
 *  its override instead (one started offline simply goes; a server one is deleted at the next flush). */
export function dismissTimers(ids: number[]): void {
  const over = { ...get(offlineTimers) };
  const next = new Set(get(pendingDismiss));
  let changed = false;
  for (const id of ids) {
    if (id < 0) { delete over[String(id)]; changed = true; }
    else if (String(id) in over) { over[String(id)] = { ...over[String(id)], removed: true }; changed = true; }
    else next.add(id);
  }
  if (changed) { setOverrides(over); void flushOfflineTimers(); }
  setDismissed(next);
  void flushDismissals();
}

/** Tell the server about every stop it has not heard of. A 404 (the timer is gone already) counts as told; the first
 *  network failure stops the run (the next reconnect tries again). */
export async function flushDismissals(send = (id: number) => patchJSON(`/api/timers/${id}`, { action: 'dismiss' })): Promise<void> {
  for (const id of [...get(pendingDismiss)]) {
    try { await send(id); }
    catch (e) { if (!(e instanceof ApiError && e.status === 404)) return; }
    const next = new Set(get(pendingDismiss));
    next.delete(id);
    setDismissed(next);
  }
}

export interface TimerSender {
  create(body: { label: string; seconds: number; recipe_id?: number; step_pos?: number }): Promise<ServerTimer>;
  act(id: number, body: { action: string; seconds?: number }): Promise<unknown>;
  remove(id: number): Promise<unknown>;
}
const serverSend: TimerSender = {
  create: (b) => postJSON<ServerTimer>('/api/timers', b),
  act: (id, b) => patchJSON(`/api/timers/${id}`, b),
  remove: (id) => del(`/api/timers/${id}`),
};
const gone404 = (e: unknown) => e instanceof ApiError && e.status === 404;

/** Hand every offline change to the server, as it stands now. The first network failure stops the run (the next
 *  reconnect tries again); a refusal drops that override; a timer that rang here stays local until it is stopped. */
let flushing: Promise<void> | null = null;
export function flushOfflineTimers(send: TimerSender = serverSend, now: () => number = Date.now): Promise<void> {
  if (!flushing) flushing = runFlush(send, now).finally(() => { flushing = null; });
  return flushing;
}
async function runFlush(send: TimerSender, now: () => number): Promise<void> {
  for (const [key, o] of Object.entries(get(offlineTimers))) {
    const id = Number(key);
    const rem = left(o, now());
    const rang = o.state === 'done' || (o.state === 'running' && rem <= 0);
    if (!o.removed && rang) continue;
    try {
      if (id > 0) await send.remove(id).catch((e) => { if (!gone404(e)) throw e; });
      if (!o.removed) {
        const body = { label: o.label, seconds: Math.max(1, o.state === 'paused' ? o.remaining : rem),
                       ...(o.recipe_id != null ? { recipe_id: o.recipe_id } : {}), ...(o.step_pos != null ? { step_pos: o.step_pos } : {}) };
        const made = await send.create(body);
        if (o.state === 'paused') await send.act(made.id, { action: 'pause' });
      }
    } catch (e) {
      if (e instanceof OfflineError) return;
      // refused (a body the server no longer takes): drop it rather than block every later one
    }
    const next = { ...get(offlineTimers) };
    delete next[key];
    setOverrides(next);
  }
}

/** The current view of one timer (server or offline copy). */
const current = (id: number) => get(timers).find((t) => t.id === id);

function changeLocal(id: number, action: 'pause' | 'resume' | 'add', seconds: number): void {
  const t = current(id);
  if (!t) return;
  setOverrides({ ...get(offlineTimers), [String(id)]: applyLocal(t, action, seconds, Date.now()) });
}
function removeLocal(id: number): void {
  const over = { ...get(offlineTimers) };
  if (id < 0) delete over[String(id)];
  else { const t = current(id); if (t) over[String(id)] = { ...t, removed: true }; }
  setOverrides(over);
}

/** Every timer write. Online it goes to the server; with the server away (OfflineError) — or while this timer already
 *  has an offline copy waiting — it is made locally and replayed at the next reconnect. Other refusals still throw. */
export const timerApi = {
  async start(label: string, seconds: number, recipe_id?: number, step_pos?: number): Promise<void> {
    try {
      await postJSON<ServerTimer>('/api/timers', { label, seconds, recipe_id, step_pos });
    } catch (e) {
      if (!(e instanceof OfflineError)) throw e;
      const now = Date.now();
      const id = tmpId();
      setOverrides({ ...get(offlineTimers), [String(id)]: {
        id, label, seconds, state: 'running', remaining: seconds, ends_at: new Date(now + seconds * 1000).toISOString(),
        recipe_id: recipe_id ?? null, step_pos: step_pos ?? null, endsLocal: now + seconds * 1000 } });
      return;
    }
    await loadTimers();
  },
  async act(id: number, action: 'pause' | 'resume' | 'add' | 'dismiss', seconds = 60): Promise<void> {
    if (action === 'dismiss') { dismissTimers([id]); return; }
    if (id < 0 || String(id) in get(offlineTimers)) { changeLocal(id, action, seconds); return; }
    try {
      await patchJSON(`/api/timers/${id}`, { action, seconds });
    } catch (e) {
      if (!(e instanceof OfflineError)) throw e;
      changeLocal(id, action, seconds);
      return;
    }
    await loadTimers();
  },
  async remove(id: number): Promise<void> {
    if (id < 0 || String(id) in get(offlineTimers)) { removeLocal(id); return; }
    try {
      await del(`/api/timers/${id}`);
    } catch (e) {
      if (!(e instanceof OfflineError)) throw e;
      removeLocal(id);
      return;
    }
    await loadTimers();
  },
};
