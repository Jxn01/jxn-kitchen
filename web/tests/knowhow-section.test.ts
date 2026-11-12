/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// Moving between two pages of one section that use the same chart type re-used the component and kept its selection:
// choosing the 5th band of one thermometer and opening a 4-band one read a band that is not there.
// The infographic area must be keyed by the page, so it mounts fresh.
describe('the know-how page remounts its infographic per page', () => {
  const src = readFileSync(join(__dirname, '../src/screens/KnowHowSection.svelte'), 'utf8');
  it('the illustration and chart branches sit inside a {#key} on the page id', () => {
    const key = src.indexOf('{#key `${sid}/${page.id}`}');
    expect(key).toBeGreaterThan(-1);
    expect(src.indexOf('{#if page.illustration}')).toBeGreaterThan(key);
    expect(src.indexOf('<Chart chart={page.chart}')).toBeGreaterThan(key);
    expect(src.indexOf('{/key}', src.indexOf('<Chart chart={page.chart}'))).toBeGreaterThan(-1);
  });
});
