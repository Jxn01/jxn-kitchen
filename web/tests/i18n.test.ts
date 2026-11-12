/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import en from '../src/i18n/en.json';
import hu from '../src/i18n/hu.json';
import { interpolate, translate } from '../src/lib/i18n';

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? sources(p) : /\.(svelte|ts)$/.test(f) ? [p] : [];
  });
}

describe('i18n dictionaries', () => {
  it('en and hu have exactly the same keys (English-only singular .one keys aside)', () => {
    expect(Object.keys(hu).sort()).toEqual(Object.keys(en).filter((k) => !k.endsWith('.one')).sort());
  });
  it('no value is empty', () => {
    for (const d of [en, hu]) for (const [k, v] of Object.entries(d)) expect(v, k).not.toBe('');
  });
  it('every key the code uses exists', () => {
    const used = new Set<string>();
    for (const f of sources(join(__dirname, '../src'))) {
      for (const m of readFileSync(f, 'utf8').matchAll(/(?<![\w$.])\$?t\(\s*['"]([a-z0-9_.-]+)['"]/g)) used.add(m[1]);
    }
    expect(used.size).toBeGreaterThan(0);
    const missing = [...used].filter((k) => !(k in en));
    expect(missing).toEqual([]);
  });
  it('interpolates {params}', () => {
    expect(interpolate('{n} things in', { n: 37 })).toBe('37 things in');
    expect(interpolate('no params', undefined)).toBe('no params');
  });
});

describe('plural', () => {
  it('uses the .one string for exactly one, in English', () => {
    expect(translate('en', 'home.recipes.count', { n: 1 })).toBe('1 recipe');
    expect(translate('en', 'home.recipes.count', { n: 2 })).toBe('2 recipes');
    expect(translate('en', 'home.recipes.count', { n: 0 })).toBe('0 recipes');
    expect(translate('hu', 'home.recipes.count', { n: 1 })).toBe('1 recept');
  });
  it('every .one key has its base key, and every English count noun that needs one has it', () => {
    for (const k of Object.keys(en)) if (k.endsWith('.one')) expect(en).toHaveProperty(k.slice(0, -4));
    for (const [k, v] of Object.entries(en as Record<string, string>)) {
      if (k.endsWith('.one') || !v.includes('{n}')) continue;
      if (/\{n\} (things|recipes|servings|swaps|places|lines)\b/.test(v)) expect(en, k).toHaveProperty(`${k}.one`);
    }
  });
});

describe('no hard-coded aria-labels (review: "remove", "undo", "keyboard" were English-only)', () => {
  it('every aria-label in the markup comes from $t', () => {
    const walk = (d: string): string[] => readdirSync(d).flatMap((f) => statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]);
    const bad = walk(join(__dirname, '../src')).filter((f) => f.endsWith('.svelte'))
      .flatMap((f) => [...readFileSync(f, 'utf8').matchAll(/aria-label="([^"{]*[A-Za-z][^"{]*)"/g)].map((m) => `${f}: ${m[1]}`));
    expect(bad).toEqual([]);
  });
});
