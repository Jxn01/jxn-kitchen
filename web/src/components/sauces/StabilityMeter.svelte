<script lang="ts">
  // What could go wrong in the pot: every stability line the engine wrote (an emulsion's load, curdling, a starch's
  // limits, raw egg, garlic in oil), each with a small dial — fine, at the limit, careful — its kind and its sentence.
  // A fixed pool of rows (lib/engine pool): an answer only fills them; the dials are static svgs whose needle is set
  // by an attribute. The "nothing to watch" line is always there, shown by class.
  import { pool } from '../../lib/engine';
  import { SAUCE_SLOTS, type Level, type Stability } from '../../lib/sauces';
  import type { Labelled } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  import { t } from '../../lib/i18n';
  let { items, kinds, levels, lang, blank = false }:
    { items: Stability[]; kinds: Labelled[]; levels: Labelled[]; lang: Lang; blank?: boolean } = $props();
  const ANGLE: Record<Level, number> = { ok: -55, 'at-limit': 0, warn: 55 };
  const kindName = (id: string) => kinds.find((k) => k.id === id)?.[lang] ?? id;
  const levelName = (id: string) => levels.find((k) => k.id === id)?.[lang] ?? id;
</script>

<ul class="meter">
  {#each pool(items, SAUCE_SLOTS.stability) as s, k (k)}
    <li class="row {s?.level ?? 'ok'}" class:gone={!s}>
      <svg class="dial" viewBox="0 0 60 36" width="66" height="40" aria-hidden="true">
        <path class="arc ok" d="M6,32 A24,24 0 0 1 18,11" />
        <path class="arc at" d="M20,10 A24,24 0 0 1 40,10" />
        <path class="arc warn" d="M42,11 A24,24 0 0 1 54,32" />
        <line class="needle" x1="30" y1="32" x2="30" y2="12" transform="rotate({ANGLE[s?.level ?? 'ok']} 30 32)" />
        <circle class="hub" cx="30" cy="32" r="4" />
      </svg>
      <div class="txt">
        <b>{s ? kindName(s.kind) : ''}<span class="lv">{s ? levelName(s.level) : ''}</span></b>
        <span>{s ? s[lang] : ''}</span>
      </div>
    </li>
  {/each}
  <li class="none" class:gone={blank || items.length > 0}>{$t('sauce.stability.none')}</li>
</ul>

<style>
  .meter { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .gone { display: none !important; }
  .row { contain: content; display: flex; align-items: center; gap: 10px; padding: 6px 12px; border: var(--outline) solid var(--ink);
         border-radius: var(--r-sm); background: var(--paper); }
  .row.ok { background: #DDF3DE; } .row.at-limit { background: #FFF1B8; } .row.warn { background: #FFD9CE; }
  .dial { flex: none; display: block; }
  .arc { fill: none; stroke-width: 7; stroke-linecap: butt; }
  .arc.ok { stroke: #7CC47F; } .arc.at { stroke: #FFD23F; } .arc.warn { stroke: #FF826E; }
  .needle { stroke: var(--ink); stroke-width: 3.4; stroke-linecap: round; }
  .hub { fill: var(--ink); }
  .txt { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; font-weight: 700; font-size: 15px; line-height: 1.3; }
  .txt b { font-weight: 900; font-size: 15px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .lv { font-size: 12px; font-weight: 900; border: 2px solid var(--ink); border-radius: 999px; padding: 0 8px; background: var(--paper); }
  .none { font-weight: 800; font-size: 15px; padding: 12px 14px; border: var(--outline) dashed #7CC47F; border-radius: var(--r-sm); background: #EEF8EE; }
</style>
