// The server-side settings, mirrored live (GET once, then SSE "settings" events). The UI language follows them.
import { writable, get } from 'svelte/store';
import { getJSON, OfflineError, putJSON } from './api';
import { outbox } from './queue';
import { lang, type Lang } from './i18n';

export interface Settings {
  language: Lang;
  night_start: number;
  night_end: number;
  idle_minutes: 1 | 2 | 5 | 10;
  sounds: boolean;
  night_brightness: number;
  day_brightness: number;
  browse_sites: string[];
  browse_custom: { name: string; url: string }[];
}

export const DEFAULTS: Settings = {
  language: 'en', night_start: 23, night_end: 6, idle_minutes: 2, sounds: true, night_brightness: 20, day_brightness: 80,
  browse_sites: ['nosalty', 'streetkitchen', 'mindmegette', 'receptneked'], browse_custom: [],
};

export const settings = writable<Settings>({ ...DEFAULTS, language: get(lang) });

export function apply(s: Settings): void {
  settings.set(s);
  lang.set(s.language);
}

export async function load(): Promise<void> {
  try { apply(await getJSON<Settings>('/api/settings')); } catch { /* offline: keep defaults/cache */ }
}

export async function save(patch: Partial<Settings>): Promise<void> {
  settings.update((s) => ({ ...s, ...patch }));                 // optimistic: the screen reacts at once
  if (patch.language) lang.set(patch.language);
  // offline (2026-11-12): the change is queued (one merged patch) and sent at the next reconnect, before the reload —
  // until then a change made offline was overwritten by the server's old settings on reconnect. While writes are
  // waiting it joins the queue, which is drained at once.
  if (get(outbox.pending) > 0) { outbox.push({ kind: 'settings', patch }); void outbox.drain(); return; }
  try { apply(await putJSON<Settings>('/api/settings', patch)); } catch (e) {
    if (e instanceof OfflineError) outbox.push({ kind: 'settings', patch });
    // refused (422): the next load or SSE event puts the server's settings back
  }
}
