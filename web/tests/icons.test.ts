/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

// An icon named in code (not in the YAML the sprite builder reads) silently renders as nothing when the sprite lacks
// it — the fridge's drink carton did (2026-10-11). Every literal icon name in web/src must be a symbol in the sprite;
// declare new ones in icons/manifest.yaml.
const sprite = new Set([...readFileSync(join(__dirname, '../public/sprite.svg'), 'utf8').matchAll(/<symbol id="i-([^"]+)"/g)].map((m) => m[1]));
const walk = (d: string): string[] => readdirSync(d, { withFileTypes: true }).flatMap((e) =>
  e.isDirectory() ? walk(join(d, e.name)) : /\.(svelte|ts)$/.test(e.name) ? [join(d, e.name)] : []);
export function namedIcons(src: string): string[] {
  return [...src.matchAll(/['"](om-[0-9a-f]{4,5}(?:-[0-9a-f]{4,5})*|c-[a-z][a-z-]*)['"]/g)].map((m) => m[1]);
}

describe('every icon named in code is in the sprite', () => {
  const used = walk(join(__dirname, '../src')).flatMap((f) => namedIcons(readFileSync(f, 'utf8')).map((n) => [f.split('/src/')[1], n] as const));
  it('sees icons (positive control on the scanner) and the sprite would catch a missing one', () => {
    expect(used.length).toBeGreaterThan(5);
    expect(namedIcons(`<Icon name="om-1f9ff" /> 'c-not-drawn'`)).toEqual(['om-1f9ff', 'c-not-drawn']);
    expect(sprite.has('om-1f9ff')).toBe(false);
  });
  it.each(used)('%s uses %s', (_f, n) => expect(sprite.has(n)).toBe(true));
});
