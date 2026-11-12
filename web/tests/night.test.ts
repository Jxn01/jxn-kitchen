/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { darkScene, isNight } from '../src/lib/night';

// Same table as server/tests/test_night.py — the two implementations must agree.
describe('isNight', () => {
  it('wraps midnight', () => {
    for (const h of [23, 2, 5]) expect(isNight(h, 23, 6)).toBe(true);
    for (const h of [6, 12, 22]) expect(isNight(h, 23, 6)).toBe(false);
  });
  it('same-day window', () => { expect(isNight(1, 0, 6)).toBe(true); expect(isNight(7, 0, 6)).toBe(false); });
  it('equal means never', () => { for (let h = 0; h < 24; h++) expect(isNight(h, 5, 5)).toBe(false); });
});

describe('darkScene — night styling is scoped to the idle scene', () => {
  it('only the idle scene goes dark at night', () => {
    expect(darkScene(true, 'idle')).toBe(true);
    for (const r of ['home', 'pantry', 'pantry-cat', 'shopping', 'recipes', 'recipe', 'recipe-edit', 'settings', 'cook'])
      expect(darkScene(true, r), r).toBe(false);
    expect(darkScene(false, 'idle')).toBe(false);
  });
});

describe('the night palette stays inside the idle scene', () => {
  // Overlays (timer card, toasts, keyboard) sit above the idle scene; with the palette on :root they got dark
  // backgrounds under dark ink — the timer's Stop button was unreadable at midnight.
  it('no stylesheet redefines --cream/--paper at document level, and nothing toggles a class on <html> for night', async () => {
    const { readdirSync, readFileSync, statSync } = await import('node:fs');
    const { join } = await import('node:path');
    const walk = (d: string): string[] => readdirSync(d).flatMap((f) => statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]);
    const files = walk(join(__dirname, '../src')).filter((f) => /\.(css|svelte|ts)$/.test(f));
    const bad: string[] = [];
    for (const f of files) {
      const src = readFileSync(f, 'utf8');
      for (const m of src.matchAll(/(:root[^{,]*\.[\w-]+|html[^{,]*\.[\w-]+)\s*\{[^}]*--(cream|paper)\s*:/g)) bad.push(`${f}: ${m[1]}`);
      if (/documentElement\.classList\.(toggle|add)\(\s*['"]night/.test(src)) bad.push(`${f}: toggles night on <html>`);
    }
    expect(bad).toEqual([]);
    const idle = readFileSync(join(__dirname, '../src/screens/Idle.svelte'), 'utf8');
    expect(idle).toMatch(/class:night-palette=\{night\}/);
  });
});
