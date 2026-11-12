<script lang="ts">
  // One icon from the sprite (web/public/sprite.svg, built by icons/build_sprite.py).
  let { name, size = 48 }: { name: string; size?: number } = $props();
</script>

<svg class="icon" width={size} height={size} aria-hidden="true" focusable="false">
  <use href={`/sprite.svg#i-${name}`} />
</svg>

<style>
  .icon { display: block; flex: none; }
</style>
