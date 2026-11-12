<script lang="ts" module>
  let uid = 0;
</script>

<script lang="ts">
  // Butcher charts (beef, pork, lamb, chicken): a side-view silhouette, the cuts as regions clipped to the body and
  // separated by dashed butcher lines. Tap a region or a chip: it lights up (the others fade) and a card pops with
  // the cut's names and what it is for. Nothing in the svg animates; the card is a div (compositor-only pop).
  let { lang, animal }: { lang: 'en' | 'hu'; animal: string } = $props();
  const id = `cut${uid++}`;

  type Cut = { id: string; hu: string; en: string; use: { en: string; hu: string }; d: string; c: string; lx: number; ly: number; sm: boolean };
  type Decor = { d: string; fill: string };
  type Map = { body: string; head: string; limbs: string; thin: string; skin: string; limb: string; decor: Decor[]; cuts: Cut[]; eye: [number, number] };
  const K = (id: string, hu: string, en: string, ue: string, uh: string, d: string, c: string, lx: number, ly: number, sm = false): Cut =>
    ({ id, hu, en, use: { en: ue, hu: uh }, d, c, lx, ly, sm });

  const MAPS: Record<string, Map> = {
    beef: {
      body: 'M150,96 C210,80 300,76 402,82 C452,86 484,98 494,122 C502,142 500,178 490,198 C480,216 458,224 432,224 L190,224 C162,224 142,212 134,190 C126,168 126,122 150,96 Z',
      head: 'M152,100 C134,94 114,96 98,106 C84,116 70,132 63,148 C57,162 60,176 73,182 C86,188 104,182 116,172 L140,156 Z',
      limbs: 'M160,214 L160,258 M196,214 L196,258 M420,214 L420,258 M456,214 L456,258',
      thin: 'M494,122 C512,140 514,170 506,196',
      skin: '#F3E1C7', limb: '#F3E1C7',
      decor: [
        { d: 'M110,104 C100,92 96,80 100,66 C108,74 114,88 118,100 Z', fill: '#FFF4DF' },
        { d: 'M128,100 C128,88 132,76 140,68 C142,80 140,92 136,102 Z', fill: '#FFF4DF' },
        { d: 'M58,160 C58,148 72,144 82,150 C88,158 86,174 74,178 C64,180 58,172 58,160 Z', fill: '#F7B8A8' },
        { d: 'M146,256 h28 v10 h-28 Z M182,256 h28 v10 h-28 Z M406,256 h28 v10 h-28 Z M442,256 h28 v10 h-28 Z', fill: '#4A423C' },
        { d: 'M498,194 C508,192 516,202 510,212 C504,218 494,210 498,194 Z', fill: '#8B5A3C' },
      ],
      eye: [96, 132],
      cuts: [
        K('chuck', 'Tarja, lapocka', 'Chuck', 'pörkölt, gulyás, braising', 'pörkölt, gulyás, párolás', 'M120,70 L238,70 L238,172 L120,172 Z', '#E8708A', 182, 128),
        K('rib', 'Rostélyos', 'Rib', 'steaks, roasts', 'steak, sült', 'M238,70 L304,70 L304,150 L238,150 Z', '#D6336C', 271, 116),
        K('sirloin', 'Hátszín', 'Sirloin', 'steaks, quick roasts', 'steak, gyors sült', 'M304,70 L384,70 L384,138 L304,138 Z', '#C2185B', 344, 108),
        K('tenderloin', 'Bélszín', 'Tenderloin', 'the tenderest: steaks, tartare', 'a legpuhább: steak, tatár', 'M304,138 L384,138 L384,162 L304,162 Z', '#8E1E36', 344, 155),
        K('rump', 'Fartő', 'Rump', 'steaks, roasts', 'steak, sült', 'M384,70 L436,70 L430,162 L384,162 Z', '#B3263A', 410, 116),
        K('round', 'Comb, felsál', 'Round', 'slow roasts, thin slices', 'lassú sült, vékony szeletek', 'M436,70 L510,70 L510,228 L420,228 L430,162 Z', '#FF826E', 468, 150),
        K('brisket', 'Szegy', 'Brisket', 'slow braising, boiling', 'lassú párolás, főzés', 'M120,172 L238,172 L230,228 L120,228 Z', '#F28C28', 180, 202),
        K('plate', 'Oldalas, dagadó', 'Plate, flank', 'marinated, grilled fast', 'pácolva, gyorsan grillezve', 'M238,150 L304,150 L304,162 L430,162 L420,228 L230,228 Z', '#F5AE3D', 330, 198),
      ],
    },
    pork: {
      body: 'M150,104 C200,84 300,80 392,86 C446,90 482,106 492,132 C500,152 498,184 486,202 C474,220 450,226 424,226 L196,226 C166,226 144,214 136,192 C128,170 130,124 150,104 Z',
      head: 'M154,110 C136,104 116,108 102,118 C88,128 76,142 70,156 C66,168 72,180 86,184 C100,188 118,182 130,172 L148,158 Z',
      limbs: 'M172,218 L172,252 M208,218 L208,252 M412,218 L412,252 M448,218 L448,252',
      thin: 'M492,128 C506,120 516,128 510,138 C504,146 496,140 502,134',
      skin: '#F9C9CB', limb: '#F9C9CB',
      decor: [
        { d: 'M118,110 C110,96 114,82 128,74 C134,88 134,100 128,112 Z', fill: '#F7A1A8' },
        { d: 'M70,150 C62,150 55,156 55,164 C55,172 62,177 70,175 C74,166 74,158 70,150 Z', fill: '#F7A1A8' },
        { d: 'M160,250 h24 v9 h-24 Z M196,250 h24 v9 h-24 Z M400,250 h24 v9 h-24 Z M436,250 h24 v9 h-24 Z', fill: '#4A423C' },
      ],
      eye: [104, 136],
      cuts: [
        K('neck', 'Tarja', 'Neck', 'the all-rounder: pörkölt, roasts, grill', 'a mindenes: pörkölt, sült, grill', 'M120,74 L232,74 L232,140 L120,140 Z', '#E8708A', 176, 112),
        K('shoulder', 'Lapocka', 'Shoulder', 'pulled pork, pörkölt, mince', 'tépett hús, pörkölt, darált', 'M120,140 L232,140 L226,230 L120,230 Z', '#F28C28', 172, 186),
        K('loin', 'Karaj', 'Loin', 'chops, roasts — lean', 'szelet, sült — sovány', 'M232,74 L404,74 L404,136 L232,136 Z', '#D6336C', 318, 108),
        K('tenderloin', 'Szűzpecsenye', 'Tenderloin', 'medallions, quick roasts', 'medalion, gyors sült', 'M330,136 L404,136 L404,158 L330,158 Z', '#8E1E36', 367, 150, true),
        K('ribs', 'Oldalas', 'Ribs', 'slow roasting, glazed', 'lassan sütve, glazúrozva', 'M232,136 L330,136 L330,180 L230,180 Z', '#FF8A6B', 280, 162),
        K('belly', 'Dagadó', 'Belly', 'crackling, bacon, rolled roast', 'ropogós sült, szalonna, töltve', 'M230,180 L330,180 L330,158 L404,158 L412,230 L226,230 Z', '#F5AE3D', 320, 206),
        K('leg', 'Comb', 'Leg', 'roasts, schnitzel, ham', 'sült, rántott, sonka', 'M404,74 L510,74 L510,232 L412,232 Z', '#FF826E', 458, 150),
      ],
    },
    lamb: {
      body: 'M152,100 C206,84 300,80 394,86 C446,90 480,102 490,126 C498,146 496,180 486,198 C476,216 452,224 428,224 L194,224 C166,224 146,212 138,190 C130,168 130,122 152,100 Z',
      head: 'M156,106 C142,96 124,92 108,96 C94,100 84,112 82,126 C80,140 86,152 98,156 C110,160 126,156 138,148 L152,140 Z',
      limbs: 'M174,214 L174,258 M206,214 L206,258 M414,214 L414,258 M446,214 L446,258',
      thin: 'M490,126 C502,132 506,144 500,154',
      skin: '#F4EEE2', limb: '#E9DCC6',
      decor: [
        { d: 'M114,100 C102,88 88,86 78,94 C90,100 102,104 112,106 Z', fill: '#E9DCC6' },
        { d: 'M162,256 h24 v10 h-24 Z M194,256 h24 v10 h-24 Z M402,256 h24 v10 h-24 Z M434,256 h24 v10 h-24 Z', fill: '#4A423C' },
      ],
      eye: [100, 120],
      cuts: [
        K('neck', 'Nyak', 'Neck', 'stews, curries', 'ragu, curry', 'M120,70 L190,70 L190,172 L120,172 Z', '#E8708A', 156, 122),
        K('shoulder', 'Lapocka', 'Shoulder', 'slow roasting, pörkölt', 'lassú sült, pörkölt', 'M190,70 L268,70 L268,176 L190,176 Z', '#F28C28', 229, 126),
        K('rack', 'Borda', 'Rack', 'roast pink, grill', 'rózsaszínre sütve, grill', 'M268,70 L340,70 L340,150 L268,150 Z', '#D6336C', 304, 112),
        K('loin', 'Gerinc', 'Loin', 'quick roasting, chops', 'gyors sült, szelet', 'M340,70 L408,70 L408,150 L340,150 Z', '#B3263A', 374, 112),
        K('leg', 'Comb', 'Leg', 'roast whole', 'egészben sütve', 'M408,70 L510,70 L510,230 L414,230 Z', '#FF826E', 458, 150),
        K('breast', 'Szegy', 'Breast', 'slow, stuffed, rolled', 'lassan, töltve, tekerve', 'M120,172 L190,172 L190,176 L268,176 L268,150 L408,150 L414,230 L120,230 Z', '#F5AE3D', 290, 198),
      ],
    },
    chicken: {
      body: 'M150,118 C170,90 214,74 270,72 C330,70 392,84 432,110 C462,130 474,164 460,192 C444,222 400,236 330,238 C262,240 196,232 166,208 C140,188 132,148 150,118 Z',
      head: 'M156,122 C146,104 132,86 116,80 C100,74 84,80 82,96 C80,110 92,120 108,124 L150,132 Z',
      limbs: '',
      thin: 'M300,236 L294,270 M282,274 L306,274 M294,270 L288,280 M350,234 L356,270 M344,274 L368,274 M356,270 L362,280',
      skin: '#FFF4DF', limb: '#F2B705',
      decor: [
        { d: 'M98,80 C94,66 102,58 110,66 C112,54 126,52 128,66 C134,58 146,62 140,76 Z', fill: '#FF826E' },
        { d: 'M82,94 L62,101 L82,108 Z', fill: '#F2B705' },
        { d: 'M90,112 C84,122 90,132 100,128 C102,120 98,114 90,112 Z', fill: '#FF826E' },
        { d: 'M432,108 C454,88 474,76 490,84 C496,108 484,134 464,150 Z', fill: '#FFF4DF' },
      ],
      eye: [100, 92],
      cuts: [
        K('breast', 'Mell', 'Breast', 'quick: grill, poach, schnitzel', 'gyors: grill, buggyantás, rántott', 'M120,130 L262,130 L262,244 L120,244 Z', '#FFD23F', 196, 186),
        K('wing', 'Szárny', 'Wing', 'crispy roasting, stock', 'ropogós sült, alaplé', 'M262,104 C300,96 344,104 360,130 C340,160 296,164 262,150 Z', '#F5AE3D', 312, 132),
        K('back', 'Hát, far', 'Back', 'stock, soup', 'alaplé, húsleves', 'M150,60 L500,60 L500,112 L360,112 L360,130 L262,104 L262,130 L150,130 Z', '#D6A27C', 360, 90),
        K('thigh', 'Felsőcomb', 'Thigh', 'the juiciest: paprikás', 'a legszaftosabb: paprikás', 'M360,112 L500,112 L500,190 L360,190 L360,130 Z', '#F28C28', 428, 156),
        K('drumstick', 'Alsócomb', 'Drumstick', 'roasting, frying', 'sütve, rántva', 'M262,150 C296,164 340,160 360,130 L360,190 L500,190 L500,244 L262,244 Z', '#FF826E', 378, 216),
      ],
    },
  };
  let map = $derived(MAPS[animal] ?? MAPS.beef);
  let sel = $state<Cut | null>(null);
  $effect(() => { void animal; sel = null; });
</script>

<div class="illus">
  <svg viewBox="40 40 500 250" class="map" role="img" aria-label={lang === 'hu' ? 'Húsrészek térképe' : 'Cut map'}>
    <defs><clipPath id="{id}-body"><path d={map.body} /></clipPath></defs>
    <!-- legs and tail: outlined tubes (wide ink under the limb colour), behind the body -->
    <path class="tube-ol" d={map.limbs} />
    <path class="tube" d={map.limbs} stroke={map.limb} />
    <path class="tube-ol thin" d={map.thin} />
    <path class="tube thin" d={map.thin} stroke={map.limb} />
    <g clip-path="url(#{id}-body)">
      {#each map.cuts as c (c.id)}
        <path d={c.d} fill={c.c} class="region" class:dim={sel && sel.id !== c.id} onclick={() => (sel = c)} role="presentation" />
      {/each}
      {#each map.cuts as c (c.id)}<path d={c.d} class="butcher" />{/each}
    </g>
    <path class="bodyline" d={map.body} />
    <path class="shape" d={map.head} fill={map.skin} />
    {#each map.decor as x}<path class="shape thin" d={x.d} fill={x.fill} />{/each}
    {#if sel}<g clip-path="url(#{id}-body)"><path d={sel.d} class="selline" /></g>{/if}
    {#each map.cuts as c (c.id)}
      <text x={c.lx} y={c.ly + 5} text-anchor="middle" class="lbl" class:sm={c.sm} class:dim={sel && sel.id !== c.id}>{lang === 'hu' ? c.hu.split(',')[0] : c.en.split(',')[0]}</text>
    {/each}
    <circle cx={map.eye[0]} cy={map.eye[1]} r="5" class="eye" /><circle cx={map.eye[0] - 1.5} cy={map.eye[1] - 1.5} r="1.6" fill="#fff" />
  </svg>
  {#key sel}
    <div class="info" class:empty={!sel}>
      {#if sel}<b>{lang === 'hu' ? sel.hu : sel.en}</b><span>{lang === 'hu' ? sel.en : sel.hu}</span><p>{sel.use[lang]}</p>
      {:else}<p>{lang === 'hu' ? 'Koppints egy részre.' : 'Tap a cut.'}</p>{/if}
    </div>
  {/key}
  <div class="chips">{#each map.cuts as c (c.id)}<button class="chip pressable" class:on={sel?.id === c.id} style:--c={c.c} onclick={() => (sel = c)}>{lang === 'hu' ? c.hu : c.en}</button>{/each}</div>
</div>

<style>
  .illus { display: flex; flex-direction: column; gap: 8px; }
  .map { width: 100%; max-height: 270px; }
  .tube-ol { fill: none; stroke: var(--ink); stroke-width: 30; stroke-linecap: round; stroke-linejoin: round; }
  .tube { fill: none; stroke-width: 21; stroke-linecap: round; stroke-linejoin: round; }
  .tube-ol.thin { stroke-width: 12; } .tube.thin { stroke-width: 6; }
  .lbl.sm { font-size: 11px; }
  .shape { stroke: var(--ink); stroke-width: 5; stroke-linejoin: round; } .shape.thin { stroke-width: 3.5; }
  .region { stroke: none; cursor: pointer; }
  .region.dim, .lbl.dim { opacity: .42; }
  .butcher { fill: none; stroke: var(--ink); stroke-width: 2.5; stroke-dasharray: 7 6; stroke-linecap: round; }
  .bodyline { fill: none; stroke: var(--ink); stroke-width: 5; stroke-linejoin: round; }
  .selline { fill: none; stroke: var(--ink); stroke-width: 7; stroke-linejoin: round; }
  .lbl { font-weight: 900; font-size: 15px; fill: var(--ink); paint-order: stroke; stroke: rgba(255, 255, 255, .75); stroke-width: 4; pointer-events: none; }
  .eye { fill: var(--ink); }
  .info { min-height: 58px; display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; transform-origin: 0 50%; animation: pop .35s cubic-bezier(.34, 1.56, .64, 1) both; }
  .info.empty { animation: none; }
  @keyframes pop { from { opacity: 0; transform: scale(.9) translateY(4px); } to { opacity: 1; transform: none; } }
  .info b { font-family: var(--font-display); font-weight: 400; font-size: 28px; }
  .info span { font-weight: 800; opacity: .6; }
  .info p { margin: 0; font-weight: 700; flex-basis: 100%; }
  .info.empty p { opacity: .6; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { min-height: var(--touch); min-width: var(--touch); padding: 0 14px; border-radius: 999px; border: var(--outline) solid var(--ink); background: var(--paper); font-weight: 800; font-size: 15px; }
  .chip.on { background: var(--c); }
</style>
