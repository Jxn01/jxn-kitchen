import { describe, expect, it } from 'vitest';
import { applyKey, LAYOUTS } from '../src/lib/keyboard-layouts';

const letters = (rows: any[][]) => rows.flat().filter((k) => typeof k === 'string').join('');

describe('keyboard layouts', () => {
  it('hu has every Hungarian accented letter', () => {
    for (const c of 'öüóőúéáűí') expect(letters(LAYOUTS.hu)).toContain(c);
  });
  it('en is QWERTY and hu is QWERTZ', () => {
    expect(letters(LAYOUTS.en).startsWith('qwerty')).toBe(true);
    expect(letters(LAYOUTS.hu).startsWith('qwertz')).toBe(true);
  });
  it('applies keys', () => {
    expect(applyKey('', 'ő', true)).toBe('Ő');
    expect(applyKey('pa', 's', false)).toBe('pas');
    expect(applyKey('', 'back', false)).toBe('');
    expect(applyKey('ab', 'back', false)).toBe('a');
    expect(applyKey('a', 'space', false)).toBe('a ');
  });
});
