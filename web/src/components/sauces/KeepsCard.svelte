<script lang="ts">
  // How long it keeps: a drawn fridge with the days on a note stuck to its door, the engine's sentence (why: the most
  // perishable thing in it), and under them the ladder of every keeping class — raw egg's 2 days up to 30 — with this
  // sauce's lit. All of it built once and changed by text and class.
  import type { SauceEvaluation } from '../../lib/sauces';
  import type { Labelled } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  import { t } from '../../lib/i18n';
  let { keeps, classes, lang, blank = false }:
    { keeps: SauceEvaluation['keeps']; classes: (Labelled & { days: number })[]; lang: Lang; blank?: boolean } = $props();
</script>

<div class="keeps" class:blank>
  <div class="top">
    <span class="fridge">
      <svg viewBox="0 0 80 110" width="80" height="110" aria-hidden="true">
        <rect class="box" x="6" y="4" width="68" height="102" rx="9" />
        <path class="seam" d="M6,40 H74" />
        <path class="grip" d="M62,16 V30 M62,52 V78" />
        <path class="feet" d="M16,106 v4 M64,106 v4" />
      </svg>
      <span class="note"><b>{blank ? '–' : keeps.days}</b><small>{$t('sauce.keeps.unit', { n: keeps.days })}</small></span>
    </span>
    <p class="says">{keeps[lang] || '·'}</p>
  </div>
  <ol class="ladder">
    {#each classes as c (c.id)}
      <li class:on={!blank && c.id === keeps.class}><b>{c.days}</b><span>{c[lang]}</span></li>
    {/each}
  </ol>
</div>

<style>
  .keeps { display: flex; flex-direction: column; gap: 10px; }
  .top { display: flex; align-items: center; gap: 14px; }
  .fridge { position: relative; flex: none; display: block; contain: layout paint; }
  svg { display: block; }
  .box { fill: #EEF3F6; stroke: var(--ink); stroke-width: 3.4; }
  .seam { stroke: var(--ink); stroke-width: 3; }
  .grip { stroke: var(--ink); stroke-width: 4; stroke-linecap: round; }
  .feet { stroke: var(--ink); stroke-width: 4; stroke-linecap: round; }
  .note { position: absolute; left: 12px; top: 48px; width: 44px; padding: 2px 0 3px; background: var(--butter); border: 2px solid var(--ink);
          border-radius: 3px; transform: rotate(-5deg); display: flex; flex-direction: column; align-items: center; box-shadow: 1px 2px 0 rgba(0, 0, 0, .18); }
  .note b { font-family: var(--font-display); font-weight: 400; font-size: 24px; line-height: 1; }
  .note small { font-weight: 900; font-size: 10px; line-height: 1; }
  .says { flex: 1; margin: 0; font-weight: 800; font-size: 16px; line-height: 1.35; }
  .blank .says, .blank .note { opacity: .4; }
  .ladder { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
  .ladder li { contain: content; display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 4px 2px; min-height: 64px;
               border: 2px solid #CDBFA8; border-radius: var(--r-sm); background: var(--paper); text-align: center; }
  .ladder li.on { border: var(--outline) solid var(--ink); background: var(--butter); }
  .ladder b { font-family: var(--font-display); font-weight: 400; font-size: 18px; line-height: 1; }
  .ladder span { font-weight: 800; font-size: 10.5px; line-height: 1.1; }
</style>
