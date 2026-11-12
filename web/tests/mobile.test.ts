/// <reference types="node" />
// The mobile-first pass (2026-10-26): the owner's iPhone in Safari is first-class, and the kiosk view must not move.
// Three source guards, each with a positive control:
//  1. every media query is one that cannot match the kiosk (1024×640 CSS px, landscape) — so a phone rule can never
//     leak onto it (the kiosk screenshots were compared pixel for pixel before and after: README → Phones);
//  2. every fixed element offset from the screen's top or bottom keeps clear of the notch / Dynamic Island / home
//     indicator with env(safe-area-inset-*) (0 on the kiosk: the same pixels there);
//  3. touch targets are sized by the --touch token (64 px kiosk, 48 px phone), not a hard-coded 64 px.
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SRC = join(__dirname, '..', 'src');
function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? files(p) : /\.(svelte|css)$/.test(f) ? [p] : [];
  });
}
const ALL = files(SRC).map((p) => ({ p: p.slice(SRC.length + 1), src: readFileSync(p, 'utf8') }));

const KIOSK = { w: 1024, h: 640 };
/** Can this media query match the kiosk? Only the forms below are understood; anything else counts as "may match". */
export function matchesKiosk(q: string): boolean {
  const parts = q.replace(/^@media\s*/, '').trim();
  if (/^\(prefers-reduced-motion: reduce\)$/.test(parts)) return false;   // the kiosk is excluded by :root:not(.kiosk)
  return !parts.split(/\s*,\s*/).every((alt) => {
    const conds = alt.split(/\s+and\s+/);
    return conds.some((c) => {
      let m;
      if ((m = c.match(/^\(max-aspect-ratio:\s*(\d+)\s*\/\s*(\d+)\)$/))) return KIOSK.w / KIOSK.h > +m[1] / +m[2];
      if ((m = c.match(/^\(max-width:\s*(\d+)px\)$/))) return KIOSK.w > +m[1];
      if ((m = c.match(/^\(max-height:\s*(\d+)px\)$/))) return KIOSK.h > +m[1];
      if (/^\(orientation:\s*portrait\)$/.test(c)) return true;
      return false;   // a condition we cannot rule out
    });
  });
}

/** Rules (selector { body }) that are position: fixed and offset by a number of px from the top or the bottom. */
export function unsafeFixed(src: string): string[] {
  return [...src.matchAll(/([^{}]+)\{([^{}]*position:\s*fixed[^{}]*)\}/g)].flatMap((m) => {
    const body = m[2];
    const bad = [];
    const top = body.match(/(?:^|[;\s])top:\s*([^;]+)/), bottom = body.match(/(?:^|[;\s])bottom:\s*([^;]+)/);
    if (top && /\d*[1-9]\d*px/.test(top[1]) && !/safe-area-inset-top/.test(top[1])) bad.push(`${m[1].trim()} top`);
    if (bottom && /\d*[1-9]\d*px/.test(bottom[1]) && !/safe-area-inset-bottom/.test(bottom[1])) bad.push(`${m[1].trim()} bottom`);
    return bad;
  });
}

/** Elements sized 64 px outright. Allowed where it is not a touch target (a decoration, a plate, a drawing). */
const HARD64 = /(?:^|[;{\s])(?:min-)?(?:width|height):\s*64px/g;
const ALLOWED_64: Record<string, string> = {
  'screens/Browse.svelte': 'the site plate: a picture, not a button',
  'components/sauces/KeepsCard.svelte': 'the keeping ladder: a drawing',
  'components/illus/Swatches.svelte': 'a tilting swatch in an infographic: a drawing',
  'screens/RecipeEdit.svelte': 'the preview\'s quantity column width, not a target',
};

describe('media queries never match the kiosk', () => {
  it('positive control', () => {
    expect(matchesKiosk('@media (max-aspect-ratio: 1/1)')).toBe(false);
    expect(matchesKiosk('@media (max-width: 760px)')).toBe(false);
    expect(matchesKiosk('@media (min-width: 600px)')).toBe(true);
    expect(matchesKiosk('@media (max-width: 1200px)')).toBe(true);
    expect(matchesKiosk('@media (max-height: 700px)')).toBe(true);
  });
  it('every query in the source', () => {
    const queries = ALL.flatMap(({ p, src }) => [...src.matchAll(/@media[^{]+/g)].map((m) => `${p}: ${m[0].trim()}`));
    expect(queries.length).toBeGreaterThan(20);
    expect(queries.filter((q) => matchesKiosk(q.split(': ').slice(1).join(': ')))).toEqual([]);
  });
});

describe('fixed elements keep clear of the safe areas', () => {
  it('positive control', () => {
    expect(unsafeFixed('.t { position: fixed; bottom: 18px; }')).toEqual(['.t bottom']);
    expect(unsafeFixed('.t { position: fixed; bottom: calc(18px + env(safe-area-inset-bottom)); }')).toEqual([]);
    expect(unsafeFixed('.s { position: fixed; inset: 0; }')).toEqual([]);
    expect(unsafeFixed('.k { position: fixed; left: 0; bottom: 0; }')).toEqual([]);
  });
  it('every fixed rule', () => {
    // Home's counter, mascot and bubble are hidden on a phone (display: none in its portrait rule)
    const bad = ALL.filter(({ p }) => p !== 'screens/Home.svelte').flatMap(({ p, src }) => unsafeFixed(src).map((b) => `${p}: ${b}`));
    expect(bad).toEqual([]);
  });
});

describe('touch targets use the --touch token', () => {
  it('positive control', () => {
    expect('.b { width: 64px; height: 64px; }'.match(HARD64)?.length).toBe(2);
    expect('.b { width: var(--touch); }'.match(HARD64)).toBeNull();
  });
  it('no hard-coded 64 px outside the allow list', () => {
    const bad = ALL.filter(({ p, src }) => [...src.matchAll(HARD64)].length > 0 && !(p in ALLOWED_64)).map(({ p }) => p);
    expect(bad).toEqual([]);
  });
});
