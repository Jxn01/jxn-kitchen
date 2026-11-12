<script lang="ts">
  // The Why ledger: every finding, best and worst first, with the points it moves — the lines add up to the score.
  // A line about a pair or about jars is a button: tapping it lights those jars in the web. The lines are a fixed pool
  // (lib/spices pool): every answer only fills them — lines keyed by the finding were rebuilt on every answer.
  import { pool, SLOTS, type Finding } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  import { t } from '../../lib/i18n';
  let { findings, lang, base = 50, picked = null, onpick, baseKey = 'spices.ledger.base' }:
    { findings: Finding[]; lang: Lang; base?: number; picked?: string | null; onpick?: (f: Finding | null) => void; baseKey?: string } = $props();
  const MARK: Record<string, string> = { good: '+', warn: '−', notice: '!', info: 'i' };
</script>

<ol class="ledger">
  <li class="row base"><span class="mark">=</span><span class="txt">{$t(baseKey)}</span><b class="w">{base}</b></li>
  {#each pool(findings, SLOTS.findings) as f, i (i)}
    <li class:gone={!f}>
      <button class="row {f?.kind ?? 'info'} pressable" class:on={!!f && picked === f.id} disabled={!f || !f.about.length || !onpick}
              onclick={() => { if (f) onpick?.(picked === f.id ? null : f); }}>
        <span class="mark">{f ? MARK[f.kind] : ''}</span>
        <span class="txt">{f ? f[lang] : ''}</span>
        <b class="w">{!f ? '' : f.weight > 0 ? `+${f.weight}` : f.weight < 0 ? `−${-f.weight}` : '·'}</b>
      </button>
    </li>
  {/each}
</ol>

<style>
  .gone { display: none; }
  .ledger { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .row { contain: content; width: 100%; min-height: var(--touch); display: flex; align-items: center; gap: 10px; padding: 6px 12px; text-align: left;
         border: var(--outline) solid var(--ink); border-radius: var(--r-sm); background: var(--paper); font: inherit; color: var(--ink); }
  button.row:disabled { opacity: 1; cursor: default; }
  .row.base { background: var(--cream); border-style: dashed; font-weight: 800; }
  .good { background: #DDF3DE; } .warn { background: #FFD9CE; } .notice { background: #FFF1B8; } .info { background: var(--paper); }
  .row.on { box-shadow: inset 0 0 0 3px var(--ink); transform: translateY(1px); }
  .mark { flex: none; width: 30px; height: 30px; border-radius: 50%; border: 2.5px solid var(--ink); display: grid; place-items: center;
          font-weight: 900; font-size: 17px; background: var(--paper); line-height: 1; }
  .txt { flex: 1; min-width: 0; font-weight: 700; font-size: 15px; line-height: 1.3; }
  .w { flex: none; min-width: 42px; text-align: right; font-family: var(--font-display); font-weight: 400; font-size: 20px; }
</style>
