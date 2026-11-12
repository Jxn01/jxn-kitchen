/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render } from 'svelte/server';
import EvalPanel from '../src/components/spices/EvalPanel.svelte';
import HarmonyWeb from '../src/components/spices/HarmonyWeb.svelte';
import FoodBoard from '../src/components/spices/FoodBoard.svelte';
import SpiceJar from '../src/components/spices/SpiceJar.svelte';
import rack from './fixtures/engine-rack.json';
import porkolt from './fixtures/engine-eval-porkolt.json';
import curry from './fixtures/engine-eval-curry.json';
import clash from './fixtures/engine-eval-clash.json';
import { lang } from '../src/lib/i18n';
import type { Evaluation, Rack } from '../src/lib/spices';
import { svgAnimationProblems } from './mascot.test';
import { iconsInKeyBlocks } from './charts.test';
import { contentKeyed, iconsInIfBlocks } from './guards';

const R = rack as unknown as Rack;
const EVALS = { porkolt, curry, clash } as unknown as Record<string, Evaluation>;
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

describe('the spice panel shows everything the engine said, in both languages', () => {
  it.each(Object.keys(EVALS))('%s', (name) => {
    const e = EVALS[name];
    for (const l of ['en', 'hu'] as const) {
      lang.set(l);
      const { body } = render(EvalPanel, { props: { e, rack: R, mode: 'scroll' } });
      for (const f of e.findings) expect(body, `${l} ${f.id}`).toContain(esc(f[l]));
      expect(body).toContain(esc(e.word_text[l]));
      expect(body).toContain(esc(e.gluten![l]));
      for (const c of e.classics) expect(body).toContain(esc(c[l]));
      for (const ax of R.axes) expect(body).toContain(esc(ax[l]));
    }
    lang.set('en');
  });
  it('the clash blend reads as a fight, with its clash on top', () => {
    expect(EVALS.clash.word).toBe('fighting');
    expect(EVALS.clash.findings[0].kind).toBe('warn');
  });
});

describe('fixed pools: a bigger blend never creates nodes, lines or icons (the lábas lesson)', () => {
  const names = Object.fromEntries(R.shelves.flatMap((s) => s.jars.map((j) => [j.id, j.label.en])));
  const fills = Object.fromEntries(R.shelves.flatMap((s) => s.jars.map((j) => [j.id, j.fill])));
  const count = (html: string, tag: string) => (html.match(new RegExp(`<${tag}\\b`, 'g')) ?? []).length;
  it('the web always holds 16 node slots, 120 edge slots and a 15-line top layer — lit or not', () => {
    const small = render(HarmonyWeb, { props: { nodes: EVALS.clash.web.nodes, edges: EVALS.clash.web.edges, names, fills } }).body;
    const big = render(HarmonyWeb, { props: { nodes: EVALS.curry.web.nodes, edges: EVALS.curry.web.edges, names, fills } }).body;
    const lit = render(HarmonyWeb, { props: { nodes: EVALS.curry.web.nodes, edges: EVALS.curry.web.edges, names, fills, focus: 'cumin' } }).body;
    for (const b of [small, big, lit]) expect(count(b, 'line')).toBe(135);
    expect(count(small, 'circle')).toBe(count(big, 'circle'));
    expect(count(lit, 'circle')).toBe(count(big, 'circle'));
  });
  it('the panel exists before the first jar, every section and every slot built (an answer only fills them)', () => {
    const empty = render(EvalPanel, { props: { e: null, rack: R, mode: 'tabs', emptyText: 'pick' } }).body;
    for (const e of Object.values(EVALS)) {
      const full = render(EvalPanel, { props: { e, rack: R, mode: 'tabs' } }).body;
      for (const tag of ['section', 'li', 'p', 'button', 'span', 'circle', 'path', 'line', 'use']) expect(count(full, tag), tag).toBe(count(empty, tag));
    }
  });
  it('the goes-with board always mounts all 25 foods', () => {
    for (const e of Object.values(EVALS)) {
      const body = render(FoodBoard, { props: { foods: R.foods, scored: e.foods, lang: 'en', names } }).body;
      expect(count(body, 'use')).toBe(25);
    }
  });
  it('a jar draws its stripes, bottom up', () => {
    const body = render(SpiceJar, { props: { stripes: [{ fill: '#C8281E', part: 4 }, { fill: '#8A6A3B', part: 1 }] } }).body;
    expect(body).toContain('#C8281E');
    expect(body).toContain('#8A6A3B');
  });
});

describe('the spice components and screens animate only compositor-friendly things, never re-create icons, and reuse rows', () => {
  const dir = join(__dirname, '../src/components/spices');
  const files = [...readdirSync(dir).filter((f) => f.endsWith('.svelte')).map((f) => join(dir, f)),
                 ...['Spices', 'Blend', 'BlendEdit'].map((s) => join(__dirname, `../src/screens/${s}.svelte`))];
  it('sees the files', () => expect(files.length).toBeGreaterThanOrEqual(13));
  it('positive control: an icon inside an {#if} is caught', () => {
    expect(iconsInIfBlocks('{#if inTray}<span class="tick"><Icon name="checkmark" size={18} /></span>{/if}')).toBe(1);
  });
  it('positive control: a refilled list keyed by its content, or not pooled, is caught; a pooled one keyed by place is not', () => {
    expect(contentKeyed('{#each classics as c (c.id)}<li></li>{/each}')).toHaveLength(1);
    expect(contentKeyed('{#each chosen?.vouchers ?? [] as v, k (v.spice)}<p></p>{/each}')).toHaveLength(1);
    expect(contentKeyed('{#each classics as c, i (i)}<li></li>{/each}')).toHaveLength(1);
    expect(contentKeyed('{#each pool(classics, SLOTS.classics) as c, i (i)}<li></li>{/each}')).toHaveLength(0);
  });
  it("the editor's rack is a fixed set of slots and its notes pane is always there (a tab tap builds nothing)", () => {
    const src = readFileSync(join(__dirname, '../src/screens/BlendEdit.svelte'), 'utf8');
    expect(src).toMatch(/\{#each Array\(slots\) as _, k \(k\)\}/);
    expect(src).not.toMatch(/\{#if shelf/);
    expect(src).not.toMatch(/\{#each \$rack\.shelves\[shelf\]\.jars/);
  });
  it.each(files)('%s', (f) => {
    const src = readFileSync(f, 'utf8');
    expect(contentKeyed(src)).toEqual([]);
    expect(svgAnimationProblems(src)).toEqual([]);
    expect(iconsInKeyBlocks(src)).toBe(0);
    expect(iconsInIfBlocks(src.replace(/<PageHeader[\s\S]*?<\/PageHeader>/, ''))).toBe(0);   // the header is built with the page
  });
});
