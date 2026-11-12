import { describe, expect, it } from 'vitest';
import { shouldReload } from '../src/lib/update';

describe('shouldReload', () => {
  it('reloads once when the server runs a different build', () => {
    expect(shouldReload('b2', 'b1', null)).toBe(true);
    expect(shouldReload('b2', 'b1', 'b2')).toBe(false);      // already tried for b2: no reload loop
  });
  it('never for the same build, a missing build, or a dev server', () => {
    expect(shouldReload('b1', 'b1', null)).toBe(false);
    expect(shouldReload(undefined, 'b1', null)).toBe(false);
    expect(shouldReload('dev', 'b1', null)).toBe(false);
  });
});
