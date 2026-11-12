/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { P } from '../src/lib/palette';
import { contrast, INK, textOn } from '../src/lib/color';
import sites from '../src/lib/sites.json';

// White text on tiles is hard to read, so every palette colour carries ink text at >= 7:1, and white text sits only on ink.
const src = join(__dirname, '../src');
const walk = (d: string): string[] => readdirSync(d).flatMap((f) => statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]);

describe('the palette', () => {
  it('palette.ts and tokens.css hold the same colours', () => {
    const css = readFileSync(join(src, 'lib/tokens.css'), 'utf8');
    for (const [k, v] of Object.entries(P)) {
      const m = new RegExp(`--${k}:\\s*(#[0-9A-Fa-f]{6});`).exec(css);
      expect(m?.[1]?.toUpperCase(), k).toBe(v.toUpperCase());
    }
  });
  it('every colour but ink takes ink text at >= 7:1', () => {
    for (const [k, v] of Object.entries(P)) {
      if (k === 'ink') continue;
      expect(contrast(INK, v), k).toBeGreaterThanOrEqual(7);
      expect(textOn(v), k).toBe(INK);
    }
  });
  it('positive control: the old plum would have failed', () => {
    expect(contrast(INK, '#8E4FBF')).toBeLessThan(7);
    expect(textOn('#8E4FBF')).toBe('#FFFFFF');
  });
  it('no Browse site tile is ink-black', () => {
    expect(sites.sites.filter((s: { color: string }) => s.color === 'ink')).toEqual([]);
  });
});

// A CSS rule that sets white text and a background that is not ink (rule level; inherited colour is checked by eye).
const WHITE = /color:\s*(#fff\b|#ffffff\b|white\b)/i;
const INK_BG = /background(?:-color)?:\s*[^;]*(var\(--ink\)|#1f1a17)/i;
function whiteOnColour(text: string): string[] {
  const bad: string[] = [];
  for (const m of text.matchAll(/([^{}]*)\{([^{}]*)\}/g)) {
    const [, sel, body] = m;
    if (WHITE.test(body) && /background/.test(body) && !INK_BG.test(body) && !/night/.test(sel)) bad.push(sel.trim());
  }
  return bad;
}

describe('white text only on ink', () => {
  it('positive control: the old green button is caught, an ink pill is not', () => {
    expect(whiteOnColour('.go { background: var(--herb); color: #fff; }')).toEqual(['.go']);
    expect(whiteOnColour('.pill { background: var(--ink); color: #fff; }')).toEqual([]);
  });
  it('no stylesheet pairs white text with a coloured background', () => {
    const files = walk(src).filter((f) => f.endsWith('.svelte') || f.endsWith('overlay/main.ts'));
    const bad = files.flatMap((f) => whiteOnColour(readFileSync(f, 'utf8')).map((s) => `${f}: ${s}`));
    expect(bad).toEqual([]);
  });
});
