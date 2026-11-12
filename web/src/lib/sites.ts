// Browse's sites: the verified built-in list (sites.json) in the order the settings give, then the user's own.
import data from './sites.json';
import { P } from './palette';

export interface Site { id: string; name: string; url: string; search: string | null; color: string }
export const BUILT_IN: Site[] = data.sites.map((s) => ({ ...s, color: (P as Record<string, string>)[s.color] ?? P.sky }));

export function siteList(enabled: string[], custom: { name: string; url: string }[]): Site[] {
  const byId = new Map(BUILT_IN.map((s) => [s.id, s]));
  const own = custom.map((c, i) => ({ id: `custom-${i}`, name: c.name, url: c.url, search: null, color: P.plum }));
  return [...enabled.map((id) => byId.get(id)).filter((s): s is Site => !!s), ...own];
}

/** The site's search page for `q`, or null when the site takes no search in its URL (open it and use its own box). */
export function searchUrl(site: Site, q: string): string | null {
  const t = q.trim();
  return site.search && t ? site.search.replace('{q}', encodeURIComponent(t)) : null;
}

/** "https://example.hu/blog" -> ok; anything else is not a web link we will open. */
export function isWebLink(u: string): boolean {
  try { const x = new URL(u.trim()); return x.protocol === 'https:' || x.protocol === 'http:'; } catch { return false; }
}
