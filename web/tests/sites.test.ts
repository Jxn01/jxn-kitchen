import { describe, expect, it } from 'vitest';
import { BUILT_IN, isWebLink, searchUrl, siteList } from '../src/lib/sites';

describe('browse sites', () => {
  it('follow the enabled order, then the custom ones', () => {
    const l = siteList(['receptneked', 'nosalty'], [{ name: 'Mentes', url: 'https://mentes.example/' }]);
    expect(l.map((s) => s.id)).toEqual(['receptneked', 'nosalty', 'custom-0']);
    expect(siteList(['gone'], []).length).toBe(0);
  });
  it('search URLs are encoded; a site without a template gives null', () => {
    const nos = BUILT_IN.find((s) => s.id === 'nosalty')!;
    expect(searchUrl(nos, 'túrós csusza')).toBe('https://www.nosalty.hu/kereses/recept/t%C3%BAr%C3%B3s%20csusza');
    expect(searchUrl(BUILT_IN.find((s) => s.id === 'mindmegette')!, 'x')).toBeNull();
    expect(searchUrl(nos, '  ')).toBeNull();
  });
  it('only web links', () => {
    expect(isWebLink('https://x.hu/a')).toBe(true);
    expect(isWebLink('javascript:alert(1)')).toBe(false);
    expect(isWebLink('nosalty.hu')).toBe(false);
  });
});
