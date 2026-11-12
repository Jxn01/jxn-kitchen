// The six home tiles (Shopping and Cook are round buttons beside Settings; Spices and Sauces took their
// places). Each leads to its section (a tile with no route shows the "being built" card).
import { P } from './palette';

export interface HomeTile { id: string; icon: string; color: string; title: string; sub: string; route?: string }

export const HOME_TILES: HomeTile[] = [
  { id: 'recipes', icon: 'recipes', color: P.tomato, title: 'home.recipes', sub: 'home.recipes.count', route: '/recipes' },
  { id: 'pantry', icon: 'pantry', color: P.mustard, title: 'home.pantry', sub: 'home.pantry.count', route: '/pantry' },
  { id: 'spices', icon: 'spices', color: P.tangerine, title: 'home.spices', sub: 'home.spices.count', route: '/spices' },
  { id: 'browse', icon: 'browse', color: P.sky, title: 'home.browse', sub: 'home.browse.sub', route: '/browse' },
  { id: 'knowhow', icon: 'knowhow', color: P.plum, title: 'home.knowhow', sub: 'home.knowhow.sub', route: '/knowhow' },
  { id: 'sauces', icon: 'sauces', color: P.teal, title: 'home.sauces', sub: 'home.sauces.count', route: '/sauces' },
];
