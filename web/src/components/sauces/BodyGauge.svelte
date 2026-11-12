<script lang="ts">
  // The body: a drawn spoon the sauce runs off (thin), coats with a clean line through it (coats — the cook's nappe
  // test), holds on in a mound (thick) or stands on in a peak (stiff); under it the four bands and a marker at the
  // engine's body index (the bands' limits come from the server). Every state is drawn once and shown by class — a
  // static svg; the one drip is an HTML drop that falls once when it is shown (the page opening, or the sauce turning
  // thin or coating).
  import type { BodyClass, SauceEvaluation } from '../../lib/sauces';
  import type { Labelled } from '../../lib/spices';
  import type { Lang } from '../../lib/i18n';
  import { t } from '../../lib/i18n';
  let { body, bands, lang, blank = false }:
    { body: SauceEvaluation['body']; bands: (Labelled & { below: number })[]; lang: Lang; blank?: boolean } = $props();
  const CLASSES: BodyClass[] = ['thin', 'coats', 'thick', 'stiff'];
  const FILL: Record<BodyClass, string> = { thin: '#CFE8F2', coats: '#FFE7A3', thick: '#FFC98B', stiff: '#F2A27E' };
  // where the marker stands: each band an equal quarter of the bar, the index placed within its band (the open-ended
  // last one, sent as 99, read as 1.5 points wide)
  let at = $derived.by(() => {
    if (!bands.length) return 0;
    const i = Math.max(0, bands.findIndex((b) => body.index < b.below));
    const from = i ? bands[i - 1].below : 0, to = bands[i].below >= 99 ? from + 1.5 : bands[i].below;
    return (i + Math.max(0, Math.min(1, (body.index - from) / (to - from)))) / bands.length;
  });
</script>

<div class="body-gauge" class:blank>
  <div class="spoon-box">
    <svg viewBox="0 0 200 120" width="220" height="132" aria-hidden="true">
      <path class="handle" d="M8,34 Q60,42 112,52 L114,60 Q60,52 6,44 Z" />
      <ellipse class="bowl" cx="150" cy="58" rx="40" ry="25" />
      <g class="st" class:on={body.class === 'thin'}>
        <path d="M114,62 Q150,80 188,60 Q182,74 150,80 Q122,78 114,62 Z" fill={FILL.thin} />
        <path class="trail" d="M140,80 V110 M156,80 V104 M168,77 V96" />
      </g>
      <g class="st" class:on={body.class === 'coats'}>
        <path d="M112,56 Q150,30 190,56 Q186,80 150,83 Q116,80 112,56 Z" fill={FILL.coats} />
        <path class="line" d="M134,48 Q150,70 166,48" />
      </g>
      <g class="st" class:on={body.class === 'thick'}>
        <path d="M114,56 Q118,30 150,26 Q182,30 186,56 Q160,64 150,64 Q132,64 114,56 Z" fill={FILL.thick} />
        <path class="sheen" d="M132,40 Q150,30 166,38" />
      </g>
      <g class="st" class:on={body.class === 'stiff'}>
        <path d="M116,56 Q126,40 142,36 Q148,10 156,6 Q156,26 162,34 Q180,40 184,56 Q160,64 150,64 Q132,64 116,56 Z" fill={FILL.stiff} />
        <path class="sheen" d="M146,30 Q150,18 154,12" />
      </g>
      <ellipse class="rim" cx="150" cy="58" rx="40" ry="25" />
    </svg>
    <span class="drip" class:gone={blank || (body.class !== 'thin' && body.class !== 'coats')} style:--f={FILL[body.class] ?? FILL.coats}></span>
  </div>
  <div class="bar">
    {#each CLASSES as c (c)}<span class="band" class:on={!blank && body.class === c} style:background={FILL[c]}>{$t(`sauce.body.${c}`)}</span>{/each}
    <span class="marker" class:gone={blank} style:transform="translateX({at * 100}cqw)"></span>
  </div>
  <p class="says">{body[lang] || '·'}</p>
</div>

<style>
  .body-gauge { display: flex; flex-direction: column; align-items: center; gap: 8px; }
  .body-gauge.blank .spoon-box { opacity: .35; }
  .spoon-box { position: relative; contain: layout paint; }
  svg { display: block; overflow: visible; }
  .handle { fill: #D8CBB5; stroke: var(--ink); stroke-width: 3; stroke-linejoin: round; }
  .bowl { fill: #E9E1D2; }
  .rim { fill: none; stroke: var(--ink); stroke-width: 3.2; }
  .st { display: none; } .st.on { display: inline; }
  .st path { stroke: var(--ink); stroke-width: 2.4; stroke-linejoin: round; }
  .st .trail { fill: none; stroke: #8FC3D6; stroke-width: 4; stroke-linecap: round; }
  .st .line { fill: none; stroke: #E9E1D2; stroke-width: 5; stroke-linecap: round; }
  .st .sheen { fill: none; stroke: rgba(255, 255, 255, .6); stroke-width: 3; stroke-linecap: round; }
  /* one drop, falling once when it is shown: transform and opacity only */
  .drip { position: absolute; left: 150px; top: 84px; width: 11px; height: 15px; border: 2px solid var(--ink);
          border-radius: 50% 50% 50% 50% / 62% 62% 38% 38%; background: var(--f); opacity: 0;
          animation: drip 1.3s .5s cubic-bezier(.5, 0, .8, .4) 1 both; }
  @keyframes drip { 0% { transform: translateY(0) scale(.4); opacity: 0; } 20% { opacity: 1; } 80% { opacity: 1; }
                    100% { transform: translateY(36px) scale(1); opacity: 0; } }
  .gone { display: none !important; }
  .bar { align-self: stretch; container-type: inline-size; position: relative; display: flex; height: 44px; border: var(--outline) solid var(--ink);
         border-radius: 999px; overflow: hidden; }
  .band { flex: 1 1 0; display: grid; place-items: center; font-weight: 800; font-size: 13px; border-right: 2px solid var(--ink); }
  .band:last-of-type { border-right: 0; }
  .band.on { font-weight: 900; text-decoration: underline; text-decoration-thickness: 2px; }
  .marker { position: absolute; left: -7px; top: -4px; bottom: -4px; width: 14px; background: var(--ink); border-radius: 7px; box-shadow: 0 0 0 3px var(--paper); }
  .says { margin: 0; font-weight: 800; font-size: 15px; text-align: center; min-height: 1.3em; }
</style>
