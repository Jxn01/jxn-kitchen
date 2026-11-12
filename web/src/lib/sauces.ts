// Sauces on the client (spec 2026-10-19 §6.3): types, API calls, the editor's tray and units, and the small pure
// helpers the sauce screens share (tested in sauces.test.ts). The engine is on the server — the web composes no
// sentences: every line it shows arrives in both languages and is only picked by language here; an amount is a number
// and the server's label for its unit.
import { writable } from 'svelte/store';
import { del, getJSON, postJSON, putJSON } from './api';
import { fmtFrac, type LedgerLine, type Word } from './engine';
import type { Lang } from './i18n';
import type { Verdict } from './recipes';
import type { Bi, Food, Labelled } from './spices';

export type Unit = 'tbsp' | 'tsp' | 'ml' | 'dl' | 'g' | 'pcs';
export type Vessel = 'jug' | 'sauceboat' | 'bowl' | 'bottle' | 'jar';
export type BodyClass = 'thin' | 'coats' | 'thick' | 'stiff';
export type Level = 'ok' | 'at-limit' | 'warn';
export type GlutenStatus = 'ok' | 'yours' | 'check' | 'unknown' | 'swap';
export type MatchHow = 'exact' | 'stem' | 'fuzzy';
export type { Verdict };

/** A shelf item, as GET /api/sauces/shelves sends it. `step` and `default` are in `unit`; `alt` are its other units. */
export interface Item {
  id: string; name: Bi; role: string; driver: boolean; unit: Unit; default: number; step: number; alt: Unit[];
  g_per_ml: number; g_per_pc: number | null; fill: string; gluten: 'free' | 'label' | 'contains'; body: string; keeps: string;
}
export interface SauceShelf { id: string; en: string; hu: string; items: Item[] }
export interface Family extends Labelled {
  parent: string | null; vessel: Vessel; chip: string; body: BodyClass | null; note: Bi | null; kind: string;
}
export interface Shelves {
  shelves: SauceShelf[]; families: Family[]; foods: Food[]; roles: Labelled[]; taste: Labelled[]; units: Labelled[];
  keeps: (Labelled & { days: number })[]; chips: Labelled[]; body: (Labelled & { below: number })[]; stability: Labelled[]; levels: Labelled[];
  words: (Labelled & { min: number; mascot: string })[]; heat: (Labelled & { below: number })[]; max_lines: number;
}

export type Kind = 'good' | 'warn' | 'notice' | 'info';
export interface Finding extends Bi, LedgerLine { kind: Kind }
export interface Stability extends Bi { kind: string; level: Level; about: string[] }
export interface Fix extends Bi { id: string; axis: string; direction: string; label: Bi }
export interface SauceVoucher extends Bi { item: string; score: number }
export interface FamilyHit extends Bi { id: string; path: string[]; user: boolean; kind: string; chip: string }
export interface GlutenLine { pos: number; status: GlutenStatus; swap_id: string | null; tip_en: string | null; tip_hu: string | null; about: string[] }
export interface SauceEvaluation {
  score: number; base: number; word: Word; word_text: Bi; mascot: string; findings: Finding[];
  taste: Record<string, number>; salt_pct: number;
  body: { index: number; class: BodyClass; by: string; reduce: boolean } & Bi;
  stability: Stability[]; keeps: { class: string; days: number } & Bi; family: FamilyHit | null;
  vessel: Vessel; fill: string; heat: { value: number; word: string } & Bi;
  web: { nodes: { id: string; share: number }[]; edges: (Bi & { a: string; b: string; score: number; reason: string })[] };
  foods: { id: string; score: number; vouchers: SauceVoucher[] }[]; fixes: Fix[]; suggest: string[];
  spices: { jars: Record<string, number>; radar: Record<string, number> };
  lines: { pos: number; kind: string; id: string | number | null; g: number; share: number }[]; total_g: number;
  gluten?: { lines: GlutenLine[]; verdict: Verdict }; seq?: number | null;
}

/** One line of a sauce as the editor holds it and the server takes it: exactly one of shelf / spice / blend / item / raw.
 *  A typed line keeps its text (`raw`) and how it was matched beside what it became; `ok_gf` is the owner's override. */
export interface SauceLine {
  shelf?: string; spice?: string; blend?: number; item?: string; raw?: string;
  qty?: number; unit?: Unit; ok_gf?: boolean; match_how?: MatchHow | null;
}
/** A stored line, as GET /api/sauces/<id> sends it. */
export interface LineView {
  pos: number; kind: 'shelf' | 'spice' | 'blend' | 'off-shelf' | 'raw'; shelf_id: string | null; spice_id: string | null;
  blend_id: number | null; item_id: string | null; raw: string | null; qty: number | null; unit: Unit | null; ok_gf: boolean;
  match_how: MatchHow | null; gluten?: Omit<GlutenLine, 'pos'>;
}
export interface SauceSummary {
  id: number; names: Bi; origin: 'typed' | 'seed' | 'riff'; classic_id: string | null; tags: string[];
  family: FamilyHit | null; family_user: boolean; vessel: Vessel; fill: string; score: number | null; word: Word | null;
  keeps: { class: string; days: number } | null; heat: string; gluten: Verdict; yield_ml: number | null;
  created_at: string; updated_at: string;
}
export interface Sauce extends SauceSummary {
  name: string; lang: string; notes: string | null; method: Bi | null; lines: LineView[]; steps: { en: string[]; hu: string[] };
  timers: Record<Lang, { seconds: number; start: number; end: number }[][]>; evaluation: SauceEvaluation | null;
}
export interface SauceIn {
  name: string; notes?: string | null; tags: string[]; yield_ml?: number | null; family?: string | null;
  lines: SauceLine[]; steps: string[]; lang?: Lang;
}
/** What POST /api/sauces/line answers for a typed line. */
export type Typed =
  | { shelf: string; qty: number; unit: Unit; raw: string; match_how: MatchHow }
  | { spice: string; qty: number; unit: 'tsp'; raw: string; match_how: MatchHow }
  | { item: string; raw: string; match_how: MatchHow }
  | { raw: string };

export const api = {
  shelves: () => getJSON<Shelves>('/api/sauces/shelves'),
  list: () => getJSON<SauceSummary[]>('/api/sauces'),
  get: (id: number) => getJSON<Sauce>(`/api/sauces/${id}`),
  create: (s: SauceIn) => postJSON<{ id: number }>('/api/sauces', s),
  update: (id: number, s: SauceIn) => putJSON<Sauce>(`/api/sauces/${id}`, s),
  remove: (id: number) => del(`/api/sauces/${id}`),
  riff: (id: number) => postJSON<{ id: number }>(`/api/sauces/${id}/riff`, {}),
  /** A typed line, read like a recipe line. Throws when there is nothing to read in it (the editor says so). */
  typed: (text: string) => postJSON<Typed>('/api/sauces/line', { text }),
  evaluate: (lines: SauceLine[], steps: string[], family: string | null, seq: number) =>
    postJSON<SauceEvaluation>('/api/sauces/evaluate', { lines, steps, family, seq }),
};

export const shelves = writable<Shelves | null>(null);
export const sauceList = writable<SauceSummary[]>([]);
export async function loadShelves(): Promise<void> { try { shelves.set(await api.shelves()); } catch { /* offline: the screens wait */ } }
export async function loadSauces(): Promise<void> { try { sauceList.set(await api.list()); } catch { /* keep what we have */ } }

/** Every shelf item by id. */
export function itemIndex(s: Shelves | null): Map<string, Item> {
  return new Map((s?.shelves ?? []).flatMap((sh) => sh.items.map((i) => [i.id, i] as const)));
}
/** A display name for everything a voucher, a ledger line or a tray line can name: shelf items and rack jars (a jar's
 *  `name` — its `label` is the hand-lettered, lower-case one on the jar). */
export function nameIndex(s: Shelves | null, jars: { id: string; name: Bi }[], l: Lang): Record<string, string> {
  const out: Record<string, string> = {};
  for (const j of jars) out[j.id] = j.name[l];
  for (const sh of s?.shelves ?? []) for (const i of sh.items) out[i.id] = i.name[l];
  return out;
}

// --- amounts -----------------------------------------------------------------------------------------------------------
/** The server's table (sauce_engine.UNIT_ML): a spoon is 15 / 5 ml, a decilitre 100. */
export const UNIT_ML: Partial<Record<Unit, number>> = { tbsp: 15, tsp: 5, dl: 100, ml: 1 };
export const MAX_QTY = 5000;
const JAR_UNITS: Unit[] = ['tsp', 'tbsp', 'g'];
const BLEND_UNITS: Unit[] = ['tsp', 'tbsp'];
const JAR_STEP: Partial<Record<Unit, number>> = { tsp: 0.25, tbsp: 0.25, g: 0.5 };
const FALLBACK_STEP: Record<Unit, number> = { tbsp: 0.5, tsp: 0.25, ml: 10, dl: 0.5, g: 5, pcs: 1 };
const NICE = [0.25, 0.5, 1, 2, 5, 10, 20, 25, 50, 100, 250, 500];
const tidy = (n: number) => Math.round(n * 1e4) / 1e4;

/** The units a line can be measured in, its own first: a shelf item's, a jar's (tsp, tbsp, g), a blend's (tsp, tbsp).
 *  A typed off-shelf or raw line has no amount (it counts for gluten only). */
export function unitsOf(l: SauceLine, items: Map<string, Item>): Unit[] {
  if (l.shelf) { const e = items.get(l.shelf); return e ? [e.unit, ...e.alt] : []; }
  if (l.spice) return JAR_UNITS;
  if (l.blend !== undefined) return BLEND_UNITS;
  return [];
}

function toMl(e: Item, q: number, u: Unit): number | null {
  if (UNIT_ML[u]) return q * UNIT_ML[u]!;
  if (u === 'g') return q / e.g_per_ml;
  if (u === 'pcs') return e.g_per_pc ? (q * e.g_per_pc) / e.g_per_ml : null;
  return null;
}
function fromMl(e: Item, ml: number, u: Unit): number | null {
  if (UNIT_ML[u]) return ml / UNIT_ML[u]!;
  if (u === 'g') return ml * e.g_per_ml;
  if (u === 'pcs') return e.g_per_pc ? (ml * e.g_per_ml) / e.g_per_pc : null;
  return null;
}
/** A shelf item's amount in another of its units (null when the two do not convert: pieces with no weight). */
export function convert(e: Item, q: number, from: Unit, to: Unit): number | null {
  const ml = toMl(e, q, from);
  return ml === null ? null : fromMl(e, ml, to);
}
/** Rounded like the server's `_fit`: grams to one decimal, everything else to two. */
const fitRound = (q: number, u: Unit) => (u === 'g' ? Math.round(q * 10) / 10 : Math.round(q * 100) / 100);

/** The next unit of the line (the unit chip), the amount converted. A line with one unit, or a conversion that cannot
 *  be made, is returned as it is. */
export function flipUnit(l: SauceLine, items: Map<string, Item>, jars: Map<string, { g_per_tsp: number }>): SauceLine {
  const units = unitsOf(l, items);
  if (units.length < 2 || l.qty === undefined || !l.unit) return l;
  const to = units[(units.indexOf(l.unit) + 1) % units.length];
  let q: number | null = null;
  if (l.shelf) q = convert(items.get(l.shelf)!, l.qty, l.unit, to);
  else {
    const g = jars.get(l.spice ?? '')?.g_per_tsp;
    const tsp = l.unit === 'tsp' ? l.qty : l.unit === 'tbsp' ? l.qty * 3 : g ? l.qty / g : null;
    q = tsp === null ? null : to === 'tsp' ? tsp : to === 'tbsp' ? tsp / 3 : g ? tsp * g : null;
  }
  if (q === null) return l;
  return { ...l, qty: Math.min(MAX_QTY, Math.max(to === 'g' ? 0.1 : 0.01, fitRound(q, to))), unit: to };
}

/** One tap on ± for the line: the item's own step in its own unit; in another unit that step converted and rounded
 *  down to a round number (1 tbsp of oil → 10 ml); a jar or a blend by quarter teaspoons. */
export function stepOf(l: SauceLine, items: Map<string, Item>): number {
  const u = l.unit;
  if (!u) return 1;
  if (!l.shelf) return JAR_STEP[u] ?? FALLBACK_STEP[u];
  const e = items.get(l.shelf);
  if (!e) return FALLBACK_STEP[u];
  if (u === e.unit) return e.step;
  const c = convert(e, e.step, e.unit, u);
  if (c === null) return FALLBACK_STEP[u];
  return [...NICE].reverse().find((n) => n <= c + 1e-9) ?? NICE[0];
}
/** A tap on ±: by the step, landing on the steps, never below one step (hold the line to take it off) nor past 5000. */
export function stepAmount(q: number, step: number, dir: 1 | -1): number {
  const next = Math.round((q + dir * step) / step) * step;
  return tidy(Math.min(MAX_QTY, Math.max(step, next)));
}

/** What a cook can measure: tablespoons and pieces by halves, teaspoons by quarters, decilitres to one decimal, ml and
 *  grams whole — never below the smallest of them. */
export function roundFor(u: Unit, q: number): number {
  const by: Record<Unit, number> = { tbsp: 0.5, pcs: 0.5, tsp: 0.25, dl: 0.1, ml: 1, g: 1 };
  return tidy(Math.max(by[u], Math.round(q / by[u]) * by[u]));
}
/** An amount scaled to another yield. */
export const scaleQty = (q: number, u: Unit, factor: number): number => roundFor(u, q * factor);

/** An amount and the server's label for its unit: "2 tbsp" / "2 ek", "½ tk", "1,5 dl", "300 ml", "27 g". */
export function fmtAmount(q: number, u: Unit, units: Labelled[], l: Lang): string {
  const label = units.find((x) => x.id === u)?.[l] ?? u;
  const loc = l === 'hu' ? 'hu-HU' : 'en';
  const n = u === 'tbsp' || u === 'tsp' || u === 'pcs' ? fmtFrac(q, l)
    : u === 'dl' ? q.toLocaleString(loc, { maximumFractionDigits: 2 })
    : q.toLocaleString(loc, { maximumFractionDigits: q >= 10 ? 0 : 1 });
  return `${n} ${label}`;
}

/** A stored line as a cook reads it: the amount (scaled by `factor`) and the name — a shelf item's or a jar's own name,
 *  a blend's — or, for a typed line, its text. Never a sentence: a number, the server's unit label and a name. */
export function lineLabel(v: LineView, l: Lang, units: Labelled[], names: Record<string, string>, blends: Record<number, string>,
                          factor = 1): string {
  if (v.kind === 'off-shelf' || v.kind === 'raw') return v.raw ?? '';
  const name = v.kind === 'blend' ? (blends[v.blend_id!] ?? '') : (names[(v.shelf_id ?? v.spice_id)!] ?? v.shelf_id ?? v.spice_id ?? '');
  if (v.qty === null || !v.unit) return name;
  const q = factor === 1 ? v.qty : scaleQty(v.qty, v.unit, factor);
  return `${fmtAmount(q, v.unit, units, l)} ${name}`;
}

/** The yield the page starts from: the owner's, else the sauce's weight rounded to 50 ml, else 250 ml. */
export function baseYield(s: { yield_ml: number | null; evaluation: SauceEvaluation | null }): number {
  if (s.yield_ml) return s.yield_ml;
  if (s.evaluation) return Math.max(50, Math.round(s.evaluation.total_g / 50) * 50);
  return 250;
}
export const YIELD_STEP = 50, MIN_YIELD = 50, MAX_YIELD = 5000;

// --- the tray ----------------------------------------------------------------------------------------------------------
/** What a line is, for "is it on the tray already": a shelf item, a jar and a blend join once; typed lines may repeat. */
export function lineKey(l: SauceLine): string {
  if (l.shelf) return `shelf:${l.shelf}`;
  if (l.spice) return `spice:${l.spice}`;
  if (l.blend !== undefined) return `blend:${l.blend}`;
  if (l.item) return `item:${l.item}`;
  return `raw:${l.raw ?? ''}`;
}
/** Add a line (once, unless typed) up to `max` lines. Pure: returns the new array (the same one when nothing changed). */
export function trayAdd(tray: SauceLine[], l: SauceLine, max = 24): SauceLine[] {
  if (tray.length >= max) return tray;
  const k = lineKey(l);
  if (!k.startsWith('raw:') && !k.startsWith('item:') && tray.some((x) => lineKey(x) === k)) return tray;
  return [...tray, l];
}
export function traySet(tray: SauceLine[], i: number, patch: Partial<SauceLine>): SauceLine[] {
  return tray.map((l, k) => (k === i ? { ...l, ...patch } : l));
}
export function trayDrop(tray: SauceLine[], i: number): SauceLine[] {
  return tray.filter((_, k) => k !== i);
}
/** A typed line as a tray line: what the server made of it, its text kept beside a match (a jar keeps none — the
 *  server stores a jar line by its jar). */
export function fromTyped(t: Typed): SauceLine {
  if ('shelf' in t) return { shelf: t.shelf, qty: t.qty, unit: t.unit, raw: t.raw, match_how: t.match_how };
  if ('spice' in t) return { spice: t.spice, qty: t.qty, unit: t.unit, match_how: t.match_how };
  if ('item' in t) return { item: t.item, raw: t.raw, match_how: t.match_how };
  return { raw: t.raw };
}
/** A saved sauce's lines back as the tray lines that were sent — nothing the editor sent may be dropped by a round trip
 *  (the owner's GF override above all). Only the fields that are set are carried. */
export function fromView(lines: LineView[]): SauceLine[] {
  return lines.map((v) => {
    const l: SauceLine = v.kind === 'shelf' ? { shelf: v.shelf_id!, qty: v.qty!, unit: v.unit! }
      : v.kind === 'spice' ? { spice: v.spice_id!, qty: v.qty!, unit: v.unit! }
      : v.kind === 'blend' ? { blend: v.blend_id!, qty: v.qty!, unit: v.unit! }
      : v.kind === 'off-shelf' ? { item: v.item_id! } : {};
    if (v.raw !== null && v.kind !== 'spice' && v.kind !== 'blend') l.raw = v.raw;
    if (v.match_how) l.match_how = v.match_how;
    if (v.ok_gf) l.ok_gf = true;
    return l;
  });
}

// --- the families and the sideboard ------------------------------------------------------------------------------------
export interface FamilyNode extends Family { kids: FamilyNode[] }
/** The forty families as their tree: the ten groups (no parent), each family under its parent, in the server's order. */
export function familyTree(fams: Family[]): FamilyNode[] {
  const nodes = new Map(fams.map((f) => [f.id, { ...f, kids: [] as FamilyNode[] }]));
  const roots: FamilyNode[] = [];
  for (const f of fams) {
    const n = nodes.get(f.id)!;
    if (f.parent && nodes.has(f.parent)) nodes.get(f.parent)!.kids.push(n);
    else roots.push(n);
  }
  return roots;
}
/** The sideboard's family chips: a sauce under its family's chip (one with no family is under All only). */
export function byChip<S extends Pick<SauceSummary, 'family'>>(list: S[], chip: string | null): S[] {
  return chip ? list.filter((s) => s.family?.chip === chip) : list;
}
/** Newest first (when it was last changed), or A–Z by the name in the screen's language. */
export function sortSauces<S extends Pick<SauceSummary, 'names' | 'updated_at'>>(list: S[], by: 'new' | 'az', l: Lang): S[] {
  return [...list].sort(by === 'new' ? (a, b) => b.updated_at.localeCompare(a.updated_at)
                                     : (a, b) => a.names[l].localeCompare(b.names[l], l));
}

/** Pool sizes, from the engine's limits: 4000 random sauces of up to 24 lines (2026-10-20) gave at most 13 findings,
 *  5 stability lines (one per kind), 4 vouchers, 5 suggestions and a family path of 3; the fixes are read off the
 *  engine's list, which names at most all nine (sauce_data.FIXES) — the sweep only ever met 6. */
export const SAUCE_SLOTS = { findings: 20, stability: 5, fixes: 9, vouchers: 4, suggest: 5, path: 3, lines: 24 } as const;

/** A line's GF chip colour by its gluten state: fine (ok, the owner's own), look at it (check, unknown), swap it. */
export const GF_LEVEL: Record<GlutenStatus, 'ok' | 'check' | 'swap'> = { ok: 'ok', yours: 'ok', check: 'check', unknown: 'check', swap: 'swap' };

/** An evaluation with nothing in it — the panel's shape before the first line (no score, no words). It lets the panel
 *  and every section be BUILT ONCE when the page opens (the SP10 lesson: creating the panel on the first tap cost the
 *  kiosk a 450 ms frame). */
export const EMPTY_SAUCE_EVALUATION: SauceEvaluation = {
  score: 0, base: 50, word: 'muddled', word_text: { en: '', hu: '' }, mascot: 'think', findings: [],
  taste: { salt: 0, acid: 0, fat: 0, sweet: 0, heat: 0, umami: 0, aromatic: 0 }, salt_pct: 0,
  body: { index: 0, class: 'thin', by: 'none', reduce: false, en: '', hu: '' }, stability: [],
  keeps: { class: 'cooked', days: 0, en: '', hu: '' }, family: null, vessel: 'jug', fill: '#E8DCC4',
  heat: { value: 0, word: 'mild', en: '', hu: '' }, web: { nodes: [], edges: [] }, foods: [], fixes: [], suggest: [],
  spices: { jars: {}, radar: { warm: 0, earthy: 0, hot: 0, bright: 0, herbal: 0, floral: 0, bitter: 0, savoury: 0 } },
  lines: [], total_g: 0,
};
