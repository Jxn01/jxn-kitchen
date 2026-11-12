import { describe, expect, it } from 'vitest';
import { fmtDate, fmtTime } from '../src/lib/i18n';
import { msToNextMinute } from '../src/lib/clock';

describe('Budapest time', () => {
  it('formats across a DST change', () => {
    expect(fmtTime(new Date('2026-10-25T00:30:00Z'))).toBe('02:30');   // CEST (UTC+2)
    expect(fmtTime(new Date('2026-10-25T01:30:00Z'))).toBe('02:30');   // CET (UTC+1), the repeated hour
    expect(fmtTime(new Date('2026-10-10T10:14:00Z'))).toBe('12:14');
  });
  it('dates in both languages', () => {
    const d = new Date('2026-10-10T10:00:00Z');
    expect(fmtDate(d, 'hu')).toBe('október 10., szombat');
    expect(fmtDate(d, 'en')).toBe('Saturday, October 10');
  });
  it('the date flips at Budapest midnight, not UTC midnight', () => {
    expect(fmtDate(new Date('2026-10-10T22:30:00Z'), 'en')).toBe('Sunday, October 11');
  });
});

describe('msToNextMinute', () => {
  it('waits to the next minute boundary', () => {
    expect(msToNextMinute(new Date('2026-10-10T10:14:59.999Z'))).toBe(1);
    expect(msToNextMinute(new Date('2026-10-10T10:14:00.000Z'))).toBe(60000);
    expect(msToNextMinute(new Date('2026-10-10T10:14:30.250Z'))).toBe(29750);
  });
});
