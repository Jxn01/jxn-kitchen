// The palette as hex values for code that needs them (contrast, per-category colours). Mirrors tokens.css (tested).
// Every colour carries INK text at >= 7:1 (white text on tiles was hard to read) — tested.
export const P = {
  ink: '#1F1A17', cream: '#FFF4DF', tomato: '#FF826E', mustard: '#F2B705', herb: '#62C46A', sky: '#5BB5F0',
  tangerine: '#F28C28', berry: '#F57FB0', teal: '#33C5B5', plum: '#C39BF2', cocoa: '#D6A27C', butter: '#FFD23F',
  slate: '#A6B8C9', salmon: '#FFB49A', leaf: '#A6D96A', olive: '#C9C45A', wine: '#E79AE0',
  rust: '#F49A5C', mint: '#7DDCB5', indigo: '#94A3F7',
} as const;

export function color(key: string): string {
  return (P as Record<string, string>)[key] ?? P.slate;
}
/** A chart's drawing colour (server/kitchen/charts.py: a palette name or #RRGGBB) as a CSS colour. */
export function paint(v: string): string {
  return v.startsWith('#') ? v : color(v);
}
