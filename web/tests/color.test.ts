import { describe, expect, it } from 'vitest';
import { contrast, INK, textOn } from '../src/lib/color';

describe('textOn', () => {
  it('picks the better of ink and white', () => {
    expect(textOn('#FFD23F')).toBe(INK);        // butter
    expect(textOn('#F2B705')).toBe(INK);        // mustard
    expect(textOn('#8E4FBF')).toBe('#FFFFFF');  // plum
    expect(textOn('#1F1A17')).toBe('#FFFFFF');
  });
  it('contrast is symmetric and black/white is 21', () => {
    expect(contrast('#000000', '#FFFFFF')).toBeCloseTo(21, 0);
    expect(contrast('#E8442E', INK)).toBeCloseTo(contrast(INK, '#E8442E'), 6);
  });
});
