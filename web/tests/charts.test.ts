/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render } from 'svelte/server';
import Chart from '../src/components/illus/Chart.svelte';
import lib from './fixtures/knowhow.json';
import { tx, type KChart, type KSection, type KText } from '../src/lib/knowhow';

// Every chart in the real library (knowhow/*.yaml → the fixture) is rendered, in both languages: a chart whose data
// and component drifted apart (a renamed key, a type the dispatcher does not know) fails here, not on the kiosk.
const charts = (lib as unknown as KSection[]).flatMap((s) => s.pages.filter((p) => p.chart).map((p) => [`${s.id}/${p.id}`, p.chart as KChart] as const));
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
// Every label is on screen at once — except a `layers` item's parts, which show for the chosen item only: those must
// show for the first item (the one chosen when the page opens).
function labels(n: unknown, out: KText[] = []): KText[] {
  if (Array.isArray(n)) n.forEach((v) => labels(v, out));
  else if (n && typeof n === 'object') for (const [k, v] of Object.entries(n)) k === 'label' ? out.push(v as KText) : k === 'layers' ? undefined : labels(v, out);
  return out;
}
function visible(chart: KChart): KText[] {
  const out = labels(chart);
  if (chart.type === 'layers') out.push(...chart.items[0].layers.map((l) => l.label));
  return out;
}

describe('every chart in the library renders, in both languages, with every label on screen', () => {
  it('the library has charts', () => expect(charts.length).toBeGreaterThan(0));
  it('every chart type is used by a real page (so every branch of the dispatcher is rendered here)', () => {
    const src = readFileSync(join(__dirname, '../src/components/illus/Chart.svelte'), 'utf8');
    const drawn = [...src.matchAll(/chart\.type === '(\w+)'/g)].map((m) => m[1]).sort();
    expect(drawn).toEqual(['bars', 'board', 'layers', 'matrix', 'picker', 'scale', 'steps', 'swatches', 'vessel']);
    expect([...new Set(charts.map(([, c]) => c.type))].sort()).toEqual(drawn);
  });
  it.each(charts)('%s', (_id, chart) => {
    for (const lang of ['en', 'hu'] as const) {
      const { body } = render(Chart, { props: { chart, lang } });
      expect(body.length).toBeGreaterThan(200);
      for (const l of visible(chart)) expect(body).toContain(esc(tx(l, lang)));
    }
  });
});

// Re-creating icons on every choice cost the kiosk 370–440 ms a tap (the lábas's floating food, 2026-10-11): an
// OpenMoji drawing is expensive to build and paint on the Atom. Everything a choice can show must exist from the start
// and be switched by opacity — so no {#key} block in an infographic may contain an <Icon>.
import { readdirSync } from 'node:fs';
export function iconsInKeyBlocks(src: string): number {
  return [...src.matchAll(/\{#key [^}]*\}([\s\S]*?)\{\/key\}/g)].filter((m) => m[1].includes('<Icon')).length;
}
describe('no infographic re-creates icons on a choice', () => {
  const dir = join(__dirname, '../src/components/illus');
  const files = readdirSync(dir).filter((f) => f.endsWith('.svelte'));
  it('positive control: the old lábas pattern is caught', () => {
    expect(iconsInKeyBlocks('{#key sel}{#each it.icons as ic}<div><Icon name={ic} /></div>{/each}{/key}')).toBe(1);
    expect(files.length).toBeGreaterThan(20);
  });
  it.each(files)('%s', (f) => expect(iconsInKeyBlocks(readFileSync(join(dir, f), 'utf8'))).toBe(0));
});
