// The know-how library's Markdown subset (knowhow/*.yaml bodies): `## heading`, paragraphs, `- ` and `1. ` lists
// (items may wrap onto indented lines), `**bold**`, `*italic*`, `| tables |` with a header row, and `> tip` cards.
// EVERYTHING is HTML-escaped first; only this file's own tags are emitted — no raw HTML, no links, no attributes
// from the content. (Tested in md.test.ts.)

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function inline(s: string): string {
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, '$1<em>$2</em>');
}

const isTableRow = (l: string) => /^\s*\|.*\|\s*$/.test(l);
const isRule = (l: string) => /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/.test(l);
const cells = (l: string) => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());

export function renderMd(src: string): string {
  const lines = src.replace(/\r/g, '').split('\n');
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    const h = /^(#{2,4})\s+(.*)$/.exec(line);
    if (h) { out.push(`<h${h[1].length + 1}>${inline(h[2])}</h${h[1].length + 1}>`); i++; continue; }
    if (isTableRow(line)) {
      const rows: string[][] = [];
      let head: string[] | null = null;
      while (i < lines.length && isTableRow(lines[i])) {
        if (isRule(lines[i])) { if (!head && rows.length) head = rows.pop()!; i++; continue; }
        rows.push(cells(lines[i]));
        i++;
      }
      const tr = (r: string[], tag: string) => `<tr>${r.map((c) => `<${tag}>${inline(c)}</${tag}>`).join('')}</tr>`;
      out.push(`<div class="tbl"><table>${head ? `<thead>${tr(head, 'th')}</thead>` : ''}<tbody>${rows.map((r) => tr(r, 'td')).join('')}</tbody></table></div>`);
      continue;
    }
    if (/^>\s?/.test(line)) {
      const parts: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) { parts.push(lines[i].replace(/^>\s?/, '')); i++; }
      out.push(`<aside class="tip">${inline(parts.join(' '))}</aside>`);
      continue;
    }
    const ul = /^\s*[-*]\s+/, ol = /^\s*\d+[.)]\s+/;
    if (ul.test(line) || ol.test(line)) {
      const ordered = ol.test(line);
      const marker = ordered ? ol : ul;
      const items: string[] = [];
      while (i < lines.length && lines[i].trim()) {
        if (marker.test(lines[i])) items.push(lines[i].replace(marker, ''));
        else if (/^\s+\S/.test(lines[i]) && items.length) items[items.length - 1] += ' ' + lines[i].trim();
        else break;
        i++;
      }
      const tag = ordered ? 'ol' : 'ul';
      out.push(`<${tag}>${items.map((it) => `<li>${inline(it)}</li>`).join('')}</${tag}>`);
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^(#{2,4}\s|>|\s*[-*]\s|\s*\d+[.)]\s)/.test(lines[i]) && !isTableRow(lines[i])) {
      para.push(lines[i].trim());
      i++;
    }
    out.push(`<p>${inline(para.join(' '))}</p>`);
  }
  return out.join('');
}

/** The words of a body, for search: markup and table pipes removed. */
export function plainText(src: string): string {
  return src
    .replace(/^\s*\|?\s*:?-{3,}.*$/gm, ' ')
    .replace(/[#>*|]/g, ' ')
    .replace(/^\s*[-]\s+/gm, ' ')
    .replace(/^\s*\d+[.)]\s+/gm, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
