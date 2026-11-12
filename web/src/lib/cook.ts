// Cook mode's pure parts (tested in cook.test.ts). Cook mode cooks a *cookable*: a recipe or a sauce, each read into
// the same shape by its adapter below.
import type { Lang } from './i18n';
import { lineText, type Line, type Recipe } from './recipes';
import { lineLabel, type GlutenStatus, type Sauce } from './sauces';
import type { Labelled } from './spices';

export type Timer = { start: number; end: number; seconds: number };
/** What cook mode needs of a recipe or a sauce. `recipeId` ties its timers to a recipe (a sauce's timers stand alone);
 *  `used` are the pantry tiles for "Used up anything?" (a sauce has none: the pantry is not an input to the engines). */
export interface Cookable {
  title: string; back: string; recipeId: number | null; used: string[];
  steps: { text: string; timers: Timer[] }[];
  lines: { key: number; text: string; note: string | null; gluten: GlutenStatus | null }[];
  servings: number | null; yield_ml: number | null; keeps: number | null;
}

export function fromRecipe(r: Recipe): Cookable {
  return {
    title: r.title, back: `/recipe/${r.id}`, recipeId: r.id, used: usedUp(r.lines), servings: r.servings, yield_ml: null, keeps: null,
    steps: r.steps.map((s) => ({ text: s.text, timers: s.timers })),
    lines: r.lines.map((l) => ({ key: l.pos, text: lineText(l, true).text, note: l.note, gluten: l.gluten })),
  };
}

export function fromSauce(s: Sauce, l: Lang, units: Labelled[], names: Record<string, string>, blends: Record<number, string>): Cookable {
  return {
    title: s.names[l], back: `/sauces/${s.id}`, recipeId: null, used: [], servings: null, yield_ml: s.yield_ml, keeps: s.keeps?.days ?? null,
    steps: s.steps[l].map((text, i) => ({ text, timers: s.timers[l][i] ?? [] })),
    lines: s.lines.map((v) => ({ key: v.pos, text: lineLabel(v, l, units, names, blends), note: null, gluten: v.gluten?.status ?? null })),
  };
}

export type Part = { text: string; seconds?: number };

/** A step's text cut into plain text and the durations the server found in it (each a timer button). */
export function stepParts(text: string, timers: { start: number; end: number; seconds: number }[]): Part[] {
  const out: Part[] = [];
  let at = 0;
  for (const t of [...timers].sort((a, b) => a.start - b.start)) {
    if (t.start < at) continue;
    if (t.start > at) out.push({ text: text.slice(at, t.start) });
    out.push({ text: text.slice(t.start, t.end), seconds: t.seconds });
    at = t.end;
  }
  if (at < text.length) out.push({ text: text.slice(at) });
  return out;
}

/** "Paprikás csirke · 3. lépés" — the recipe and the step, within the server's 60-character label limit. */
export function timerLabel(title: string, pos: number, lang: 'en' | 'hu'): string {
  const step = lang === 'hu' ? `${pos + 1}. lépés` : `step ${pos + 1}`;
  const room = 60 - step.length - 3;
  const t = title.length > room ? title.slice(0, room - 1).trimEnd() + '…' : title;
  return `${t} · ${step}`;
}

/** "Used up anything?": each pantry tile the recipe used that is in, once. */
export function usedUp(lines: Pick<Line, 'pantry_id' | 'have'>[]): string[] {
  const out: string[] = [];
  for (const l of lines) if (l.have && l.pantry_id && !out.includes(l.pantry_id)) out.push(l.pantry_id);
  return out;
}
