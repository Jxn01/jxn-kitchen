// The Atom guards both engines' screens are held to (SP10, measured on the kiosk, 2026-10-19): source checks shared by
// spices-ui.test.ts and sauces-ui.test.ts, so a rule tightened for one is tightened for both. Each has a positive control
// in those files.

/** An {#if} that a tap flips creates its contents on that tap: no OpenMoji <Icon> may live inside one (a check mark on
 *  the rack cost ~400 ms a tap on the kiosk). Screens only show icons that are always there. */
export const iconsInIfBlocks = (src: string) =>
  [...src.matchAll(/\{#if [^}]*\}([\s\S]*?)\{\/if\}/g)].filter((m) => m[1].includes('<Icon')).length;

/** The lists an engine answer (or the editor's tray) refills. Every one reuses its rows BY PLACE — keyed by the index,
 *  never by what a row shows (rows keyed by the finding or the classic were all rebuilt on every answer: 56–76 ms of the
 *  kiosk's slowest frames) — and is a FIXED POOL (lib/engine pool): a list keyed by place still built rows whenever it
 *  grew past its longest yet (the first answers after the page opened, 84 ms frames). A filtered index (`shown`: a chip,
 *  a letter in the search) is one too — going back to All built eleven vessels in one frame (104 ms). */
export const FED = /findings|classics|cuisines|vouchers|missing|extra|\bids\b|suggest|stability|fixes|\btray\b|\blines\b|\bshown\b/;
// the key may call something — `(lineKey(l))` slipped past a key pattern that stopped at the first `)`
const EACH = /\{#each\s+([^}]*?)\s+as\s+([^,(}]+?)(?:,\s*(\w+))?\s*\(((?:[^()]|\([^()]*\))*)\)\s*\}/g;
export const contentKeyed = (src: string) => [...src.matchAll(EACH)]
  .filter((m) => FED.test(m[1]) && (m[4].trim() !== (m[3] ?? '').trim() || !/\bpool\(/.test(m[1]))).map((m) => m[0]);
