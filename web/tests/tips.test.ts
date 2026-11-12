import { describe, expect, it } from 'vitest';
import lib from './fixtures/knowhow.json';
import { TIPS } from '../src/lib/tips';
import { parse } from '../src/lib/router';

// The mascot's tips link to know-how pages: every link must exist, both languages must be there, and a tip must fit
// the speech bubble (kept short on purpose).
describe('the mascot\'s tips', () => {
  const pages = new Set((lib as { id: string; pages: { id: string }[] }[]).flatMap((s) => s.pages.map((p) => `${s.id}/${p.id}`)));
  it('every tip links to a real page, in both languages, short enough for the bubble', () => {
    expect(TIPS.length).toBeGreaterThanOrEqual(30);
    for (const t of TIPS) {
      if (t.to.startsWith('/')) expect(parse(`#${t.to}`).name, t.to).not.toBe('home');   // an app route the router knows
      else expect(pages.has(t.to), t.to).toBe(true);
      expect(t.en.length, t.en).toBeLessThanOrEqual(95);
      expect(t.hu.length, t.hu).toBeLessThanOrEqual(95);
      expect(t.hu).not.toBe(t.en);
    }
  });
});
