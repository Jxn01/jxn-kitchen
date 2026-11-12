/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render } from 'svelte/server';
import SauceEvalPanel from '../src/components/sauces/SauceEvalPanel.svelte';
import Vessel from '../src/components/sauces/Vessel.svelte';
import FamilyTree from '../src/components/sauces/FamilyTree.svelte';
import shelvesFx from './fixtures/engine-sauce-shelves.json';
import rackFx from './fixtures/engine-rack.json';
import paprikas from './fixtures/engine-sauce-paprikas.json';
import mayonnaise from './fixtures/engine-sauce-mayonnaise.json';
import fights from './fixtures/engine-sauce-fights.json';
import { lang, translate } from '../src/lib/i18n';
import { nameIndex, type SauceEvaluation, type Shelves } from '../src/lib/sauces';
import type { Rack } from '../src/lib/spices';
import { svgAnimationProblems } from './mascot.test';
import { iconsInKeyBlocks } from './charts.test';
import { contentKeyed, iconsInIfBlocks } from './guards';

const SH = shelvesFx as unknown as Shelves;
const RACK = rackFx as unknown as Rack;
const JARS = RACK.shelves.flatMap((s) => s.jars);
const EVALS = { paprikas, mayonnaise, fights } as unknown as Record<string, SauceEvaluation>;
// a short sauce the engine recognises no family in (seen in the random sweep): everything must still render
const NOFAMILY = { ...(paprikas as unknown as SauceEvaluation), family: null } as SauceEvaluation;
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const count = (html: string, tag: string) => (html.match(new RegExp(`<${tag}\\b`, 'g')) ?? []).length;

describe('the sauce panel shows everything the engine said, in both languages', () => {
  it.each(Object.keys(EVALS))('%s', (name) => {
    const e = EVALS[name];
    for (const l of ['en', 'hu'] as const) {
      lang.set(l);
      const names = nameIndex(SH, JARS, l);
      const { body } = render(SauceEvalPanel, { props: { e, shelves: SH, names, mode: 'scroll' } });
      for (const f of e.findings) expect(body, `${l} ${f.id}`).toContain(esc(f[l]));
      for (const s of e.stability) expect(body, `${l} ${s.kind}`).toContain(esc(s[l]));
      for (const x of e.fixes) { expect(body).toContain(esc(x[l])); expect(body).toContain(esc(x.label[l])); }
      expect(body).toContain(esc(e.word_text[l]));
      expect(body).toContain(esc(e.body[l]));
      expect(body).toContain(esc(e.keeps[l]));
      for (const a of SH.taste) expect(body).toContain(esc(a[l]));
      for (const f of SH.families) expect(body).toContain(esc(f[l]));         // the family tree, every family
      const v = e.gluten!.verdict;
      expect(body).toContain(esc(translate(l, `recipe.verdict.${v.state}`, { n: v.state === 'check' ? v.check : v.unknown })));
    }
    lang.set('en');
  });
  it('the mayonnaise holds its emulsion and warns of raw egg; the fights sauce reads as a fight', () => {
    expect(EVALS.mayonnaise.stability.map((s) => s.kind)).toEqual(['emulsion', 'raw-egg']);
    expect(EVALS.fights.findings.filter((f) => f.kind === 'warn').length).toBeGreaterThan(3);
  });
  it('a sauce with no family still renders, its tree unlit', () => {
    const body = render(SauceEvalPanel, { props: { e: NOFAMILY, shelves: SH, names: nameIndex(SH, JARS, 'en'), mode: 'scroll' } }).body;
    expect(body).toContain(esc(NOFAMILY.findings[0].en));
    expect(body).not.toMatch(/class="fam[^"]*\blit\b/);
  });
});

describe('fixed pools: a bigger sauce never creates rows, dials or icons (the lábas lesson)', () => {
  const names = nameIndex(SH, JARS, 'en');
  it('the panel exists before the first line, every section and every slot built (an answer only fills them)', () => {
    const empty = render(SauceEvalPanel, { props: { e: null, shelves: SH, names, mode: 'tabs', emptyText: 'pick' } }).body;
    for (const e of [...Object.values(EVALS), NOFAMILY]) {
      const full = render(SauceEvalPanel, { props: { e, shelves: SH, names, mode: 'tabs' } }).body;
      for (const tag of ['section', 'li', 'p', 'button', 'span', 'circle', 'path', 'line', 'use', 'svg', 'ellipse']) expect(count(full, tag), tag).toBe(count(empty, tag));
    }
  });
  it('the family tree lights the path and nothing else', () => {
    const body = render(FamilyTree, { props: { families: SH.families, path: ['emulsions', 'mayonnaise', 'aioli'], lang: 'en' } }).body;
    expect((body.match(/class="fam[^"]*\blit\b/g) ?? []).length).toBe(3);
    expect(count(body, 'span')).toBe(SH.families.length);
  });
  it('every vessel draws, and a new vessel only changes paths (the same elements)', () => {
    const shapes = (['jug', 'sauceboat', 'bowl', 'bottle', 'jar'] as const).map((v) => render(Vessel, { props: { vessel: v, fill: '#C8281E' } }).body);
    for (const b of shapes) { expect(b).toContain('#C8281E'); expect(count(b, 'path')).toBe(count(shapes[0], 'path')); }
    expect(new Set(shapes).size).toBe(5);
  });
});

describe('the sauce components and screens animate only compositor-friendly things, never re-create icons, and reuse rows', () => {
  const dir = join(__dirname, '../src/components/sauces');
  const files = [...readdirSync(dir).filter((f) => f.endsWith('.svelte')).map((f) => join(dir, f)),
                 ...['Sauces', 'Sauce', 'SauceEdit'].map((s) => join(__dirname, `../src/screens/${s}.svelte`))];
  it('sees the files', () => expect(files.length).toBeGreaterThanOrEqual(10));
  it('positive controls: the shared guards still bite on sauce lists', () => {
    expect(contentKeyed('{#each e.stability as s (s.kind)}<li></li>{/each}')).toHaveLength(1);
    expect(contentKeyed('{#each fixes as f, k (k)}<li></li>{/each}')).toHaveLength(1);
    expect(contentKeyed('{#each tray as l (lineKey(l))}<div></div>{/each}')).toHaveLength(1);
    expect(contentKeyed('{#each pool(tray, SAUCE_SLOTS.lines) as l, k (k)}<div></div>{/each}')).toHaveLength(0);
    expect(contentKeyed('{#each shown as s, i (i)}<button></button>{/each}')).toHaveLength(1);           // a filtered index, unpooled
    expect(contentKeyed('{#each pool(shown, $sauceList.length) as s, i (i)}<button></button>{/each}')).toHaveLength(0);
    expect(iconsInIfBlocks('{#if open}<Icon name="sauces" />{/if}')).toBe(1);
  });
  it("the editor's shelves are a fixed set of slots and its notes pane is always there (a tab tap builds nothing)", () => {
    const src = readFileSync(join(__dirname, '../src/screens/SauceEdit.svelte'), 'utf8');
    expect(src).toMatch(/\{#each Array\(slots\) as _, k \(k\)\}/);
    expect(src).not.toMatch(/\{#if (tab|shelf)/);
  });
  it.each(files)('%s', (f) => {
    const src = readFileSync(f, 'utf8');
    expect(contentKeyed(src)).toEqual([]);
    expect(svgAnimationProblems(src)).toEqual([]);
    expect(iconsInKeyBlocks(src)).toBe(0);
    expect(iconsInIfBlocks(src.replace(/<PageHeader[\s\S]*?<\/PageHeader>/, ''))).toBe(0);
  });
});
