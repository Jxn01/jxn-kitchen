// WCAG contrast: tiles pick ink or white text, whichever reads better on their colour (spec §5).
export const INK = '#1F1A17';

function lum(hex: string): number {
  const c = hex.replace('#', '');
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(c.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

export function textOn(bg: string): string {
  return contrast(INK, bg) >= contrast('#FFFFFF', bg) ? INK : '#FFFFFF';
}
