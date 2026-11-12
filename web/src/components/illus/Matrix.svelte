<script lang="ts">
  // chart type `matrix`: what goes where — rows (dishes) × columns (appliances), each cell no / works / best. The
  // column heads are the touch targets: a highlight slides to the chosen column (one div, translateX by its own width),
  // its cells puff up, and the card says what that column is for. The cells pop in once, row by row.
  import { tx, type KMatrix } from '../../lib/knowhow';
  import Icon from '../Icon.svelte';
  import Card from './Card.svelte';

  let { chart, lang }: { chart: KMatrix; lang: 'en' | 'hu' } = $props();
  let sel = $state(0);
  const n = $derived(chart.cols.length);
  let col = $derived(chart.cols[sel]);
</script>

<div class="wrap">
  <div class="grid" style:--n={n}>
    <div class="corner">
      {#each [2, 1, 0] as l}<span class="key"><span class="dot l{l}"></span>{tx(chart.levels[l], lang)}</span>{/each}
    </div>
    <div class="cols">
      <div class="hl" style:width="{100 / n}%" style:transform="translateX({sel * 100}%)"></div>
      {#each chart.cols as c, i}
        <button class="head pressable" class:on={i === sel} onclick={() => (sel = i)}>
          {#if c.icon}<Icon name={c.icon} size={40} />{/if}<span>{tx(c.label, lang)}</span>
        </button>
      {/each}
      {#each chart.rows as r, ri}
        {#each r.cells as v, ci}
          <span class="cell" class:hot={ci === sel}><span class="dot l{v}" style:animation-delay="{ri * 40 + ci * 25}ms"></span></span>
        {/each}
      {/each}
    </div>
    <div class="labels">
      {#each chart.rows as r}<span class="rl">{#if r.icon}<Icon name={r.icon} size={22} />{/if}{tx(r.label, lang)}</span>{/each}
    </div>
  </div>
  <Card title={tx(col.label, lang)} text={tx(col.note, lang)} />
</div>

<style>
  .wrap { display: flex; flex-direction: column; gap: 12px; }
  .grid { display: grid; grid-template-columns: minmax(150px, 34%) 1fr; grid-template-rows: 78px 1fr; }   /* the head row is 78 px on BOTH sides, so labels and cells line up */
  .corner { grid-column: 1; grid-row: 1; height: 78px; display: flex; flex-direction: column; justify-content: flex-end; gap: 3px; padding: 0 8px 8px 0; font-weight: 700; font-size: 12.5px; }
  .key { display: flex; align-items: center; gap: 6px; }
  .cols { grid-column: 2; grid-row: 1 / span 2; position: relative; display: grid; grid-template-columns: repeat(var(--n), 1fr); grid-auto-rows: 32px;
          grid-template-rows: 78px; align-items: center; }
  .hl { position: absolute; left: 0; top: 0; bottom: 0; background: var(--butter); border: var(--outline) solid var(--ink); border-radius: 14px; z-index: 0;
        transition: transform .4s cubic-bezier(.34, 1.3, .64, 1); pointer-events: none; }
  .head { position: relative; z-index: 1; min-height: var(--touch); display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 6px 2px 4px;
          border: 0; background: none; color: var(--ink); font: inherit; font-weight: 800; font-size: 12px; line-height: 1.1; text-align: center; }
  .head span { min-height: 2.2em; display: flex; align-items: center; }
  .labels { grid-column: 1; grid-row: 2; display: grid; grid-auto-rows: 32px; align-items: center; }
  .rl { display: flex; align-items: center; gap: 6px; font-weight: 800; font-size: 13.5px; line-height: 1.1; border-bottom: 1px dashed rgba(31, 26, 23, .18); height: 100%; }
  .cell { position: relative; z-index: 1; display: grid; place-items: center; height: 100%; border-bottom: 1px dashed rgba(31, 26, 23, .18); }
  .dot { display: inline-block; border-radius: 50%; animation: dot-in .35s cubic-bezier(.34, 1.56, .64, 1) both; transition: transform .25s cubic-bezier(.34, 1.56, .64, 1); }
  @keyframes dot-in { from { opacity: 0; transform: scale(.3); } to { opacity: 1; transform: none; } }
  .dot.l2 { width: 20px; height: 20px; background: var(--herb); border: 2.5px solid var(--ink); }
  .dot.l1 { width: 14px; height: 14px; background: var(--paper); border: 2.5px solid var(--ink); box-shadow: inset 0 -5px 0 var(--mustard); }
  .dot.l0 { width: 12px; height: 3px; border-radius: 2px; background: rgba(31, 26, 23, .3); }
  .key .dot { animation: none; }
  .cell.hot .dot.l2, .cell.hot .dot.l1 { transform: scale(1.25); }
  /* phone: narrow labels, small heads (a 390 px screen still shows all five columns) */
  @media (max-aspect-ratio: 1/1) {
    .grid { grid-template-columns: 96px minmax(0, 1fr); }
    .head { padding: 4px 0; min-width: 0; }
    .head span { display: none; }   /* icons only — the card names the chosen column */
    .head :global(svg) { width: 28px; height: 28px; }
    .rl { font-size: 11px; gap: 3px; }
    .rl :global(svg) { display: none; }
    .corner { font-size: 10.5px; }
    .dot.l2 { width: 15px; height: 15px; } .dot.l1 { width: 11px; height: 11px; }
  }
</style>
