<script lang="ts">
  import Icon from './Icon.svelte';
  import { textOn } from '../lib/color';
  import { fit } from '../lib/fit';
  let { icon, color, title, subtitle = '', onclick, wiggle = false }:
    { icon: string; color: string; title: string; subtitle?: string; onclick?: () => void; wiggle?: boolean } = $props();
</script>

<button class="tile pressable" class:wiggle style:--c={color} style:color={textOn(color)} {onclick}>
  <span class="plate"><Icon name={icon} size={62} /></span>
  <span class="txt"><span class="title" use:fit={title}>{title}</span>{#if subtitle}<span class="sub">{subtitle}</span>{/if}</span>
</button>

<style>
  /* The tile's content never shrinks to fit its box — neither the plate nor the text. In a
     row shorter than the content Chrome squashed the plate's HEIGHT only (an oval), and Safari kept the plate and cut
     the subtitle off at the bottom (iPhone, every home tile). Now the box must grow instead (Home's rows
     are minmax(min-content, 1fr) and the phone layout scrolls), and phones get a smaller plate so it rarely has to.
     scripts/clip-audit.py fails the build when any text is cut off like that again. */
  .tile {
    --plate: 86px;
    background: var(--c); border: var(--outline) solid var(--ink); border-radius: var(--r-lg);
    box-shadow: var(--shadow); padding: 14px; min-height: var(--touch);
    display: flex; flex-direction: column; justify-content: space-between; align-items: flex-start; gap: 8px;
    text-align: left; overflow: hidden;
  }
  .plate {
    flex: none; width: var(--plate); height: var(--plate);
    border-radius: 50%; background: var(--cream); border: var(--outline) solid var(--ink);
    display: grid; place-items: center;
  }
  .plate :global(.icon) { width: 72%; height: 72%; }   /* 62 px in the 86 px plate, the same share in a smaller one */
  @media (max-aspect-ratio: 1/1), (max-height: 500px) { .tile { --plate: 60px; padding: 12px; } }
  .wiggle .plate { animation: wig 1s ease-in-out both; }
  @keyframes wig { 0%, 100% { transform: none; } 20% { transform: rotate(-9deg) scale(1.08); } 45% { transform: rotate(7deg) scale(1.08); } 70% { transform: rotate(-3deg); } }
  .txt { flex: none; display: flex; flex-direction: column; gap: 2px; min-width: 0; width: 100%; }
  .title { font-family: var(--font-display); font-size: 23px; line-height: 1.05; white-space: nowrap; overflow: hidden; display: block; }
  .sub { font-weight: 700; font-size: 13.5px; opacity: .9; }
</style>
