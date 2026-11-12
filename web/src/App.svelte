<script lang="ts">
  import { onMount } from 'svelte';
  import { derived } from 'svelte/store';
  import Home from './screens/Home.svelte';
  import Idle from './screens/Idle.svelte';
  import Settings from './screens/Settings.svelte';
  import Soon from './screens/Soon.svelte';
  import Pantry from './screens/Pantry.svelte';
  import PantryCategory from './screens/PantryCategory.svelte';
  import PantryHave from './screens/PantryHave.svelte';
  import Toast from './components/Toast.svelte';
  import Shopping from './screens/Shopping.svelte';
  import Recipes from './screens/Recipes.svelte';
  import RecipeView from './screens/Recipe.svelte';
  import RecipeEdit from './screens/RecipeEdit.svelte';
  import Browse from './screens/Browse.svelte';
  import Add from './screens/Add.svelte';
  import Timers from './screens/Timers.svelte';
  import Cook from './screens/Cook.svelte';
  import KnowHow from './screens/KnowHow.svelte';
  import MascotLab from './screens/MascotLab.svelte';
  import KnowHowSection from './screens/KnowHowSection.svelte';
  import Spices from './screens/Spices.svelte';
  import BlendView from './screens/Blend.svelte';
  import BlendEdit from './screens/BlendEdit.svelte';
  import Sauces from './screens/Sauces.svelte';
  import SauceView from './screens/Sauce.svelte';
  import SauceEdit from './screens/SauceEdit.svelte';
  import { loadBlends } from './lib/spices';
  import { loadSauces } from './lib/sauces';
  import TimerDone from './components/TimerDone.svelte';
  import { acceptTimers, flushDismissals, flushOfflineTimers, loadTimers, type ServerTimer } from './lib/cooktimers';
  import { loadRecipes } from './lib/recipes';
  import { startOfflineWarm } from './lib/offlinewarm';
  import { registerWorker } from './lib/swregister';
  import { loadShopping, shopping, type ShopItem } from './lib/shopping';
  import { checkForUpdate } from './lib/update';
  import { outbox } from './lib/queue';
  import { loadPantry, pantry, type PantryState } from './lib/pantry';
  import OfflineBadge from './components/OfflineBadge.svelte';
  import Keyboard from './components/Keyboard.svelte';
  import NightOverlay from './components/NightOverlay.svelte';
  import { route, go } from './lib/router';
  import { connectEvents } from './lib/events';
  import { report } from './lib/offline';
  import { apply, load, settings, type Settings as S } from './lib/settings';
  import { now } from './lib/clock';
  import { budapestHour, darkScene, isNight } from './lib/night';
  import { isKiosk } from './lib/kiosk';
  import { createIdle } from './lib/idle';
  import { createAmbient, cueMascot, wiggleTile } from './lib/ambient';
  import { online } from './lib/offline';

  // ?shot=1 = screenshot mode (scripts/screens.sh): no SSE, whose endless stream keeps headless Chrome waiting.
  const shotMode = new URLSearchParams(location.search).has('shot');
  // ?demo=acts,day (scripts/kiosk-measure.py --query): acts back to back — the worst case for the CPU budget — and/or
  // the day look at any hour. Never set in normal use.
  const demo = (new URLSearchParams(location.search).get('demo') ?? '').split(',');
  const night = derived([now, settings], ([$n, $s]) => !demo.includes('day') && isNight(budapestHour($n), $s.night_start, $s.night_end));
  let dark = $derived(darkScene($night, $route.name));
  $effect(() => { document.documentElement.classList.toggle('kiosk', $isKiosk); });
  // ?demo=nobreathe: the mascot's continuous breath off, to weigh its cost on the kiosk
  if (demo.includes('nobreathe')) document.documentElement.classList.add('demo-nobreathe');
  if (demo.includes('layers')) document.documentElement.classList.add('demo-layers');

  onMount(() => {
    load();
    loadPantry();
    loadShopping();
    loadRecipes();
    loadTimers();
    loadBlends();
    loadSauces();
    const ambient = createAmbient(demo.includes('acts') ? { minGapMs: 300, maxGapMs: 700 } : {});
    const unNight = night.subscribe((v) => ambient.setNight(v));
    // the visible mascot (home/idle) reacts to the connection: worried when it drops, a hop when it is back
    let wasOnline: boolean | null = null;
    const unOnline = online.subscribe((v) => { if (wasOnline !== null && v !== wasOnline) cueMascot(v ? 'hop' : 'worried'); wasOnline = v; });
    const onVis = () => ambient.wake();
    document.addEventListener('visibilitychange', onVis);
    ambient.start();

    let idle: ReturnType<typeof createIdle> | null = null;
    let before = '#/';
    if ($isKiosk && !shotMode) {
      idle = createIdle({
        timeoutMs: $settings.idle_minutes * 60000,
        onIdle: () => { before = location.hash || '#/'; if ($route.name !== 'idle') go('/idle', { replace: true }); },
        onWake: () => go(before === '#/idle' || !before ? '/' : before, { replace: true }),
        onIdleScreen: () => $route.name === 'idle',
        holdIf: () => $route.name === 'cook' || $route.name === 'cook-sauce',
      });
    }
    const unIdle = settings.subscribe((s) => idle?.setTimeoutMs(s.idle_minutes * 60000));

    // the kiosk keeps every recipe, sauce, blend and photo for offline use (lib/offlinewarm.ts)
    const warm = $isKiosk && !shotMode ? startOfflineWarm() : null;
    let ev: ReturnType<typeof connectEvents> | null = null;
    if (!shotMode) {
      // back online: first replay what was done offline, then reload, so the reload already includes it
      ev = connectEvents({ onStatus: (ok) => { report(ok); if (ok) { checkForUpdate(); registerWorker(__BUILD__); outbox.drain().finally(() => { load(); loadPantry(); loadShopping(); flushDismissals().then(() => flushOfflineTimers()).finally(() => loadTimers()); }); warm?.poke(); } } });
      ev.on('settings', (s: S) => apply(s));
      ev.on('pantry', (e: { state: PantryState }) => pantry.accept(e.state));
      ev.on('shopping', (e: { items: ShopItem[] }) => shopping.items.set(e.items));
      ev.on('recipes', () => { loadRecipes(); warm?.poke(); });
      // a blend change also changes every sauce that uses it (its verdict, its gluten line)
      ev.on('blends', () => { loadBlends(); loadSauces(); warm?.poke(); });
      ev.on('sauces', () => { loadSauces(); warm?.poke(); });
      ev.on('timers', (e: { timers: ServerTimer[] }) => acceptTimers(e.timers));
    }
    return () => { ev?.close(); warm?.stop(); ambient.stop(); idle?.destroy(); unNight(); unOnline(); unIdle(); document.removeEventListener('visibilitychange', onVis); };
  });
</script>

{#key $route.name}<div class="screen-in">
{#if $route.name === 'soon'}
  <Soon section={$route.param} />
{:else if $route.name === 'pantry'}
  <Pantry />
{:else if $route.name === 'pantry-cat'}
  <PantryCategory cat={$route.param} sub={$route.sub} />
{:else if $route.name === 'pantry-have'}
  <PantryHave />
{:else if $route.name === 'shopping'}
  <Shopping />
{:else if $route.name === 'recipes'}
  <Recipes folder={$route.folder} />
{:else if $route.name === 'recipe'}
  <RecipeView id={$route.id} />
{:else if $route.name === 'recipe-edit'}
  {#key $route.id}<RecipeEdit id={$route.id} folder={$route.folder ?? null} />{/key}
{:else if $route.name === 'cook'}
  {#key $route.id}<Cook id={$route.id} servings={$route.servings} />{/key}
{:else if $route.name === 'spices'}
  <Spices />
{:else if $route.name === 'blend'}
  {#key $route.id}<BlendView id={$route.id} />{/key}
{:else if $route.name === 'blend-edit'}
  {#key $route.id}<BlendEdit id={$route.id} />{/key}
{:else if $route.name === 'sauces'}
  <Sauces />
{:else if $route.name === 'sauce'}
  {#key $route.id}<SauceView id={$route.id} />{/key}
{:else if $route.name === 'sauce-edit'}
  {#key $route.id}<SauceEdit id={$route.id} />{/key}
{:else if $route.name === 'cook-sauce'}
  {#key $route.id}<Cook id={$route.id} kind="sauce" />{/key}
{:else if $route.name === 'knowhow'}
  <KnowHow />
{:else if $route.name === 'knowhow-section'}
  <KnowHowSection sid={$route.sid} pid={$route.pid} />
{:else if $route.name === 'timers'}
  <Timers />
{:else if $route.name === 'browse'}
  <Browse />
{:else if $route.name === 'add'}
  {#key $route.url}<Add url={$route.url} />{/key}
{:else if $route.name === 'mascot-lab'}
  <MascotLab query={$route.query} />
{:else if $route.name === 'settings'}
  <Settings />
{:else if $route.name === 'idle'}
  <Idle night={$night} />
{:else}
  <Home wiggleTile={$wiggleTile} />
{/if}
</div>{/key}
<TimerDone />
<Toast />
<NightOverlay on={dark && $isKiosk} />
<Keyboard />
<OfflineBadge />
