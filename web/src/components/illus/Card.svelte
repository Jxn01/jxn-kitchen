<script lang="ts">
  // What the chosen chip means: a title, an optional big value, a sentence. Pops in when the choice changes.
  let { title, value = '', text }: { title: string; value?: string; text: string } = $props();
</script>

{#key title + text}
  <div class="card">
    <div class="head"><b>{title}</b>{#if value}<span>{value}</span>{/if}</div>
    <p>{text}</p>
  </div>
{/key}

<style>
  .card { background: var(--paper); border: var(--outline) solid var(--ink); border-radius: 16px; padding: 10px 14px; box-shadow: 0 4px 0 var(--ink);
          transform-origin: 0 50%; animation: pop .35s cubic-bezier(.34, 1.56, .64, 1) both; }
  @keyframes pop { from { opacity: 0; transform: scale(.92) translateY(4px); } to { opacity: 1; transform: none; } }
  .head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  b { font-family: var(--font-display); font-weight: 400; font-size: 24px; }
  span { font-family: var(--font-display); font-size: 20px; opacity: .7; }
  p { margin: 4px 0 0; font-weight: 700; font-size: 15px; line-height: 1.35; }
</style>
