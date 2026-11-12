/// <reference types="node" />
import { describe, expect, it } from 'vitest';
import { renderMd, plainText } from '../src/lib/md';

describe('the know-how Markdown subset', () => {
  it('escapes everything first: no HTML gets through', () => {
    const out = renderMd('<img src=x onerror=alert(1)> **<b>bold</b>** [x](javascript:alert(1))');
    expect(out).not.toContain('<img');
    expect(out).not.toContain('<b>bold</b>');
    expect(out).toContain('&lt;img');
    expect(out).toContain('<strong>&lt;b&gt;bold&lt;/b&gt;</strong>');
    expect(out).not.toMatch(/href/);
  });
  it('headings, paragraphs, lists, bold, italics', () => {
    const out = renderMd('## Title\n\nSome **bold** and *it* text\nwrapped.\n\n- one\n- two\n\n1. first\n2. second');
    expect(out).toBe('<h3>Title</h3><p>Some <strong>bold</strong> and <em>it</em> text wrapped.</p><ul><li>one</li><li>two</li></ul><ol><li>first</li><li>second</li></ol>');
  });
  it('a list item can wrap onto indented lines', () => {
    expect(renderMd('- a long\n  item\n- b')).toBe('<ul><li>a long item</li><li>b</li></ul>');
  });
  it('tables with a header row', () => {
    expect(renderMd('| A | B |\n|---|---|\n| 1 | **2** |')).toBe(
      '<div class="tbl"><table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td><strong>2</strong></td></tr></tbody></table></div>');
  });
  it('a > tip is a tip card', () => {
    expect(renderMd('> Rest the meat.')).toBe('<aside class="tip">Rest the meat.</aside>');
  });
  it('plain text for search drops the markup', () => {
    expect(plainText('## Rántás\n| a | **b** |\n|---|---|\n- *x*')).toBe('Rántás a b x');
  });
});

import lib from './fixtures/knowhow.json';

describe('every real know-how page renders cleanly', () => {
  for (const s of lib as any[]) for (const p of s.pages) for (const lang of ['en', 'hu']) {
    it(`${s.id}/${p.id} (${lang})`, () => {
      const html = renderMd(p[lang].body);
      expect(html.length).toBeGreaterThan(40);
      expect(html).not.toMatch(/\*\*|\|\s*---|^\||<p>\s*\|/m);          // no markup left unrendered
      expect(html).not.toMatch(/<(?!\/?(h3|h4|h5|p|ul|ol|li|strong|em|div|table|thead|tbody|tr|th|td|aside)[ >])/);
    });
  }
});

describe('{@html} only ever renders escaped Markdown', () => {
  it('source scan: every {@html} is {@html renderMd(...)}', async () => {
    const { readdirSync, readFileSync, statSync } = await import('node:fs');
    const { join } = await import('node:path');
    const walk = (d: string): string[] => readdirSync(d).flatMap((f) => statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]);
    const bad = walk(join(__dirname, '../src')).filter((f) => f.endsWith('.svelte'))
      .flatMap((f) => [...readFileSync(f, 'utf8').matchAll(/\{@html\s+([^}]*)\}/g)].filter((m) => !m[1].startsWith('renderMd(')).map((m) => `${f}: ${m[0]}`));
    expect(bad).toEqual([]);
  });
});
