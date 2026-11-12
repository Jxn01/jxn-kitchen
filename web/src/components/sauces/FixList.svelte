<script lang="ts">
  // The fix-it ledger: for what can go wrong with this sauce (lumpy, split, curdled, too salty, too thin…), the cure the
  // know-how teaches — the engine picks them, the web only lists them. A fixed pool of cards (lib/engine pool).
  import { pool } from '../../lib/engine';
  import { SAUCE_SLOTS, type Fix } from '../../lib/sauces';
  import type { Lang } from '../../lib/i18n';
  let { fixes, lang }: { fixes: Fix[]; lang: Lang } = $props();
</script>

<ul class="fixes">
  {#each pool(fixes, SAUCE_SLOTS.fixes) as f, k (k)}
    <li class="fix {f?.axis ?? ''}" class:gone={!f}>
      <b>{f ? f.label[lang] : ''}</b>
      <span>{f ? f[lang] : ''}</span>
    </li>
  {/each}
</ul>

<style>
  .fixes { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .gone { display: none !important; }
  .fix { contain: content; display: flex; flex-direction: column; gap: 2px; padding: 8px 12px 8px 16px; border: var(--outline) solid var(--ink);
         border-radius: var(--r-sm); background: var(--paper); position: relative; font-weight: 700; font-size: 15px; line-height: 1.3; }
  .fix::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 7px; border-radius: var(--r-sm) 0 0 var(--r-sm); background: var(--butter); }
  .fix.body::before { background: #FFC98B; } .fix.stability::before { background: #FF826E; } .fix.salt::before { background: #CFE8F2; }
  .fix.acid::before { background: #E3F28B; } .fix.fat::before { background: #F2D86B; }
  .fix b { font-weight: 900; }
</style>
