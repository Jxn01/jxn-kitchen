// The know-how library on the client: /api/knowhow (cached by the service worker like any GET), page lookup and a
// search over titles and bodies in both languages, accent-folded (tested in knowhow.test.ts).
import { writable } from 'svelte/store';
import { getJSON } from './api';
import { fold } from './search';
import { plainText } from './md';

export interface KPage {
  id: string;
  illustration: string | null /* doneness | sugar | smoke | oven | cuts | blend | balance | onion | angle | cutsizes | press | moka | eggtimer | eggfloat | fridge */;
  chart: KChart | null;       /* an infographic drawn from data — server/kitchen/charts.py validates it */
  open?: 'spices' | 'sauces' | null;   /* a button to that section's engine */
  en: { title: string; body: string };
  hu: { title: string; body: string };
}

// ---- charts (the shapes server/kitchen/charts.py guarantees) ----
/** A text in both languages: one string for both ("1 dl", "°C"), or {en, hu}. */
export type KText = string | { en: string; hu: string };
export const tx = (v: KText, lang: 'en' | 'hu'): string => (typeof v === 'string' ? v : v[lang]);
/** A drawing colour: a palette name or #RRGGBB (never behind text). */
export type KFill = string;
export interface KVessel { type: 'vessel'; shape: 'jug' | 'pot' | 'cup'; max: number; unit?: KText; ticks?: { value: number; label: KText }[];
  items: { value: number; label: KText; note: KText; fill?: KFill; icons?: string[] }[] }
export interface KScale { type: 'scale'; unit: KText; min: number; max: number;
  bands: { from: number; to: number; fill: KFill; label: KText; note: KText; range?: KText }[]; marks?: { value: number; label: KText }[] }
export interface KBoard { type: 'board'; groups: { color: string; label: KText; note?: KText; icon?: string; items: { label: KText; icon?: string }[] }[] }
export interface KSteps { type: 'steps'; items: { label: KText; note: KText; icon?: string; time?: KText }[] }
export interface KBars { type: 'bars'; unit: KText; max: number; marker?: { value: number; label: KText };
  items: { value: number; to?: number; label: KText; note?: KText; fill?: KFill }[] }
export interface KSwatches { type: 'swatches'; shape?: 'spoons' | 'jars'; items: { fill: KFill; label: KText; note: KText; heat?: number; value?: KText }[] }
export interface KLayers { type: 'layers'; shape: 'cup' | 'glass' | 'pot' | 'jar'; unit?: KText;
  items: { label: KText; note: KText; value?: KText; layers: { fill: KFill; part: number; label: KText }[] }[] }
export interface KMatrix { type: 'matrix'; levels: [KText, KText, KText]; cols: { label: KText; icon?: string; note: KText }[];
  rows: { label: KText; icon?: string; cells: (0 | 1 | 2)[] }[] }
export interface KPicker { type: 'picker'; items: { label: KText; note: KText; icon?: string; value?: KText }[] }
export type KChart = KVessel | KScale | KBoard | KSteps | KBars | KSwatches | KLayers | KMatrix | KPicker;
export interface KSection { id: string; icon: string; color: string; en: { title: string; sub: string }; hu: { title: string; sub: string }; pages: KPage[] }
export interface KHit { section: KSection; page: KPage; where: 'title' | 'body'; snippet: string }

export const knowhow = writable<KSection[] | null>(null);
export async function loadKnowhow(): Promise<void> {
  try { knowhow.set(await getJSON<KSection[]>('/api/knowhow')); } catch { /* offline: the SW cache or nothing */ }
}

export function findPage(lib: KSection[], sid: string, pid: string): { section: KSection; page: KPage } | null {
  const section = lib.find((s) => s.id === sid);
  const page = section?.pages.find((p) => p.id === pid);
  return section && page ? { section, page } : null;
}

export function searchKnowhow(lib: KSection[], q: string, lang: 'en' | 'hu', limit = 20): KHit[] {
  const needle = fold(q);
  if (needle.length < 2) return [];
  const other = lang === 'en' ? 'hu' : 'en';
  const titles: KHit[] = [], bodies: KHit[] = [];
  for (const section of lib) for (const page of section.pages) {
    if ([page[lang].title, page[other].title].some((t) => fold(t).includes(needle))) {
      titles.push({ section, page, where: 'title', snippet: plainText(page[lang].body).slice(0, 120) });
      continue;
    }
    for (const l of [lang, other] as const) {
      const text = plainText(page[l].body);
      const at = fold(text).indexOf(needle);
      if (at >= 0) {
        const from = Math.max(0, at - 50);
        bodies.push({ section, page, where: 'body', snippet: (from ? '…' : '') + text.slice(from, at + needle.length + 70) + '…' });
        break;
      }
    }
  }
  return [...titles, ...bodies].slice(0, limit);
}
