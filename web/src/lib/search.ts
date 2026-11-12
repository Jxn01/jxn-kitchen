// Catalogue types + accent/case-insensitive search. fold() MUST equal server/kitchen/catalogue.py fold() — both are
// tested against web/tests/fixtures/fold_cases.json.
export interface CatItem { id: string; en: string; hu: string; icon: string | null; gluten: 'free' | 'contains' | 'label'; aliases?: string[]; staple?: boolean }
export interface CatGroup { id: string; en: string; hu: string; icon: string; items: CatItem[] }
export interface CatCategory { id: string; en: string; hu: string; icon: string; color: string; kind: 'food' | 'supply'; groups: CatGroup[] }
export interface Cat { categories: CatCategory[] }

export function fold(s: string): string {
  return s.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase().replace(/\s+/g, ' ').trim();
}

export interface Hit {
  kind: 'item' | 'group';
  id: string;
  category: CatCategory;
  group: CatGroup;
  item?: CatItem;
  score: number;
}

function scoreName(q: string, name: string, base: number): number {
  const n = fold(name);
  if (n === q) return base + 300;
  if (n.startsWith(q)) return base + 200;
  if (n.split(' ').some((w) => w.startsWith(q))) return base + 150;
  if (n.includes(q)) return base + 100;
  return 0;
}

/** Ranked: exact > prefix > word-prefix > substring; display names slightly above aliases; items above groups. */
export function search(cat: Cat, query: string, limit = 40): Hit[] {
  const q = fold(query);
  if (!q) return [];
  const hits: Hit[] = [];
  for (const category of cat.categories) {
    for (const group of category.groups) {
      const gs = Math.max(scoreName(q, group.en, 5), scoreName(q, group.hu, 5));
      if (gs) hits.push({ kind: 'group', id: group.id, category, group, score: gs });
      for (const item of group.items) {
        const ns = Math.max(scoreName(q, item.en, 20), scoreName(q, item.hu, 20));
        const as = Math.max(0, ...(item.aliases ?? []).map((a) => scoreName(q, a, 10)));
        const score = Math.max(ns, as);
        if (score) hits.push({ kind: 'item', id: item.id, category, group, item, score });
      }
    }
  }
  return hits.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id)).slice(0, limit);
}

export function nameOf(n: { en: string; hu: string }, lang: 'en' | 'hu'): string {
  return lang === 'hu' ? n.hu : n.en;
}
