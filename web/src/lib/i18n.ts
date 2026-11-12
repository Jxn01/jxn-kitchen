// UI strings (EN/HU) and Budapest-time formatting. Recipes keep their own language; this is only the UI.
import { derived, writable } from 'svelte/store';
import en from '../i18n/en.json';
import hu from '../i18n/hu.json';

export type Lang = 'en' | 'hu';
export const TZ = 'Europe/Budapest';
const DICTS: Record<Lang, Record<string, string>> = { en, hu };
const LS_KEY = 'kitchen.lang';

function initialLang(): Lang {
  try {
    const v = globalThis.localStorage?.getItem(LS_KEY);
    return v === 'hu' ? 'hu' : 'en';
  } catch {
    return 'en';
  }
}

export const lang = writable<Lang>(initialLang());
lang.subscribe((l) => {
  try { globalThis.localStorage?.setItem(LS_KEY, l); } catch { /* private mode: fine */ }
  if (typeof document !== 'undefined') document.documentElement.lang = l;
});

export function interpolate(s: string, params?: Record<string, string | number>): string {
  return params ? s.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m)) : s;
}

/** English needs a singular for some counts ("1 recipe"): a `<key>.one` string is used when params.n === 1.
 *  Hungarian keeps the singular after any number, so it needs no `.one` keys. */
export function translate(l: Lang, key: string, params?: Record<string, string | number>): string {
  const one = params?.n === 1 ? (DICTS[l][`${key}.one`]) : undefined;
  return interpolate(one ?? DICTS[l][key] ?? DICTS.en[key] ?? key, params);
}

export const t = derived(lang, ($l) => (key: string, params?: Record<string, string | number>) => translate($l, key, params));

export function fmtTime(d: Date): string {
  return new Intl.DateTimeFormat('hu-HU', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: TZ }).format(d);
}

export function fmtDate(d: Date, l: Lang): string {
  const opts: Intl.DateTimeFormatOptions = { weekday: 'long', month: 'long', day: 'numeric', timeZone: TZ };
  return new Intl.DateTimeFormat(l === 'hu' ? 'hu-HU' : 'en-US', opts).format(d);
}
