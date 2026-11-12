// Spices on the client (spec 2026-10-19 §6.2): types, API calls, the editor's evaluator and tray, and the small pure
// helpers the screens share (tested in spices.test.ts). The engine itself is on the server — the web composes no
// sentences: every line it shows arrives in both languages and is only picked by language here.
import { writable } from 'svelte/store';
export { createEvaluator, ledgerFor, ledgerTotal, pool, WORD_COLOR, WORD_FACE, type Word } from './engine';
import { fmtFrac, type Word } from './engine';
import { getJSON, postJSON, putJSON } from './api';
import type { Lang } from './i18n';

export type Bi = { en: string; hu: string };
export interface Jar {
  id: string; label: Bi; name: Bi; fill: string; tag: Bi; heat: number; role: string; timing: 'bloom' | 'during' | 'finish';
  form: string; fragile: boolean; gluten: 'free' | 'label' | 'contains'; g_per_tsp: number; note: Bi | null; page: string | null;
}
export interface Shelf { id: string; en: string; hu: string; jars: Jar[] }
export interface Food { id: string; icon: string; en: string; hu: string }
export interface Labelled { id: string; en: string; hu: string }
export interface Rack {
  shelves: Shelf[]; foods: Food[]; axes: Labelled[]; cuisines: Labelled[]; roles: Labelled[]; timings: Labelled[];
  words: (Labelled & { min: number; mascot: string })[]; heat: (Labelled & { below: number })[];
  classics: (Labelled & { source: string })[]; max_spices: number;
}
export type Kind = 'good' | 'warn' | 'notice' | 'info';
export interface Finding extends Bi { id: string; kind: Kind; weight: number; about: string[] }
export interface Edge extends Bi { a: string; b: string; score: number; reason: string }
export interface Voucher extends Bi { spice: string; score: number }
export interface Classic { id: string; en: string; hu: string; similarity: number; missing: string[]; extra: string[];
  ratios: { spice: string; yours: number; theirs: number }[] }
export interface Gluten extends Bi { status: 'ok' | 'check' | 'yours'; about: string[] }
export interface Evaluation {
  score: number; base: number; word: Word; word_text: Bi; mascot: string; findings: Finding[];
  radar: Record<string, number>; profile: Record<string, number>;
  web: { nodes: { id: string; share: number }[]; edges: Edge[] };
  foods: { id: string; score: number; vouchers: Voucher[] }[];
  timing: { bloom: string[]; during: string[]; finish: string[]; conflict: boolean };
  heat: { value: number; word: string } & Bi;
  classics: Classic[]; cuisines: { id: string; pct: number }[];
  salt_pct: number; sugar_pct: number; jar_fill: string;
  batch: { tbsp: number; tsp: number; grams: { spice: string; tsp: number; g: number }[]; total_g: number };
  suggest: string[]; shares: Record<string, number>; volume: Record<string, number>;
  gluten?: Gluten; seq?: number | null;
}
export interface Part { spice: string; parts: number }
export interface BlendSummary {
  id: number; names: Bi; origin: 'typed' | 'seed' | 'riff'; classic_id: string | null; tags: string[]; parts: Part[];
  score: number | null; word: Word | null; jar_fill: string; heat: string; gluten: Gluten;
  created_at: string; updated_at: string; missing_jars: string[];
}
export interface Blend extends BlendSummary {
  name: string; lang: string; notes: string | null; method: Bi | null; evaluation: Evaluation | null; used_by: { id: number; name: string }[];
}
export interface BlendIn { name: string; notes?: string | null; tags: string[]; parts: Part[] }

export const api = {
  rack: () => getJSON<Rack>('/api/spices'),
  list: () => getJSON<BlendSummary[]>('/api/blends'),
  get: (id: number, batchTbsp?: number) => getJSON<Blend>(`/api/blends/${id}${batchTbsp ? `?batch_tbsp=${batchTbsp}` : ''}`),
  create: (b: BlendIn) => postJSON<{ id: number }>('/api/blends', b),
  update: (id: number, b: BlendIn) => putJSON<Blend>(`/api/blends/${id}`, b),
  riff: (id: number) => postJSON<{ id: number }>(`/api/blends/${id}/riff`, {}),
  evaluate: (parts: Part[], seq: number, batchTbsp?: number) =>
    postJSON<Evaluation>('/api/blends/evaluate', { parts, seq, ...(batchTbsp ? { batch_tbsp: batchTbsp } : {}) }),
  /** 409 when a sauce uses the blend: -> the sauces, so the screen can name them. */
  remove: async (id: number): Promise<{ ok: true } | { ok: false; sauces: { id: number; name: string }[] }> => {
    const res = await fetch(`/api/blends/${id}`, { method: 'DELETE' });
    if (res.status === 409) return { ok: false, sauces: ((await res.json()).detail?.sauces ?? []) };
    if (!res.ok) throw new Error(String(res.status));
    return { ok: true };
  },
};

export const rack = writable<Rack | null>(null);
export const blendList = writable<BlendSummary[]>([]);
export async function loadRack(): Promise<void> { try { rack.set(await api.rack()); } catch { /* offline: the screens wait */ } }
export async function loadBlends(): Promise<void> { try { blendList.set(await api.list()); } catch { /* keep what we have */ } }

/** Every jar by id. */
export function jarIndex(r: Rack | null): Map<string, Jar> {
  return new Map((r?.shelves ?? []).flatMap((s) => s.jars.map((j) => [j.id, j] as const)));
}

export const pick = (b: Bi | null | undefined, l: Lang): string => (b ? b[l] : '');

/** Parts in level teaspoons, as the owner reads them: 1, 1½, ½, 2½ (anything off the half-steps keeps one decimal). */
export const fmtParts = (n: number): string => fmtFrac(n);

export const STEP = 0.5, MIN_PARTS = 0.5, MAX_PARTS = 50;
/** One tap on ± — half-teaspoon steps, never below ½ (drop the jar to remove it) nor above 50. */
export function stepParts(n: number, dir: 1 | -1): number {
  return Math.min(MAX_PARTS, Math.max(MIN_PARTS, Math.round((n + dir * STEP) * 2) / 2));
}

/** The tray: add a jar with 1 part (once — a second tap does nothing), set, drop. Pure: returns the new array. */
export function trayAdd(tray: Part[], spice: string, max = 16): Part[] {
  if (tray.some((p) => p.spice === spice) || tray.length >= max) return tray;
  return [...tray, { spice, parts: 1 }];
}
export function traySet(tray: Part[], spice: string, parts: number): Part[] {
  return tray.map((p) => (p.spice === spice ? { ...p, parts } : p));
}
export function trayDrop(tray: Part[], spice: string): Part[] {
  return tray.filter((p) => p.spice !== spice);
}

/** Pool sizes, from the engine's limits (3000 random blends, 2026-10-19: at most 14 findings, 3 classics and cuisines,
 *  9 missing and 15 extra jars against a classic, 4 vouchers, 14 jars in one timing lane). */
export const SLOTS = { findings: 20, classics: 3, cuisines: 3, chips: 6, vouchers: 4, lane: 16, suggest: 3 } as const;

/** A 100 ml spice jar holds about 20 level teaspoons: how full the batch fills one (the detail page's jar). */
export const JAR_TSP = 20;
/** Grams per jar for a batch of `tbsp` tablespoons — the server's batch rule (parts scaled, × g per tsp). */
export function batchGrams(parts: Part[], jars: Map<string, Jar>, tbsp: number): { spice: string; tsp: number; g: number }[] {
  const total = parts.reduce((n, p) => n + p.parts, 0) || 1;
  const k = (tbsp * 3) / total;
  return parts.map((p) => ({ spice: p.spice, tsp: Math.round(p.parts * k * 100) / 100,
                              g: Math.round(p.parts * k * (jars.get(p.spice)?.g_per_tsp ?? 0) * 10) / 10 }));
}

/** An evaluation with nothing in it — the panel's shape before the first jar (no score, no words: nothing is said). It
 *  lets the panel and every section be BUILT ONCE when the page opens; the first jar then only updates them (creating
 *  the panel on the first tap cost the kiosk a 450 ms frame, 2026-10-19). */
export const EMPTY_EVALUATION: Evaluation = {
  score: 0, base: 50, word: 'muddled', word_text: { en: '', hu: '' }, mascot: 'think', findings: [],
  radar: { warm: 0, earthy: 0, hot: 0, bright: 0, herbal: 0, floral: 0, bitter: 0, savoury: 0 },
  profile: { warm: 0, earthy: 0, hot: 0, bright: 0, herbal: 0, floral: 0, bitter: 0, savoury: 0 },
  web: { nodes: [], edges: [] }, foods: [], timing: { bloom: [], during: [], finish: [], conflict: false },
  heat: { value: 0, word: 'mild', en: '', hu: '' }, classics: [], cuisines: [], salt_pct: 0, sugar_pct: 0,
  jar_fill: '#CCBFA8', batch: { tbsp: 0, tsp: 0, grams: [], total_g: 0 }, suggest: [], shares: {}, volume: {},
};
