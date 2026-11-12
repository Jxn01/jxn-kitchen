<script lang="ts">
  // A small jar in plain HTML/CSS — a lid and a glass in the spice's colour — for the places a tap adds one (the tray,
  // the timing lanes, the Try cards): far cheaper to create on the Atom than the clipped svg of SpiceJar.
  let { fill = '#CCBFA8', size = 30 }: { fill?: string; size?: number } = $props();
</script>

<span class="mj" style:--f={fill} style:width="{size * 0.8}px" style:height="{size}px" aria-hidden="true"><i></i></span>

<style>
  .mj { position: relative; display: inline-block; flex: none; }
  .mj::before { content: ''; position: absolute; left: 0; right: 0; bottom: 0; top: 24%; border: 2px solid var(--ink); border-radius: 3px 3px 5px 5px;
                background: linear-gradient(90deg, rgba(255, 255, 255, .45) 0 18%, transparent 18%), var(--f); }
  i { position: absolute; left: 12%; right: 12%; top: 0; height: 26%; background: #C48A55; border: 2px solid var(--ink); border-radius: 3px; }
</style>
