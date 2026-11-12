<script lang="ts">
  // A know-how page's infographic drawn from data (knowhow/*.yaml `chart:`, validated by server/kitchen/charts.py):
  // one component per type, each a drawn object the data fills. Still until touched; the chips are the targets.
  import type { KChart } from '../../lib/knowhow';
  import Vessel from './Vessel.svelte';
  import Board from './Board.svelte';
  import Scale from './Scale.svelte';
  import Swatches from './Swatches.svelte';
  import Bars from './Bars.svelte';
  import Steps from './Steps.svelte';
  import Layers from './Layers.svelte';
  import Matrix from './Matrix.svelte';
  import Picker from './Picker.svelte';
  let { chart, lang }: { chart: KChart; lang: 'en' | 'hu' } = $props();
</script>

{#if chart.type === 'vessel'}<Vessel {chart} {lang} />
{:else if chart.type === 'board'}<Board {chart} {lang} />
{:else if chart.type === 'scale'}<Scale {chart} {lang} />
{:else if chart.type === 'swatches'}<Swatches {chart} {lang} />
{:else if chart.type === 'bars'}<Bars {chart} {lang} />
{:else if chart.type === 'steps'}<Steps {chart} {lang} />
{:else if chart.type === 'layers'}<Layers {chart} {lang} />
{:else if chart.type === 'matrix'}<Matrix {chart} {lang} />
{:else if chart.type === 'picker'}<Picker {chart} {lang} />{/if}
