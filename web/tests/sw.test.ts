import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
// @ts-ignore — plain JS module shared with the service worker
import { cacheFor, DATA_CACHE, fallbackKeys, fontUrls, isShell, shellAssets, staleImageKeys, strategyFor, usable } from '../public/sw-strategy.js';

const O = 'https://kitchen.example.com';
describe('service worker routing', () => {
  it.each([
    [`${O}/api/events`, 'GET', 'cors', 'bypass'],
    [`${O}/api/health`, 'GET', 'cors', 'bypass'],
    [`${O}/api/settings`, 'PUT', 'cors', 'bypass'],
    [`${O}/api/settings`, 'GET', 'cors', 'network-first'],
    [`${O}/api/weather`, 'GET', 'cors', 'network-first'],
    [`${O}/`, 'GET', 'navigate', 'network-first'],
    [`${O}/#/settings`, 'GET', 'navigate', 'network-first'],
    [`${O}/api/health`, 'GET', 'navigate', 'bypass'],
    [`${O}/api/images/3-1700000000000.jpg`, 'GET', 'no-cors', 'cache-first'],
    [`${O}/assets/index-abc123.js`, 'GET', 'cors', 'cache-first'],
    [`${O}/sprite.svg`, 'GET', 'no-cors', 'cache-first'],
    [`${O}/fonts/archivo-latin.woff2`, 'GET', 'cors', 'cache-first'],
    ['https://www.nosalty.hu/recept/x', 'GET', 'navigate', 'bypass'],
  ])('%s %s %s -> %s', (url, method, mode, want) => {
    expect(strategyFor(new URL(url), method, mode, O)).toBe(want);
  });
});

describe('usable (review I3: a 502 from Caddy used to replace the cached app)', () => {
  it.each([[200, true], [404, true], [422, true], [500, false], [502, false], [503, false]])('%i -> %s', (status, want) => {
    expect(usable({ status })).toBe(want);
  });
  it('no response is not usable', () => expect(usable(null)).toBe(false));
  it('only the app page is the shell', () => {
    expect(isShell(new URL(`${O}/`))).toBe(true);
    expect(isShell(new URL(`${O}/api/health`))).toBe(false);
  });
});

describe('the data cache (item 5: a deploy no longer empties the kiosk\'s offline copy)', () => {
  it('API answers and photos go to the deploy-proof cache; the shell and its assets stay per build', () => {
    expect(DATA_CACHE).toBe('kitchen-data');
    expect(DATA_CACHE.startsWith('kitchen-')).toBe(true);   // so sw.js activate must spare it explicitly:
    const sw = readFileSync(join(__dirname, '../public/sw.js'), 'utf8');
    expect(sw).toMatch(/key\.startsWith\('kitchen-'\) && key !== SHELL_CACHE && key !== DATA_CACHE/);
    for (const p of ['/api/recipes/3', '/api/images/3-1.jpg', '/api/settings']) expect(cacheFor(new URL(O + p))).toBe('data');
    for (const p of ['/', '/assets/index-abc.js', '/sprite.svg', '/fonts/a.woff2']) expect(cacheFor(new URL(O + p))).toBe('shell');
  });
  it('a recipe or blend at another size falls back to its default copy; nothing else does', () => {
    expect(fallbackKeys(new URL(`${O}/api/recipes/3?servings=6`))).toEqual([`${O}/api/recipes/3?servings=6`, `${O}/api/recipes/3`]);
    expect(fallbackKeys(new URL(`${O}/api/blends/9?batch_tbsp=4`))).toEqual([`${O}/api/blends/9?batch_tbsp=4`, `${O}/api/blends/9`]);
    expect(fallbackKeys(new URL(`${O}/api/recipes/3`))).toEqual([`${O}/api/recipes/3`]);
    expect(fallbackKeys(new URL(`${O}/api/recipes?q=leves`))).toEqual([`${O}/api/recipes?q=leves`]);
  });
  it('only photos the warm-up no longer lists are pruned', () => {
    const cached = [`${O}/api/images/1-a.jpg`, `${O}/api/images/2-b.jpg`, `${O}/api/recipes/1`, `${O}/api/recipes?q=x`];
    expect(staleImageKeys(cached, [`${O}/api/images/1-a.jpg`, `${O}/api/recipes/1`])).toEqual([`${O}/api/images/2-b.jpg`]);
  });
});

describe('the shell a build precaches (2026-11-12: the kiosk\'s build cache held no app code)', () => {
  const html = '<link rel="icon" href="/favicon.svg"><link rel="preload" href="/fonts/archivo-latin.woff2" as="font">'
    + '<script type="module" crossorigin src="/assets/index-BNF1_toA.js"></script>'
    + '<link rel="stylesheet" crossorigin href="/assets/index-Cd2Cjz81.css"><link rel="manifest" href="/manifest.webmanifest">'
    + '<link rel="preload" href="/fonts/archivo-latin.woff2" as="font">';
  it('the page\'s hashed assets and preloaded fonts, once each; nothing else', () => {
    expect(shellAssets(html)).toEqual(['/fonts/archivo-latin.woff2', '/assets/index-BNF1_toA.js', '/assets/index-Cd2Cjz81.css']);
  });
  it('the fonts a stylesheet loads, quoted or not; data: URLs ignored', () => {
    const css = '@font-face{src:url(/fonts/archivo-latin.woff2) format("woff2")}@font-face{src:url("/fonts/alfa-slab-one-latin-ext.woff2")}'
      + '.x{background:url("data:image/svg+xml,%3Csvg%3E")}@font-face{src:url(\'/fonts/archivo-latin.woff2\')}';
    expect(fontUrls(css)).toEqual(['/fonts/archivo-latin.woff2', '/fonts/alfa-slab-one-latin-ext.woff2']);
  });
  it('sw.js installs by precaching that shell, page last', () => {
    const sw = readFileSync(join(__dirname, '../public/sw.js'), 'utf8');
    expect(sw).toMatch(/event\.waitUntil\(precacheShell\(\)/);
    expect(sw.indexOf("cache.put('/', page)")).toBeGreaterThan(sw.indexOf('cache.addAll('));
  });
});
