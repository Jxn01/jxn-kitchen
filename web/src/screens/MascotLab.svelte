<script lang="ts">
  // The mascot's moves, one button each (Settings → About → "The mascot"). Also the stage for scripts/anim-sheet.py,
  // which drives window.__mascot and samples each action into a filmstrip. Query: ?size= &night=1 &still=1 (no
  // blinks/glances/breathing — for frame-exact sampling) &expr= &prop=cap|chef &tap=1 &loop=<action> &pulse=<action>
  import { onDestroy, onMount } from 'svelte';
  import PageHeader from '../components/PageHeader.svelte';
  import Mascot from '../components/Mascot.svelte';
  import { ACTIONS, type Expr } from '../lib/mascot';
  import { P } from '../lib/palette';
  import { t } from '../lib/i18n';
  import { go } from '../lib/router';

  let { query = '' }: { query?: string } = $props();
  // the lab is opened once per query (the route mounts it afresh): its knobs start from the query and are then its own
  // svelte-ignore state_referenced_locally
  const q = new URLSearchParams(query);
  let size = $state(Number(q.get('size')) || 520);
  let night = $state(q.get('night') === '1');
  let still = q.get('still') === '1';
  const tap = q.get('tap') === '1';            // tappable, as on home (to measure its cost)
  // measuring knobs: loop=<action> repeats an action forever; pulse=<action> plays it once every 3 s (the timer card)
  const pulseId = q.get('pulse');
  let expr = $state<Expr>((q.get('expr') as Expr) || 'neutral');
  let prop = $state<'cap' | 'chef' | null>((q.get('prop') as 'cap' | 'chef') || null);
  let loop = $state<string | null>(q.get('loop'));
  let m: Mascot | undefined = $state();
  const EXPRS: Expr[] = ['neutral', 'happy', 'joy', 'surprised', 'sleepy', 'asleep', 'worried', 'focus', 'proud', 'alarm'];

  onMount(() => {
    const beat = pulseId ? setInterval(() => m?.play(pulseId), 3000) : null;
    (window as unknown as Record<string, unknown>).__mascot = {
      play: (id: string, keep = false) => m?.play(id, keep), stop: () => m?.stop(), setExpr: (e: Expr) => (expr = e), setNight: (v: boolean) => (night = v),
      setLoop: (id: string | null) => (loop = id), setProp: (p: 'cap' | 'chef' | null) => (prop = p),
      actions: Object.fromEntries(Object.entries(ACTIONS).map(([k, v]) => [k, v.ms])),
    };
    return () => { if (beat) clearInterval(beat); };
  });
  onDestroy(() => { delete (window as unknown as Record<string, unknown>).__mascot; });
</script>

<div class="screen" class:night>
  <PageHeader title={$t('lab.title')} sub={$t('lab.sub')} icon="cook" color={P.butter} back={() => go('/settings')} />
  <div class="body">
    <div class="stage" id="stage"><Mascot bind:this={m} {size} {night} {expr} {prop} {loop} alive={!still} breathe={!still} tappable={tap} /></div>
    <div class="panel">
      <div class="row">{#each Object.keys(ACTIONS) as id}<button class="b pressable" onclick={() => m?.play(id)}>{id}</button>{/each}</div>
      <div class="row">{#each EXPRS as e}<button class="b pressable" class:on={expr === e} onclick={() => (expr = e)}>{e}</button>{/each}</div>
      <div class="row">
        <button class="b pressable" class:on={night} onclick={() => (night = !night)}>{$t('lab.night')}</button>
        <button class="b pressable" class:on={prop === 'cap'} onclick={() => (prop = prop === 'cap' ? null : 'cap')}>{$t('lab.cap')}</button>
        <button class="b pressable" class:on={prop === 'chef'} onclick={() => (prop = prop === 'chef' ? null : 'chef')}>{$t('lab.chef')}</button>
        <button class="b pressable" class:on={loop === 'alarm'} onclick={() => (loop = loop === 'alarm' ? null : 'alarm')}>{$t('lab.alarm')}</button>
        <button class="b pressable" class:on={loop === 'think'} onclick={() => (loop = loop === 'think' ? null : 'think')}>{$t('lab.think')}</button>
      </div>
    </div>
  </div>
</div>

<style>
  .screen { height: 100%; display: flex; flex-direction: column; }
  .screen.night { background: #2A2420; }
  /* one row of minmax(0, 1fr): an auto row grew to the panel's full height, so the panel never scrolled and .body cut its
     buttons off on a short screen (a phone on its side; scripts/clip-audit.py) */
  .body { flex: 1; min-height: 0; display: grid; grid-template-columns: auto 1fr; grid-template-rows: minmax(0, 1fr); gap: 16px;
          padding: 12px 18px; overflow: hidden; }
  .stage { display: grid; place-items: center; padding: 40px 20px 0; }
  .panel { display: flex; flex-direction: column; gap: 10px; overflow-y: auto; }
  .row { display: flex; flex-wrap: wrap; gap: 8px; }
  .b { min-height: var(--touch); min-width: var(--touch); padding: 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink);
       background: var(--paper); font-weight: 800; font-size: 15px; }
  .b.on { background: var(--butter); }
  /* minmax(0, 1fr), not 1fr: a 1fr column never shrinks below its widest item (the mascot's stage), so on a phone it
     grew past the screen, the button rows wrapped at that width and .body cut "snore" & co off on the right
     (scripts/clip-audit.py). The stage keeps its drawing centred and clips what does not fit. */
  @media (max-aspect-ratio: 1/1) {
    .body { grid-template-columns: minmax(0, 1fr); grid-template-rows: none; overflow-y: auto; }
    .stage { overflow: hidden; }
  }
</style>
