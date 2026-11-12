<script lang="ts">
  // The mascot's speech bubble on the home screen: one kitchen tip (lib/tips.ts); tap it to open the know-how page it
  // comes from. Pops in (scale from the tail), goes away by itself. Transform/opacity only.
  import type { Tip } from '../lib/tips';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  let { tip, onclose }: { tip: Tip; onclose: () => void } = $props();
</script>

<button class="bubble pressable" onclick={() => { onclose(); go(tip.to.startsWith('/') ? tip.to : `/knowhow/${tip.to}`); }}>
  <span class="txt">{tip[$lang]}</span>
  <span class="more">{$t('mascot.more')} →</span>
</button>

<style>
  .bubble { position: relative; display: flex; flex-direction: column; align-items: flex-start; gap: 6px; text-align: left;
            min-height: var(--touch); max-width: 330px; padding: 14px 18px 12px; background: var(--paper); color: var(--ink);
            border: var(--outline) solid var(--ink); border-radius: 22px; box-shadow: var(--shadow-sm); font: inherit;
            transform-origin: 40px 100%; animation: pop .42s cubic-bezier(.34, 1.56, .64, 1) both; }
  .bubble::after { content: ''; position: absolute; left: 34px; bottom: -17px; width: 26px; height: 26px; background: var(--paper);
                   border-right: var(--outline) solid var(--ink); border-bottom: var(--outline) solid var(--ink);
                   transform: rotate(45deg) skew(10deg, 10deg); }
  .txt { font-weight: 800; font-size: 16.5px; line-height: 1.3; }
  .more { font-weight: 900; font-size: 13px; opacity: .6; }
  @keyframes pop { 0% { opacity: 0; transform: scale(.5) translateY(14px); } 60% { opacity: 1; } 100% { opacity: 1; transform: scale(1); } }
</style>
