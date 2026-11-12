<script lang="ts">
  import { failKey } from '../lib/api';
  import { onMount } from 'svelte';
  import Mascot from '../components/Mascot.svelte';
  // Cook mode (spec §6.5; for sauces 2026-10-19 §6.3): one step at a time, huge text; ‹ › or a swipe to move;
  // durations in a step are buttons that start a labelled timer; the ingredients (GF version, scaled) in a drawer with
  // a checklist and their GF chips; after the last step, "Used up anything?" — a sauce ends on how long it keeps
  // instead (the pantry is not an input to the engines). It cooks a *cookable* (lib/cook): a recipe or a sauce, read
  // into one shape. The screen never goes idle here (App.svelte holds the idle timer on these routes).
  import Icon from '../components/Icon.svelte';
  import RoundButton from '../components/RoundButton.svelte';
  import TimerChips from '../components/TimerChips.svelte';
  import GlutenChip from '../components/GlutenChip.svelte';
  import { api } from '../lib/recipes';
  import { api as sauceApi, loadShelves, nameIndex, shelves } from '../lib/sauces';
  import { blendList, loadBlends, loadRack, rack } from '../lib/spices';
  import { fromRecipe, fromSauce, stepParts, timerLabel, type Cookable } from '../lib/cook';
  import { timerApi, fmtTime } from '../lib/cooktimers';
  import { catalogue } from '../lib/pantry';
  import { toggleWithToast } from '../lib/pantry-actions';
  import { nameOf } from '../lib/search';
  import { fit } from '../lib/fit';
  import { lang, t } from '../lib/i18n';
  import { go } from '../lib/router';
  import { showToast } from '../lib/toast';
  import { sound } from '../lib/sound';

  let { id, servings = null, kind = 'recipe' }: { id: number; servings?: number | null; kind?: 'recipe' | 'sauce' } = $props();
  let r = $state<Cookable | null>(null);
  let pos = $state(0);
  let drawer = $state(false);
  let ticked = $state<Set<number>>(new Set());
  let finished = $state(false);
  let usedTaken = $state<Set<string>>(new Set());
  // a sauce reads its lines' names from the shelves, the rack and the owner's blends: loaded once here (an effect that
  // loaded the blends whenever the list was empty would reload forever for an owner with none)
  onMount(() => { if (kind === 'sauce') { if (!$shelves) loadShelves(); if (!$rack) loadRack(); loadBlends(); } });
  $effect(() => {
    if (kind === 'recipe') { api.get(id, servings ?? undefined).then((x) => { r = fromRecipe(x); }).catch(() => { r = null; }); return; }
    if (!$shelves || !$rack) return;
    const names = nameIndex($shelves, $rack.shelves.flatMap((s) => s.jars), $lang);
    const blends = Object.fromEntries($blendList.map((b) => [b.id, b.names[$lang]]));
    const sh = $shelves;
    sauceApi.get(id).then((x) => { r = fromSauce(x, $lang, sh.units, names, blends); }).catch(() => { r = null; });
  });

  let steps = $derived(r?.steps ?? []);
  let last = $derived(Math.max(0, steps.length - 1));
  let parts = $derived(steps[pos] ? stepParts(steps[pos].text, steps[pos].timers) : []);
  let used = $derived(r?.used ?? []);

  function next() { if (pos < last) pos += 1; else finished = true; }
  function prev() { if (finished) finished = false; else if (pos > 0) pos -= 1; }
  async function startTimer(seconds: number) {
    try { await timerApi.start(timerLabel(r!.title, pos, $lang), seconds, r!.recipeId ?? undefined, r!.recipeId ? pos : undefined); sound.on(); showToast({ text: $t('cook.timer.started', { time: fmtTime(seconds) }) }); }
    catch (e) { showToast({ text: $t(failKey(e)), tone: 'warn' }); }
  }
  // swipe: a horizontal drag of more than 80 px
  let x0: number | null = null;
  const down = (e: PointerEvent) => { x0 = e.clientX; };
  const up = (e: PointerEvent) => { if (x0 !== null && Math.abs(e.clientX - x0) > 80) (e.clientX < x0 ? next() : prev()); x0 = null; };
  function tickLine(p: number) { const s = new Set(ticked); s.has(p) ? s.delete(p) : s.add(p); ticked = s; }
  const itemName = (pid: string) => {
    for (const c of $catalogue?.categories ?? []) for (const g of c.groups) for (const it of g.items) if (it.id === pid) return nameOf(it, $lang);
    return pid;
  };
  async function takeOut(pid: string) {
    await toggleWithToast(pid, itemName(pid));
    usedTaken = new Set([...usedTaken, pid]);
  }
</script>

{#if r}
  <div class="cook">
    <header>
      <RoundButton icon="back" label={$t('common.back')} onclick={() => go(r!.back)} />
      <h1 use:fit={r.title}>{r.title}</h1>
      <span class="count">{finished ? '✓' : `${pos + 1} / ${steps.length}`}</span>
      <button class="ing pressable" class:on={drawer} onclick={() => (drawer = !drawer)} aria-label={$t('recipe.ingredients')}><Icon name="recipes" size={30} /><span class="lbl">{$t('recipe.ingredients')}</span></button>
    </header>
    <div class="timers"><TimerChips /></div>

    {#if !finished}
      <main class="step" onpointerdown={down} onpointerup={up}>
        {#if steps.length}
          <p class="text">
            {#each parts as p}{#if p.seconds}<button class="dur pressable" onclick={() => startTimer(p.seconds!)}><Icon name="cook" size={30} />{p.text}</button>{:else}{p.text}{/if}{/each}
          </p>
        {:else}
          <p class="text">{$t('cook.nosteps')}</p>
        {/if}
      </main>
    {:else}
      <main class="done">
        <div class="donehead">
          <Mascot size={180} act="celebrate" prop="chef" />
          {#if r.recipeId !== null}
            <div><h2>{$t('cook.usedup')}</h2><p class="hint">{$t('cook.usedup.hint')}</p></div>
          {:else}
            <div><h2>{$t('cook.sauce.done')}</h2>{#if r.keeps}<p class="hint">{$t('cook.sauce.keeps', { n: r.keeps })}</p>{/if}</div>
          {/if}
        </div>
        <div class="chips" class:gone={r.recipeId === null}>
          {#each used as pid (pid)}
            <button class="chip pressable" class:taken={usedTaken.has(pid)} disabled={usedTaken.has(pid)} onclick={() => takeOut(pid)}>{itemName(pid)}</button>
          {:else}
            <p class="hint">{$t('cook.usedup.none')}</p>
          {/each}
        </div>
        <button class="finish pressable" onclick={() => go(r!.back)}>{$t('cook.finish')}</button>
      </main>
    {/if}

    <nav>
      <button class="nav prev pressable" onclick={prev} disabled={pos === 0 && !finished}>‹ {$t('cook.prev')}</button>
      <div class="dots">{#each steps as _, i}<span class:on={i === pos && !finished} class:past={i < pos || finished}></span>{/each}</div>
      {#if !finished}<button class="nav next pressable" onclick={next}>{pos === last ? $t('cook.last') : $t('cook.next')} ›</button>{/if}
    </nav>

    {#if drawer}
      <div class="scrim" role="presentation" onclick={() => (drawer = false)}></div>
      <aside class="drawer">
        <h2>{$t('recipe.ingredients')}{#if r.servings} · {$t('recipes.servings', { n: r.servings })}{:else if r.yield_ml} · {$t('sauce.yield', { ml: r.yield_ml })}{/if}</h2>
        <ul>
          {#each r.lines as l (l.key)}
            <li><button class="line" class:ticked={ticked.has(l.key)} onclick={() => tickLine(l.key)}><span class="box">{ticked.has(l.key) ? '✓' : ''}</span>
              <span class="lt">{l.text}{#if l.note}<i> ({l.note})</i>{/if}</span>{#if l.gluten}<GlutenChip status={l.gluten} />{/if}</button></li>
          {/each}
        </ul>
      </aside>
    {/if}
  </div>
{/if}

<style>
  .donehead { display: flex; align-items: center; gap: 10px; margin: -24px 0 4px -16px; }
  .cook { height: 100%; display: flex; flex-direction: column; background: var(--cream); }
  header { flex: none; display: flex; align-items: center; gap: 14px; padding: 12px 20px; background: var(--herb); color: var(--ink); border-bottom: var(--outline-thick) solid var(--ink); }
  h1 { flex: 1; min-width: 0; font-size: 28px; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .count { font-family: var(--font-display); font-size: 26px; }
  .ing { min-height: var(--touch); display: flex; align-items: center; gap: 8px; padding: 0 16px 0 8px; border-radius: 999px; border: var(--outline) solid var(--ink);
         background: var(--paper); color: var(--ink); font-weight: 800; font-size: 16px; }
  .ing.on { background: var(--butter); }
  .timers { flex: none; padding: 10px 20px 0; }
  .step, .done { flex: 1; min-height: 0; overflow-y: auto; padding: 18px 40px; touch-action: pan-y; }
  .text { margin: 0; font-size: 34px; line-height: 1.4; font-weight: 700; }
  .dur { display: inline-flex; align-items: center; gap: 6px; vertical-align: middle; min-height: var(--touch); padding: 0 16px 0 8px; margin: 0 4px;
         border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--butter); font: inherit; font-weight: 900; font-size: 30px; box-shadow: var(--shadow-sm); }
  nav { flex: none; display: flex; align-items: center; gap: 14px; padding: 12px 20px 16px; }
  .nav { min-height: 76px; min-width: 200px; border-radius: var(--r); border: var(--outline-thick) solid var(--ink); font-family: var(--font-display); font-size: 26px; box-shadow: var(--shadow); }
  .prev { background: var(--paper); } .prev:disabled { opacity: .35; box-shadow: none; }
  .next { background: var(--herb); color: var(--ink); margin-left: auto; }
  .dots { flex: 1; display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }
  .dots span { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--ink); background: var(--paper); }
  .dots .past { background: var(--leaf); } .dots .on { background: var(--herb); transform: scale(1.3); }
  .done h2 { font-size: 34px; margin-bottom: 4px; }
  .hint { font-weight: 700; opacity: .7; margin: 0 0 14px; }
  .chips { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
  .chip { min-height: var(--touch); padding: 0 20px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 18px; }
  .chip.taken { opacity: .45; text-decoration: line-through; }
  .finish { min-height: 76px; padding: 0 34px; border-radius: var(--r); border: var(--outline-thick) solid var(--ink); background: var(--herb); color: var(--ink);
            font-family: var(--font-display); font-size: 26px; box-shadow: var(--shadow); }
  .scrim { position: fixed; inset: 0; background: rgba(0, 0, 0, .3); z-index: 20; }
  .drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(440px, 92vw); z-index: 21; background: var(--paper); border-left: var(--outline-thick) solid var(--ink);
            padding: calc(16px + env(safe-area-inset-top)) calc(16px + env(safe-area-inset-right)) calc(16px + env(safe-area-inset-bottom)) 16px;
            overflow-y: auto; animation: slide 200ms ease-out both; }
  @keyframes slide { from { transform: translateX(100%); } to { transform: none; } }
  .drawer h2 { font-size: 22px; margin-bottom: 8px; }
  ul { list-style: none; margin: 0; padding: 0; }
  .line { width: 100%; min-height: var(--touch); display: flex; align-items: center; gap: 12px; border: 0; border-bottom: 2px dashed #E7DCCB; background: none;
          text-align: left; font: inherit; font-weight: 700; font-size: 17px; color: inherit; padding: 0; }
  .line.ticked { opacity: .45; text-decoration: line-through; }
  .box { flex: none; width: 34px; height: 34px; border-radius: 8px; border: var(--outline) solid var(--ink); display: grid; place-items: center; font-weight: 900; background: var(--cream); }
  .line i { font-style: normal; opacity: .6; font-size: 14px; }
  .lt { flex: 1; min-width: 0; }
  .gone { display: none; }
  @media (max-aspect-ratio: 1/1) {
    .text { font-size: 26px; } .step, .done { padding: 14px 16px; } .nav { min-width: 0; flex: 1; font-size: 20px; min-height: 60px; } .dots { display: none; }
    /* phones: the title gets the room — the ingredients button shows its icon only, the counter shrinks */
    header { gap: 8px; padding: 8px 10px; } h1 { font-size: 20px; } .count { font-size: 20px; }
    .ing { padding: 0; min-width: var(--touch); justify-content: center; } .ing .lbl { display: none; }
  }
</style>
