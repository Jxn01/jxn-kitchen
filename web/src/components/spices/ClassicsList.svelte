<script lang="ts">
  // The nearest classics: how alike (a bar), and what differs — the jars you are missing and the ones you added.
  // Rows and chips are fixed pools (lib/spices pool): every answer only fills them — rows keyed by the classic were all
  // rebuilt each time (a 76 ms frame on the kiosk). At most six chips a side, then "+N" for the rest.
  import { pool, SLOTS, type Classic, type Jar } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  import { t } from '../../lib/i18n';
  let { classics, jars, lang }: { classics: Classic[]; jars: Map<string, Jar>; lang: Lang } = $props();
  const nm = (id: string) => jars.get(id)?.label[lang] ?? id;
</script>

<ul class="cl">
  {#each pool(classics, SLOTS.classics) as c, i (i)}
    {@const miss = c?.missing ?? []}
    {@const extra = c?.extra ?? []}
    <li class:gone={!c}>
      <div class="top"><b>{c ? c[lang] : ''}</b><span class="pct">{c ? `${c.similarity} %` : ''}</span></div>
      <div class="bar"><span style:transform="scaleX({c ? c.similarity / 100 : 0})"></span></div>
      <div class="chips">
        {#each pool(miss.slice(0, SLOTS.chips), SLOTS.chips) as m, k (k)}<span class="ch miss" class:gone={!m}>− {m ? nm(m) : ''}</span>{/each}
        <span class="ch miss" class:gone={miss.length <= SLOTS.chips}>− {miss.length - SLOTS.chips} {$t('spices.classics.more')}</span>
        {#each pool(extra.slice(0, SLOTS.chips), SLOTS.chips) as x, k (k)}<span class="ch extra" class:gone={!x}>+ {x ? nm(x) : ''}</span>{/each}
        <span class="ch extra" class:gone={extra.length <= SLOTS.chips}>+ {extra.length - SLOTS.chips} {$t('spices.classics.more')}</span>
        <small class:gone={!c || miss.length || extra.length}>{$t('spices.classics.same')}</small>
      </div>
    </li>
  {/each}
</ul>

<style>
  .cl { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
  li { background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r-sm); padding: 8px 12px; }
  .top { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
  b { font-family: var(--font-display); font-weight: 400; font-size: 17px; }
  .pct { font-weight: 900; font-size: 16px; }
  .bar { height: 12px; border: 2px solid var(--ink); border-radius: 999px; margin: 6px 0; overflow: hidden; background: var(--cream); }
  .bar span { display: block; height: 100%; background: var(--tangerine); transform-origin: 0 50%; }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; }
  .ch { border: 2px solid var(--ink); border-radius: 999px; padding: 0 8px; font-weight: 800; font-size: 12.5px; }
  .miss { background: #FFD9CE; } .extra { background: #D6EEFB; }
  small { font-weight: 700; opacity: .7; }
  .gone { display: none !important; }
</style>
