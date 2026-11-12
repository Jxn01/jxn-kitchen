/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

// The look: OpenMoji icons from our sprite, NEVER emoji glyphs — on the kiosk's Windows a glyph falls
// back to Segoe UI Emoji and sits there in colour, off-style. Typographic symbols (✓ ✕ ✎ ⌫ ▶ →) are fine: they render as plain text.
const EMOJI = /[\u{1F000}-\u{1FAFF}\u{FE0F}⌚⌛⏩-⏳⏸-⏺☔☕⚡⭐✅❌✨]/u;
const stripComments = (s: string) => s.replace(/<!--[\s\S]*?-->/g, '').replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/.*$/gm, '$1');

describe('no emoji glyphs in the UI', () => {
  it('positive control: the pattern catches the glyphs that slipped in', () => {
    for (const g of ['💡', '⏱', '⏲']) expect(EMOJI.test(g), g).toBe(true);
    for (const g of ['✓', '✕', '✎', '⌫', '▶', '→']) expect(EMOJI.test(g), g).toBe(false);
  });
  it('no source file or string table shows one', () => {
    const walk = (d: string): string[] => readdirSync(d).flatMap((f) => statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]);
    const bad = walk(join(__dirname, '../src'))
      .filter((f) => /\.(svelte|ts|json|css)$/.test(f) && !f.endsWith('icons.json'))
      .flatMap((f) => stripComments(readFileSync(f, 'utf8')).split('\n').flatMap((l, i) => EMOJI.test(l) ? [`${f}:${i + 1}: ${l.trim()}`] : []));
    expect(bad).toEqual([]);
  });
});
