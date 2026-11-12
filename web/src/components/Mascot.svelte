<script lang="ts">
  // The mascot — a cast-iron pan with a fried egg, big eyes and rubber-hose arms. See lib/mascot.ts for the rules:
  // every moving part is an HTML div (own compositor layer) wrapping a static svg drawn in the 340×260 design space;
  // animations touch only transform/opacity of those divs (guarded by tests/mascot.test.ts).
  import { onDestroy, onMount } from 'svelte';
  import { ACTIONS, W, box, createBrain, vb, type Expr } from '../lib/mascot';

  let {
    size = 300, act = null, actKey = 0, expr = 'neutral', loop = null, alive = true, breathe = true,
    night = false, prop = null, tappable = false, ontap, label = '',
  }: {
    size?: number; act?: string | null; actKey?: number; expr?: Expr; loop?: string | null; alive?: boolean;
    breathe?: boolean; night?: boolean; prop?: 'cap' | 'chef' | null; tappable?: boolean; ontap?: () => void;
    label?: string;                                   // the tap area's accessible name (translated by the caller)
  } = $props();

  let playing = $state<string | null>(null);
  let held = $state<string | null>(null);          // a pose that stays (shrug) until the next action
  let blink = $state('');
  let wobble = $state(false);
  let look = $state<[number, number]>([0, 0]);
  let hidden = $state(false);
  let endTimer: ReturnType<typeof setTimeout> | null = null;

  /** Play one action; returns when it has finished. A new action replaces the one playing. `keep` leaves the action
   *  on until stop() — for scripts/anim-sheet.py, which steps the paused animations frame by frame. */
  export function play(id: string, keep = false): Promise<void> {
    const def = ACTIONS[id];
    if (!def) return Promise.resolve();
    if (endTimer) clearTimeout(endTimer);
    playing = null; held = null;
    return new Promise((resolve) => {
      requestAnimationFrame(() => {            // a frame without the class restarts the same action cleanly
        playing = id;
        if (keep) { resolve(); return; }
        endTimer = setTimeout(() => {
          endTimer = null;
          if (def.hold) held = id;
          playing = null;
          resolve();
        }, def.ms);
      });
    });
  }

  export function stop(): void {
    if (endTimer) clearTimeout(endTimer);
    endTimer = null; playing = null; held = null;
  }

  let face = $derived<Expr>(playing ? (ACTIONS[playing].expr ?? expr) : loop ? (ACTIONS[loop]?.expr ?? expr) : expr);
  let actionClass = $derived(playing ? `a-${playing}` : loop ? `a-${loop} loop` : held ? `a-${held} held` : '');

  $effect(() => { void actKey; if (act) play(act); });

  const brain = createBrain({
    blink: (double) => { blink = double ? 'blink2' : 'blink'; setTimeout(() => (blink = ''), double ? 460 : 240); },
    look: (dx, dy) => (look = [dx, dy]),
    wobble: () => { wobble = true; setTimeout(() => (wobble = false), 950); },
    canMove: () => !playing && !loop && expr !== 'asleep' && !hidden,
  });
  const onVis = () => { hidden = document.hidden; };
  onMount(() => {
    document.addEventListener('visibilitychange', onVis);
  });
  // `alive` is live: a screen may let the face rest and wake it again (it was read once, at mount, until 2026-10-19 —
  // switching it off later did nothing). start() is idempotent; stop() clears every pending timer.
  $effect(() => { if (alive) brain.start(); else brain.stop(); });
  onDestroy(() => {
    brain.stop();
    if (endTimer) clearTimeout(endTimer);
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVis);
  });

  function tap() {
    if (!tappable) return;
    play('giggle');
    ontap?.();
  }

  // static geometry, in design units
  const EYE = { l: [110, 178], r: [190, 178] } as const;
  const shoulder = { l: [44, 176], r: [256, 176] } as const;   // upper arm 30, forearm 28 (design units)
</script>

<div class="m e-{face} {actionClass} {blink}" class:breathe={breathe && !hidden} class:night class:wob={wobble}
     class:cap={prop === 'cap' || face === 'asleep'} class:chef={prop === 'chef'}
     style:zoom={size / W} aria-hidden="true">
  <div class="p shadow" style={box(40, 212, 220, 24, 150, 224)}>
    <svg viewBox={vb(40, 212, 220, 24)}><ellipse class="shadow-fill" cx="150" cy="224" rx="108" ry="10" /></svg>
  </div>

  <div class="p rig" style={box(0, 0, 340, 260, 150, 228)}>
    <div class="p squash" style={box(0, 0, 340, 260, 150, 228)}>
      <!-- the handle, behind the body; it wags like a tail -->
      <div class="p handle" style={box(250, 62, 90, 64, 262, 110)}>
        <svg viewBox={vb(250, 62, 90, 64)}>
          <g transform="rotate(-17 262 110)">
            <rect class="iron ol" x="252" y="100" width="80" height="20" rx="10" stroke-width="4" />
            <rect class="iron-hi" x="262" y="104" width="52" height="4" rx="2" />
            <circle class="iron-lo ol" cx="319" cy="110" r="4.5" stroke-width="2.5" />
          </g>
        </svg>
      </div>

      <!-- the chef's toque sits on the back of the rim (cook mode) -->
      <div class="p prop-chef" style={box(96, 0, 118, 80, 155, 70)}>
        <svg viewBox={vb(96, 0, 118, 80)}>
          <path class="cloth ol" stroke-width="3.5" d="M116,52 C98,50 98,24 119,24 C121,8 146,3 155,17 C165,4 192,9 189,28 C207,28 207,53 187,53 Z" />
          <rect class="cloth ol" x="119" y="49" width="64" height="21" rx="6" stroke-width="3.5" />
          <path class="ink-line" stroke-width="2.2" d="M135,53 V66 M151,53 V68 M167,53 V66" />
        </svg>
      </div>

      <!-- body: rim, cooking surface and the front wall that carries the face -->
      <div class="p body" style={box(28, 56, 244, 172, 150, 228)}>
        <svg viewBox={vb(28, 56, 244, 172)}>
          <path class="iron ol" stroke-width="4" d="M36,104 C37,150 41,178 46,192 A104,26 0 0 0 254,192 C259,178 263,150 264,104 A114,40 0 0 1 36,104 Z" />
          <path class="iron-hi" d="M45,126 C46,158 50,180 57,193 L69,197 C62,181 58,158 57,131 Z" />
          <path class="iron-lo" d="M70,207 A104,26 0 0 0 232,207 L238,203 A106,24 0 0 1 64,203 Z" />
          <path class="rimlight" stroke-width="3" d="M39,114 C40,150 44,175 49,189" />
          <ellipse class="rim ol" cx="150" cy="104" rx="114" ry="40" stroke-width="4" />
          <ellipse class="iron-lo ol" cx="150" cy="104" rx="100" ry="33" stroke-width="3" />
          <ellipse class="floor" cx="150" cy="111" rx="86" ry="24" />
          <path class="sheen" stroke-width="3" d="M74,95 Q150,74 226,95" />
          <path class="rimlight" stroke-width="4.5" d="M58,86 Q96,68 150,65" />
          <path class="rimlight dim" stroke-width="3" d="M236,79 Q250,86 257,96" />
        </svg>
      </div>

      <!-- the fried egg: white, and a yolk that wobbles on its own; the wrapper flips -->
      <div class="p eggw" style={box(92, 80, 112, 52, 148, 112)}>
        <div class="p egg" style={box(92, 80, 112, 52, 148, 124, [92, 80])}>
          <svg viewBox={vb(92, 80, 112, 52)}>
            <path class="eggwhite ol" stroke-width="3" d="M100,111 C95,98 114,90 129,93 C140,85 164,85 176,94 C193,96 200,110 189,119 C180,129 152,127 139,125 C121,130 103,124 100,111 Z" />
            <path class="eggshade" d="M110,119 C126,127 170,127 186,116 C178,126 152,127 139,125 C124,128 112,124 110,119 Z" />
          </svg>
        </div>
        <div class="p yolk" style={box(132, 86, 42, 34, 153, 116, [92, 80])}>
          <svg viewBox={vb(132, 86, 42, 34)}>
            <ellipse class="yolkfill ol" cx="153" cy="104" rx="16" ry="13" stroke-width="3" />
            <path class="yolkshade" d="M140,108 Q153,121 166,108 Q161,116 153,116 Q145,116 140,108 Z" />
            <ellipse class="glint" cx="147" cy="99" rx="5" ry="3.4" transform="rotate(-22 147 99)" />
          </svg>
        </div>
      </div>

      <!-- the face lives on the wall; the whole face shifts a little when the pan looks around -->
      <div class="p face" style={box(56, 134, 188, 88, 150, 180)}>
        {#each (['l', 'r'] as const) as s}
          {@const [cx, cy] = EYE[s]}
          <div class="p eye {s}" style={box(cx - 18, cy - 22, 36, 44, cx, cy, [56, 134])}>
            <svg viewBox={vb(cx - 18, cy - 22, 36, 44)}><ellipse class="eyewhite" {cx} {cy} rx="17" ry="21" /></svg>
            <!-- .look carries the glance (inline), .pupil the expression and the actions' eye moves -->
            <div class="p look" style="{box(cx - 9, cy - 10, 20, 24, cx + 1, cy + 2, [cx - 18, cy - 22])};transform:translate({look[0]}px,{look[1]}px)">
              <div class="p pupil" style={box(cx - 9, cy - 10, 20, 24, cx + 1, cy + 2, [cx - 9, cy - 10])}>
                <svg viewBox={vb(cx - 9, cy - 10, 20, 24)}>
                  <ellipse class="pupilfill" cx={cx + 1} cy={cy + 3} rx="9" ry="11" />
                  <circle class="glint" cx={cx - 3} cy={cy - 2} r="3.6" />
                  <circle class="glint" cx={cx + 4.5} cy={cy + 8} r="1.7" />
                </svg>
              </div>
            </div>
            <svg class="ring" viewBox={vb(cx - 18, cy - 22, 36, 44)}><ellipse class="ol none" {cx} {cy} rx="15.6" ry="19.6" stroke-width="3" /></svg>
            <div class="p lid" style={box(cx - 18, cy - 22, 36, 44, cx, cy - 22, [cx - 18, cy - 22])}>
              <svg viewBox={vb(cx - 18, cy - 22, 36, 44)}><ellipse class="iron" {cx} {cy} rx="17.6" ry="21.6" /></svg>
            </div>
          </div>
          <div class="p joy {s}" style={box(cx - 18, cy - 14, 36, 28, cx, cy, [56, 134])}>
            <svg viewBox={vb(cx - 18, cy - 14, 36, 28)}><path class="creamline" stroke-width="5" d="M{cx - 14},{cy + 7} Q{cx},{cy - 13} {cx + 14},{cy + 7}" /></svg>
          </div>
          <div class="p shut {s}" style={box(cx - 18, cy - 8, 36, 26, cx, cy, [56, 134])}>
            <svg viewBox={vb(cx - 18, cy - 8, 36, 26)}>
              <path class="creamline" stroke-width="4.5" d="M{cx - 14},{cy + 1} Q{cx},{cy + 15} {cx + 14},{cy + 1}" />
              <path class="creamline" stroke-width="2.6" d="M{cx - 12},{cy + 7} l-4,4 M{cx + 12},{cy + 7} l4,4" />
            </svg>
          </div>
          <div class="p brow {s}" style={box(cx - 20, 136, 40, 20, cx, 147, [56, 134])}>
            <svg viewBox={vb(cx - 20, 136, 40, 20)}>
              <path class="browline" stroke-width="6" d={s === 'l' ? 'M95,150 Q110,141 125,148' : 'M175,148 Q190,141 205,150'} />
            </svg>
          </div>
          <div class="p cheek {s}" style={box(s === 'l' ? 64 : 208, 190, 28, 18, s === 'l' ? 78 : 222, 199, [56, 134])}>
            <svg viewBox={vb(s === 'l' ? 64 : 208, 190, 28, 18)}><ellipse class="cheekfill" cx={s === 'l' ? 78 : 222} cy="199" rx="12" ry="7" /></svg>
          </div>
        {/each}
        <!-- mouths: one shows at a time (opacity) -->
        {#snippet mouth(name: string)}
          <div class="p mouth m-{name}" style={box(128, 186, 44, 32, 150, 202, [56, 134])}>
            <svg viewBox={vb(128, 186, 44, 32)}>
              {#if name === 'smile'}<path class="creamline" stroke-width="4" d="M139,199 Q150,209 161,199" />
              {:else if name === 'cat'}<path class="creamline" stroke-width="3.5" d="M137,199 q6.5,8 13,0 q6.5,8 13,0" />
              {:else if name === 'grin'}
                <path class="mouthfill creamol" stroke-width="3" d="M136,196 Q150,198 164,196 Q162,214 150,214 Q138,214 136,196 Z" />
                <path class="tongue" d="M142.5,208 Q150,203 157.5,208 Q155,213 150,213 Q145,213 142.5,208 Z" />
              {:else if name === 'o'}<ellipse class="mouthfill creamol" cx="150" cy="203" rx="6.5" ry="8" stroke-width="3" />
              {:else if name === 'bigo'}
                <ellipse class="mouthfill creamol" cx="150" cy="203" rx="10" ry="12" stroke-width="3" />
                <ellipse class="tongue" cx="150" cy="210" rx="6" ry="3" />
              {:else if name === 'flat'}<path class="creamline" stroke-width="4" d="M141,203 L159,203" />
              {:else if name === 'wavy'}<path class="creamline" stroke-width="3.5" d="M136,205 q4.5,-5 9,0 t9,0 t9,0" />
              {:else if name === 'tongue'}
                <path class="creamline" stroke-width="3.5" d="M140,200 Q150,207 160,200" />
                <path class="tongue creamol" stroke-width="2" d="M152.5,203.5 q4,8 9,1.5 q-3,-3.5 -9,-1.5 Z" />
              {:else if name === 'sleep'}<ellipse class="mouthfill creamol" cx="150" cy="205" rx="4" ry="5" stroke-width="2.5" />{/if}
            </svg>
          </div>
        {/snippet}
        {#each ['smile', 'cat', 'grin', 'o', 'bigo', 'flat', 'wavy', 'tongue', 'sleep'] as name}{@render mouth(name)}{/each}
      </div>

      <!-- arms: shoulder → elbow → wrist, each its own layer; the right glove can hold a wooden spoon -->
      {#each (['l', 'r'] as const) as s}
        {@const [sx, sy] = shoulder[s]}
        {@const k = s === 'l' ? 1 : -1}
        <div class="p arm {s}" style={box(sx - 8, sy - 5, 16, 40, sx, sy)}>
          <svg viewBox={vb(sx - 8, sy - 5, 16, 40)}>
            <path class="hose-ol" d="M{sx},{sy} L{sx},{sy + 30}" /><path class="hose" d="M{sx},{sy} L{sx},{sy + 30}" />
          </svg>
          <div class="p fore" style={box(sx - 8, sy + 25, 16, 38, sx, sy + 30, [sx - 8, sy - 5])}>
            <svg viewBox={vb(sx - 8, sy + 25, 16, 38)}>
              <path class="hose-ol" d="M{sx},{sy + 30} L{sx},{sy + 58}" /><path class="hose" d="M{sx},{sy + 30} L{sx},{sy + 58}" />
            </svg>
            <div class="p glove" style={box(sx - 20, sy + 48, 40, 46, sx, sy + 56, [sx - 8, sy + 25])}>
              {#if s === 'r'}
                <div class="p spoon" style={box(sx - 9, sy + 72, 18, 58, sx, sy + 76, [sx - 20, sy + 48])}>
                  <svg viewBox={vb(sx - 9, sy + 72, 18, 58)}>
                    <path class="wood ol" stroke-width="2.5" d="M{sx - 2.8},{sy + 76} H{sx + 2.8} V{sy + 108} H{sx - 2.8} Z" />
                    <ellipse class="wood ol" cx={sx} cy={sy + 116} rx="6.5" ry="10" stroke-width="2.5" />
                  </svg>
                </div>
              {/if}
              <svg viewBox={vb(sx - 20, sy + 48, 40, 46)}>
                <rect class="cuff ol" x={sx - 10.5} y={sy + 52} width="21" height="9" rx="4" stroke-width="3" />
                <path class="glovefill ol" stroke-width="3" d="M{sx - 12},{sy + 60} C{sx - 16.5},{sy + 74} {sx - 11},{sy + 89} {sx},{sy + 89} C{sx + 11},{sy + 89} {sx + 16.5},{sy + 76} {sx + 13},{sy + 61} Z" />
                <path class="glovefill ol" stroke-width="3" d="M{sx + 12 * k},{sy + 66} q{8 * k},2 {6 * k},11 q{-4 * k},3.5 {-7.5 * k},-3 Z" />
                <path class="ink-line" stroke-width="2.2" d="M{sx - 5.5},{sy + 80} V{sy + 87} M{sx + 0.5},{sy + 81} V{sy + 88}" />
              </svg>
            </div>
          </div>
        </div>
      {/each}

      <!-- the nightcap (asleep) -->
      <div class="p prop-cap" style={box(14, 26, 124, 72, 98, 76)}>
        <svg viewBox={vb(14, 26, 124, 72)}>
          <path class="capfill ol" stroke-width="3.5" d="M66,86 C58,64 44,50 31,45 C47,40 76,40 101,54 C115,60 125,66 131,71 Q97,64 66,86 Z" />
          <circle class="capdot" cx="62" cy="58" r="4" /><circle class="capdot" cx="84" cy="54" r="4" /><circle class="capdot" cx="104" cy="62" r="3.5" /><circle class="capdot" cx="76" cy="70" r="3.5" />
          <path class="cloth ol" stroke-width="3.5" d="M62,86 Q96,63 133,69 L134,77 Q98,71 66,93 Z" />
          <circle class="cloth ol" cx="29" cy="45" r="8" stroke-width="3.5" />
        </svg>
      </div>

      <!-- effects: hidden until an action shows them -->
      {#each [[112, 74], [150, 60], [188, 74]] as [x, y], i}
        <div class="p fx puff p{i + 1}" style={box(x - 20, y - 16, 40, 30, x, y)}>
          <svg viewBox={vb(x - 20, y - 16, 40, 30)}>
            <g class="cloudol"><circle cx={x - 8} cy={y + 3} r="7.5" /><circle cx={x} cy={y - 4} r="9.5" /><circle cx={x + 9} cy={y + 2} r="7.5" /></g>
            <g class="cloud"><circle cx={x - 8} cy={y + 3} r="7.5" /><circle cx={x} cy={y - 4} r="9.5" /><circle cx={x + 9} cy={y + 2} r="7.5" /></g>
          </svg>
        </div>
      {/each}
      {#each [[38, 72, 13], [290, 64, 12], [72, 26, 10], [236, 20, 14], [306, 124, 9]] as [x, y, r], i}
        <div class="p fx spark s{i + 1}" style={box(x - 16, y - 16, 32, 32, x, y)}>
          <svg viewBox={vb(x - 16, y - 16, 32, 32)}>
            <path class="sparkfill ol" stroke-width="2.2" d="M{x},{y - r} Q{x},{y} {x + r},{y} Q{x},{y} {x},{y + r} Q{x},{y} {x - r},{y} Q{x},{y} {x},{y - r} Z" />
          </svg>
        </div>
      {/each}
      {#each [[230, 58, 1], [252, 36, 1.3], [278, 14, 1.6]] as [x, y, k], i}
        <div class="p fx zz z{i + 1}" style={box(x - 14, y - 14, 30, 30, x, y)}>
          <svg viewBox={vb(x - 14, y - 14, 30, 30)}>
            <path class="zol" d="M{x - 6 * k},{y - 6 * k} h{12 * k} l{-12 * k},{12 * k} h{12 * k}" stroke-width={7 * Math.min(k, 1.2)} />
            <path class="zline" d="M{x - 6 * k},{y - 6 * k} h{12 * k} l{-12 * k},{12 * k} h{12 * k}" stroke-width={3.4 * Math.min(k, 1.2)} />
          </svg>
        </div>
      {/each}
      <div class="p fx sweat" style={box(232, 140, 20, 26, 242, 152)}>
        <svg viewBox={vb(232, 140, 20, 26)}>
          <path class="dropfill ol" stroke-width="2.2" d="M242,142 C248,150 250,156 242,161 C234,156 236,150 242,142 Z" /><ellipse class="glint" cx="240" cy="154" rx="1.6" ry="2.6" />
        </svg>
      </div>
      {#each [[62, 70], [240, 58]] as [x, y], i}
        <div class="p fx heart h{i + 1}" style={box(x - 13, y - 12, 26, 24, x, y)}>
          <svg viewBox={vb(x - 13, y - 12, 26, 24)}>
            <path class="heartfill ol" stroke-width="2.2" d="M{x},{y + 8} C{x - 14},{y - 1} {x - 9},{y - 12} {x},{y - 5} C{x + 9},{y - 12} {x + 14},{y - 1} {x},{y + 8} Z" />
          </svg>
        </div>
      {/each}
      <div class="p fx bang" style={box(244, 14, 50, 52, 268, 40)}>
        <svg viewBox={vb(244, 14, 50, 52)}>
          <path class="bangfill ol" stroke-width="3" d="M268,16 L274,30 L289,25 L282,38 L292,48 L278,49 L276,63 L267,52 L256,61 L256,48 L245,42 L257,36 L252,23 L264,29 Z" />
          <path class="ink-line" stroke-width="5" d="M268,29 V43" /><circle class="inkdot" cx="268" cy="50" r="3" />
        </svg>
      </div>
      {#each [[58, 66], [266, 52]] as [x, y], i}
        <div class="p fx note n{i + 1}" style={box(x - 12, y - 16, 24, 30, x, y)}>
          <svg viewBox={vb(x - 12, y - 16, 24, 30)}>
            <ellipse class="inkdot" cx={x - 3} cy={y + 8} rx="5.5" ry="4.2" transform="rotate(-22 {x - 3} {y + 8})" />
            <path class="ink-line" stroke-width="2.6" d="M{x + 2},{y + 7} V{y - 13} q7,3 8,10" />
          </svg>
        </div>
      {/each}
      {#each [[232, 104, 4.5], [248, 86, 6.5], [270, 62, 9.5]] as [x, y, r], i}
        <div class="p fx dot d{i + 1}" style={box(x - 12, y - 12, 24, 24, x, y)}>
          <svg viewBox={vb(x - 12, y - 12, 24, 24)}><circle class="cloud ol" cx={x} cy={y} {r} stroke-width="2.5" /></svg>
        </div>
      {/each}
      {#each [[106, 100], [194, 104], [124, 122], [176, 92]] as [x, y], i}
        <div class="p fx bubble b{i + 1}" style={box(x - 7, y - 7, 14, 14, x, y)}>
          <svg viewBox={vb(x - 7, y - 7, 14, 14)}><circle class="eggwhite ol" cx={x} cy={y} r="3.6" stroke-width="1.6" /></svg>
        </div>
      {/each}
    </div>
  </div>
  {#if tappable}<button class="hit" onclick={tap} aria-label={label}></button>{/if}
</div>

<style>
  .m {
    --iron: #3B3430; --iron-hi: #4F4741; --iron-lo: #2A2420; --floor: #342D29; --rim: #4A423C;
    --m-ol: var(--ink); --rimlight: #FFF4DF; --brow: #A79788; --cheek: #FF8FA3; --mouth: #6E1E24; --tongue: #FF7B8A;
    --eggshade: #EFE5D3; --yolk: #FFB703; --yolkshade: #F08C00;
    position: relative; width: 340px; height: 260px; pointer-events: none; contain: layout style;
  }
  .m.night { --m-ol: #7A6D62; }
  /* only the rig and the squash wrapper hold permanent layers: the breath scales the squash layer, and separately
     composited children under a scaling parent get re-rasterised at the new scale (measured on the kiosk: 20–60 % CPU
     breathing vs ~1 % still). Parts are promoted by Chrome only while their own animation runs. */
  .p { position: absolute; }
  .rig, .squash { will-change: transform; }
  :global(.demo-layers) .p { will-change: transform; }
  .p > svg, .ring { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; display: block; }
  .fx, .mouth, .joy, .shut, .prop-cap, .prop-chef, .spoon { opacity: 0; }
  .fx, .prop-cap, .prop-chef, .spoon, .shut, .joy, .cheek { will-change: auto; }

  /* fills and lines (static styling of the static svg) */
  .ol { stroke: var(--m-ol); stroke-linejoin: round; }
  .none { fill: none; }
  .iron { fill: var(--iron); } .iron-hi { fill: var(--iron-hi); } .iron-lo { fill: var(--iron-lo); }
  .floor { fill: var(--floor); } .rim { fill: var(--rim); }
  .sheen { fill: none; stroke: var(--iron-hi); opacity: .8; stroke-linecap: round; }
  .rimlight { fill: none; stroke: var(--rimlight); stroke-linecap: round; opacity: .8; }
  .rimlight.dim { opacity: .45; }
  .shadow-fill { fill: rgba(31, 26, 23, .2); }
  .night .shadow-fill { fill: rgba(0, 0, 0, .4); }
  .eggwhite { fill: #fff; } .eggshade { fill: var(--eggshade); }
  .yolkfill { fill: var(--yolk); } .yolkshade { fill: var(--yolkshade); }
  .glint { fill: #fff; opacity: .95; }
  .eyewhite { fill: #fff; } .pupilfill { fill: var(--ink); }
  .lash, .creamline { fill: none; stroke: var(--rimlight); stroke-linecap: round; stroke-linejoin: round; }
  .browline { fill: none; stroke: var(--brow); stroke-linecap: round; }
  .cheekfill { fill: var(--cheek); }
  .mouthfill { fill: var(--mouth); } .creamol { stroke: var(--rimlight); } .tongue { fill: var(--tongue); }
  .hose-ol { stroke: var(--m-ol); stroke-width: 15; stroke-linecap: round; fill: none; }
  .hose { stroke: var(--iron); stroke-width: 9; stroke-linecap: round; fill: none; }
  .glovefill { fill: #fff; } .cuff { fill: var(--cream); }
  .ink-line { stroke: var(--ink); fill: none; stroke-linecap: round; } .inkdot { fill: var(--ink); }
  .wood { fill: #C98F55; } .cloth { fill: #fff; } .capfill { fill: var(--sky); } .capdot { fill: #fff; opacity: .85; }
  .cloudol { fill: var(--ink); stroke: var(--ink); stroke-width: 5; } .cloud { fill: var(--cream); }
  .sparkfill { fill: var(--butter); } .dropfill { fill: var(--sky); } .heartfill { fill: var(--berry); }
  .bangfill { fill: var(--butter); }   /* reads on cream and on the coral timer card */
  .zol { fill: none; stroke: var(--ink); stroke-linecap: round; stroke-linejoin: round; }
  .zline { fill: none; stroke: var(--cream); stroke-linecap: round; stroke-linejoin: round; }

  /* no clipping on the eye: a rounded clip of moving children costs a mask pass per frame on the kiosk's GPU (measured);
     the pupil's travel stays inside the white, and the lid is an ellipse that scales down from the top */
  .ring { pointer-events: none; }

  /* ---- rest pose ---- */
  /* hands on hips: elbows out, gloves back against the base — hanging arms read as legs */
  .arm.l { transform: rotate(58deg); } .arm.l .fore { transform: rotate(-104deg); } .arm.l .glove { transform: rotate(26deg); }
  .arm.r { transform: rotate(-58deg); } .arm.r .fore { transform: rotate(104deg); } .arm.r .glove { transform: rotate(-26deg); }
  .lid { transform: scaleY(0); transition: transform .16s ease-out; }
  .look { transition: transform .24s cubic-bezier(.3, 1.6, .5, 1); }
  .pupil { transition: transform .18s ease-out; }
  .brow { transition: transform .18s ease-out; }
  .mouth { transition: opacity .1s linear; }
  .cheek { opacity: .5; transition: opacity .2s; }
  .eye, .joy, .shut { transition: opacity .12s; }
  .prop-cap, .prop-chef { transition: opacity .4s; }
  .cap .prop-cap, .chef .prop-chef { opacity: 1; }

  /* ---- expressions (faces) ---- */
  .e-neutral .m-smile, .e-proud .m-smile, .e-happy .m-cat, .e-joy .m-grin, .e-surprised .m-o, .e-sleepy .m-flat,
  .e-asleep .m-sleep, .e-worried .m-wavy, .e-focus .m-tongue, .e-alarm .m-bigo { opacity: 1; }
  .e-happy .brow { transform: translateY(-2px); }
  .e-joy .brow, .e-proud .brow { transform: translateY(-4px); }
  .e-surprised .brow { transform: translateY(-7px); }
  .e-alarm .brow { transform: translateY(-9px); }
  .e-worried .brow.l { transform: translateY(-2px) rotate(-16deg); } .e-worried .brow.r { transform: translateY(-2px) rotate(16deg); }
  .e-focus .brow.l { transform: translateY(3px) rotate(12deg); } .e-focus .brow.r { transform: translateY(3px) rotate(-12deg); }
  .e-asleep .brow, .e-sleepy .brow { transform: translateY(3px); }
  .e-joy .eye { opacity: 0; } .e-joy .joy { opacity: 1; }
  .e-asleep .eye { opacity: 0; } .e-asleep .shut { opacity: 1; }
  .e-sleepy .lid { transform: scaleY(.52); }
  .e-focus .lid { transform: scaleY(.34); }
  .e-alarm .pupil { transform: scale(.7); } .e-surprised .pupil { transform: scale(.85); }
  .e-happy .cheek, .e-joy .cheek, .e-proud .cheek { opacity: .85; }

  /* ---- always-on: breathing (measured on the kiosk; see the README) and the idle micro-moves ---- */
  /* The breath is STEPPED, ~10 fps (eight eased segments, 5 or 7 steps each): it is a sub-pixel motion, and on the
     kiosk any 60 Hz animation costs ~14 % CPU whatever its size (compositor + GPU process + DWM present per frame),
     while the identical frames between steps are not drawn at all. Measured 2026-10-11: breath + brain 16.7 % smooth
     → 7.4–9.3 % stepped; asleep 10.5 % → 4.8 %. */
  .breathe .squash { animation: breathe 4.2s steps(5, jump-end) infinite; }
  .breathe.e-asleep .squash { animation: breathe-deep 5.6s steps(7, jump-end) infinite; }
  :global(.demo-nobreathe) .breathe .squash { animation: none; }
  @keyframes breathe {
    0% { transform: scale(1.0000, 1.0000); }
    12.5% { transform: scale(1.0018, 0.9979); }
    25% { transform: scale(1.0060, 0.9930); }
    37.5% { transform: scale(1.0102, 0.9881); }
    50% { transform: scale(1.0120, 0.9860); }
    62.5% { transform: scale(1.0102, 0.9881); }
    75% { transform: scale(1.0060, 0.9930); }
    87.5% { transform: scale(1.0018, 0.9979); }
    100% { transform: scale(1.0000, 1.0000); }
  }
  @keyframes breathe-deep {
    0% { transform: scale(1.0000, 1.0000); }
    12.5% { transform: scale(1.0044, 0.9949); }
    25% { transform: scale(1.0150, 0.9825); }
    37.5% { transform: scale(1.0256, 0.9701); }
    50% { transform: scale(1.0300, 0.9650); }
    62.5% { transform: scale(1.0256, 0.9701); }
    75% { transform: scale(1.0150, 0.9825); }
    87.5% { transform: scale(1.0044, 0.9949); }
    100% { transform: scale(1.0000, 1.0000); }
  }
  .blink .lid { animation: blink .22s ease-in-out; }
  .blink2 .lid { animation: blink .21s ease-in-out 2; }
  @keyframes blink { 45%, 55% { transform: scaleY(1.02); } }
  .wob .yolk { animation: wobble .9s ease-out; }
  @keyframes wobble { 18% { transform: scale(1.1, .92); } 38% { transform: scale(.94, 1.06); } 58% { transform: scale(1.04, .97); } 78% { transform: scale(.99, 1.01); } }

  /* ---- actions ---- */
  .loop .p { animation-iteration-count: infinite !important; }   /* episodic: an import in progress (seconds) */
  .held .p { animation-fill-mode: forwards; }

  /* hop: anticipation → stretch → apex → land squash → settle; the egg and the handle follow through */
  .a-hop .rig { animation: hop-rig 1s both; }
  @keyframes hop-rig { 16% { transform: translateY(0); animation-timing-function: cubic-bezier(.2, .75, .4, 1); }
    46% { transform: translateY(-66px); animation-timing-function: cubic-bezier(.6, 0, .9, .55); } 72%, 100% { transform: translateY(0); } }
  .a-hop .squash { animation: hop-sq 1s both; }
  @keyframes hop-sq { 14% { transform: scale(1.14, .84); } 26% { transform: scale(.9, 1.14); } 42% { transform: scale(.97, 1.04); }
    62% { transform: scale(1.02, .98); } 72% { transform: scale(1.18, .8); } 81% { transform: scale(.94, 1.07); } 90% { transform: scale(1.03, .97); } }
  .a-hop .shadow { animation: hop-sh 1s both; }
  @keyframes hop-sh { 16% { transform: scale(1.06); } 46% { transform: scale(.55); opacity: .45; } 72% { transform: scale(1.1); opacity: 1; } }
  .a-hop .eggw { animation: hop-egg 1s both; }
  @keyframes hop-egg { 22% { transform: translateY(5px); } 44% { transform: translateY(-16px); } 66% { transform: translateY(-6px); }
    74% { transform: translateY(3px); } 84% { transform: translateY(-4px); } 92% { transform: translateY(0); } }
  .a-hop .yolk { animation: land-yolk 1s both; }
  @keyframes land-yolk { 72% { transform: scale(1); } 76% { transform: scale(1.2, .78); } 84% { transform: scale(.9, 1.12); } 92% { transform: scale(1.05, .95); } }
  .a-hop .arm.l { animation: hop-al 1s both; } .a-hop .arm.r { animation: hop-ar 1s both; }
  @keyframes hop-al { 16% { transform: rotate(40deg); } 36% { transform: rotate(150deg); } 60% { transform: rotate(138deg); } 76% { transform: rotate(48deg); } 88% { transform: rotate(64deg); } }
  @keyframes hop-ar { 16% { transform: rotate(-40deg); } 36% { transform: rotate(-150deg); } 60% { transform: rotate(-138deg); } 76% { transform: rotate(-48deg); } 88% { transform: rotate(-64deg); } }
  .a-hop .arm .fore { animation: straight-hop 1s both; }
  @keyframes straight-hop { 30%, 64% { transform: rotate(0deg); } }
  .a-hop .handle { animation: tail-land 1s both; }
  @keyframes tail-land { 24% { transform: rotate(6deg); } 46% { transform: rotate(-4deg); } 74% { transform: rotate(-12deg); } 84% { transform: rotate(7deg); } 93% { transform: rotate(-2deg); } }

  /* wave: the LEFT arm swings up (the handle is on the right) with an overshoot; forearm and glove wave with a lag */
  .a-wave .arm.l { animation: wave-al 1.8s both; }
  @keyframes wave-al { 14% { transform: rotate(140deg); animation-timing-function: ease-out; } 20% { transform: rotate(152deg); } 26%, 84% { transform: rotate(142deg); } }
  .a-wave .arm.l .fore { animation: wave-f 1.8s both; }
  @keyframes wave-f { 16% { transform: rotate(0deg); } 26% { transform: rotate(28deg); } 36% { transform: rotate(-26deg); } 46% { transform: rotate(26deg); } 56% { transform: rotate(-24deg); } 66% { transform: rotate(22deg); } 76% { transform: rotate(-16deg); } 86% { transform: rotate(0deg); } }
  .a-wave .arm.l .glove { animation: wave-g 1.8s both; }
  @keyframes wave-g { 18% { transform: rotate(0deg); } 30% { transform: rotate(22deg); } 40% { transform: rotate(-22deg); } 50% { transform: rotate(20deg); } 60% { transform: rotate(-20deg); } 70% { transform: rotate(16deg); } 80% { transform: rotate(-10deg); } 88% { transform: rotate(0deg); } }
  .a-wave .squash { animation: lean-r 1.8s both; }
  @keyframes lean-r { 14%, 84% { transform: rotate(3deg) scale(1.01, .99); } }
  .a-wave .handle { animation: wag 1.8s both; }
  @keyframes wag { 30% { transform: rotate(-6deg); } 45% { transform: rotate(5deg); } 60% { transform: rotate(-5deg); } 75% { transform: rotate(4deg); } 90% { transform: rotate(-1deg); } }

  /* hello: pops up from below, lands, waves */
  .a-hello .rig { animation: hello-rig 1.7s both; }
  @keyframes hello-rig { 0% { transform: translateY(160px); opacity: 0; } 12% { opacity: 1; } 26% { transform: translateY(-20px); animation-timing-function: ease-in; } 36% { transform: translateY(4px); } 44% { transform: translateY(0); } }
  .a-hello .squash { animation: hello-sq 1.7s both; }
  @keyframes hello-sq { 0% { transform: scale(.88, 1.14); } 26% { transform: scale(.95, 1.06); } 36% { transform: scale(1.12, .88); } 46% { transform: scale(.98, 1.02); } 52% { transform: scale(1, 1); } }
  .a-hello .arm.l { animation: hello-al 1.7s both; }
  @keyframes hello-al { 44% { transform: rotate(58deg); } 56% { transform: rotate(172deg); } 62%, 88% { transform: rotate(162deg); } }
  .a-hello .arm.l .fore { animation: hello-f 1.7s both; }
  @keyframes hello-f { 50% { transform: rotate(0deg); } 58% { transform: rotate(-26deg); } 66% { transform: rotate(26deg); } 74% { transform: rotate(-24deg); } 82% { transform: rotate(18deg); } 90% { transform: rotate(0deg); } }

  /* flip: the signature act — dip, toss, the egg turns over in the air, catch, splat, proud */
  .a-flip .squash { animation: flip-sq 2.4s both; }
  @keyframes flip-sq { 12% { transform: scale(1.1, .88); } 20% { transform: scale(.93, 1.09); } 27% { transform: scale(1.02, .98); } 34%, 66% { transform: scale(1, 1); }
    72% { transform: scale(1.12, .86); } 80% { transform: scale(.96, 1.05); } 88% { transform: scale(1.02, .98); } }
  .a-flip .rig { animation: flip-rig 2.4s both; }
  @keyframes flip-rig { 12% { transform: translateY(2px); } 20% { transform: translateY(-12px); } 30% { transform: translateY(0); } 72% { transform: translateY(3px); } 80% { transform: translateY(0); } }
  .a-flip .handle { animation: flip-h 2.4s both; }
  @keyframes flip-h { 12% { transform: rotate(10deg); } 20% { transform: rotate(-16deg); } 30% { transform: rotate(5deg); } 40% { transform: rotate(0deg); } 72% { transform: rotate(-9deg); } 82% { transform: rotate(5deg); } 92% { transform: rotate(0deg); } }
  .a-flip .eggw { animation: flip-egg 2.4s both; }
  @keyframes flip-egg { 12% { transform: translateY(4px) rotateX(0deg); } 20% { transform: translateY(-34px) rotateX(70deg); animation-timing-function: cubic-bezier(.2, .7, .4, 1); }
    44% { transform: translateY(-196px) rotateX(360deg) rotate(-8deg); animation-timing-function: cubic-bezier(.6, 0, .9, .5); }
    68% { transform: translateY(0) rotateX(720deg) rotate(0deg); } 73% { transform: translateY(6px) rotateX(720deg); } 81% { transform: translateY(-7px) rotateX(720deg); }
    89%, 100% { transform: translateY(0) rotateX(720deg); } }
  .a-flip .yolk { animation: flip-yolk 2.4s both; }
  @keyframes flip-yolk { 68% { transform: scale(1); } 72% { transform: scale(1.24, .74); } 80% { transform: scale(.88, 1.14); } 88% { transform: scale(1.06, .95); } 95% { transform: scale(1); } }
  .a-flip .pupil { animation: flip-look 2.4s both; }
  @keyframes flip-look { 18% { transform: translate(0, 0); } 34%, 50% { transform: translate(1px, -8px); } 64% { transform: translate(0, 1px); } 72% { transform: translate(0, 3px); } 86% { transform: translate(0, 0); } }
  .a-flip .brow { animation: flip-brow 2.4s both; }
  @keyframes flip-brow { 24% { transform: translateY(0); } 32%, 62% { transform: translateY(-7px); } 72% { transform: translateY(-2px); } 80%, 96% { transform: translateY(-5px); } }
  .a-flip .arm.l { animation: flip-al 2.4s both; } .a-flip .arm.r { animation: flip-ar 2.4s both; }
  @keyframes flip-al { 12% { transform: rotate(44deg); } 22% { transform: rotate(84deg); } 40% { transform: rotate(72deg); } 64% { transform: rotate(96deg); } 74% { transform: rotate(50deg); } 86% { transform: rotate(62deg); } }
  @keyframes flip-ar { 12% { transform: rotate(-44deg); } 22% { transform: rotate(-84deg); } 40% { transform: rotate(-72deg); } 64% { transform: rotate(-96deg); } 74% { transform: rotate(-50deg); } 86% { transform: rotate(-62deg); } }
  .a-flip .m-smile { animation: show-to-22 2.4s both; }
  .a-flip .m-o { animation: show-26-66 2.4s both; }
  .a-flip .m-grin { animation: show-70-100 2.4s both; }
  .a-flip .cheek { animation: show-70-100 2.4s both; }
  @keyframes show-to-22 { 0%, 21% { opacity: 1; } 24%, 100% { opacity: 0; } }
  @keyframes show-26-66 { 0%, 24% { opacity: 0; } 27%, 65% { opacity: 1; } 68%, 100% { opacity: 0; } }
  @keyframes show-70-100 { 0%, 68% { opacity: 0; } 71%, 100% { opacity: 1; } }
  .a-flip .spark { animation: flip-spark 2.4s both; }
  .a-flip .s2 { animation-delay: .08s; } .a-flip .s3 { animation-delay: .16s; } .a-flip .s4 { animation-delay: .05s; } .a-flip .s5 { animation-delay: .12s; }
  @keyframes flip-spark { 0%, 70% { opacity: 0; transform: scale(0) rotate(0deg); } 78% { opacity: 1; transform: scale(1.25) rotate(45deg); } 90% { opacity: 1; transform: scale(.9) rotate(75deg); } 100% { opacity: 0; transform: scale(0) rotate(100deg); } }

  /* stir: the right arm goes up and over (counter-clockwise, never through the floor), the glove on the rim, the spoon's
     bowl in the pan; small circles; focused face, a puff of steam. Angles solved for upper 30 / forearm 28. */
  .a-stir .arm.r { animation: stir-ar 2.6s both; }
  @keyframes stir-ar { 10% { transform: rotate(-210deg); } 22% { transform: rotate(-200deg); } 34% { transform: rotate(-218deg); } 46% { transform: rotate(-200deg); } 58% { transform: rotate(-218deg); } 70% { transform: rotate(-200deg); } 82% { transform: rotate(-210deg); } }
  .a-stir .arm.r .fore { animation: stir-f 2.6s both; }
  @keyframes stir-f { 10% { transform: rotate(-47deg); } 22% { transform: rotate(-38deg); } 34% { transform: rotate(-56deg); } 46% { transform: rotate(-38deg); } 58% { transform: rotate(-56deg); } 70% { transform: rotate(-38deg); } 82% { transform: rotate(-47deg); } }
  .a-stir .arm.r .glove { animation: stir-g 2.6s both; }
  @keyframes stir-g { 10%, 82% { transform: rotate(27deg); } }
  .a-stir .spoon { animation: stir-spoon 2.6s both; }
  @keyframes stir-spoon { 0%, 6% { opacity: 0; } 10%, 84% { opacity: 1; } 90%, 100% { opacity: 0; } }
  .a-stir .squash { animation: stir-sq 2.6s both; }
  @keyframes stir-sq { 22% { transform: rotate(1.5deg); } 34% { transform: rotate(-1deg); } 46% { transform: rotate(1.5deg); } 58% { transform: rotate(-1deg); } 70% { transform: rotate(1.5deg); } 82% { transform: rotate(0deg); } }
  .a-stir .pupil { animation: stir-look 2.6s both; }
  @keyframes stir-look { 12%, 80% { transform: translate(4px, -6px); } }
  .a-stir .puff { animation: puff 1.8s .5s both; }
  .a-stir .p2 { animation-delay: .9s; } .a-stir .p3 { animation-delay: 1.2s; }

  /* yawn: a big stretch, eyes shut, wide mouth, then a satisfied smack */
  .a-yawn .squash { animation: yawn-sq 2.6s both; }
  @keyframes yawn-sq { 16% { transform: scale(.95, 1.1); } 48% { transform: scale(.96, 1.09); } 62% { transform: scale(1.06, .94); } 74% { transform: scale(.99, 1.01); } }
  .a-yawn .arm.l { animation: yawn-al 2.6s both; } .a-yawn .arm.r { animation: yawn-ar 2.6s both; }
  @keyframes yawn-al { 16% { transform: rotate(158deg); } 50% { transform: rotate(166deg); } 66% { transform: rotate(52deg); } 76% { transform: rotate(62deg); } }
  @keyframes yawn-ar { 16% { transform: rotate(-158deg); } 50% { transform: rotate(-166deg); } 66% { transform: rotate(-52deg); } 76% { transform: rotate(-62deg); } }
  .a-yawn .arm .fore { animation: yawn-f 2.6s both; }
  @keyframes yawn-f { 16%, 50% { transform: rotate(0deg); } }
  .a-yawn .eye { animation: yawn-eye 2.6s both; } .a-yawn .shut { animation: yawn-shut 2.6s both; }
  @keyframes yawn-eye { 0%, 16% { opacity: 1; } 22%, 62% { opacity: 0; } 70%, 100% { opacity: 1; } }
  @keyframes yawn-shut { 0%, 16% { opacity: 0; } 22%, 62% { opacity: 1; } 70%, 100% { opacity: 0; } }
  .a-yawn .brow { animation: yawn-brow 2.6s both; }
  @keyframes yawn-brow { 18%, 56% { transform: translateY(-6px); } }
  .a-yawn .m-smile { animation: yawn-smile 2.6s both; }
  @keyframes yawn-smile { 0%, 10% { opacity: 1; } 14%, 88% { opacity: 0; } 94%, 100% { opacity: 1; } }
  .a-yawn .m-bigo { animation: show-16-58 2.6s both; }
  @keyframes show-16-58 { 0%, 14% { opacity: 0; } 18%, 56% { opacity: 1; } 60%, 100% { opacity: 0; } }
  .a-yawn .m-cat { animation: show-62-86 2.6s both; }
  @keyframes show-62-86 { 0%, 60% { opacity: 0; } 64%, 86% { opacity: 1; } 90%, 100% { opacity: 0; } }

  /* snore (asleep): a slow deep breath, Z Z Z drifting up */
  .a-snore .squash { animation: snore-sq 3.2s ease-in-out both; }
  @keyframes snore-sq { 45% { transform: scale(1.035, .955); } 90% { transform: scale(1, 1); } }
  .a-snore .zz { animation: zz 2.2s ease-out both; }
  .a-snore .z2 { animation-delay: .5s; } .a-snore .z3 { animation-delay: 1s; }
  @keyframes zz { 0% { opacity: 0; transform: translate(0, 6px) scale(.5); } 18% { opacity: 1; } 70% { opacity: 1; transform: translate(12px, -22px) scale(1.12); } 100% { opacity: 0; transform: translate(18px, -36px) scale(1.25); } }
  .a-snore .m-sleep { animation: snore-mouth 3.2s ease-in-out both; }
  @keyframes snore-mouth { 45% { transform: scale(1.35); } }

  /* alarm (a timer ended): jumps, shakes, flails, a "!" pops — loops while the card is up */
  .a-alarm .rig { animation: alarm-rig 1.2s both; }
  @keyframes alarm-rig { 10% { transform: translateY(-28px); animation-timing-function: ease-in; } 22% { transform: translateY(0); } 32% { transform: translateY(-18px); animation-timing-function: ease-in; } 44% { transform: translateY(0); } }
  .a-alarm .squash { animation: alarm-sq 1.2s both; }
  @keyframes alarm-sq { 6% { transform: scale(.9, 1.1); } 22% { transform: scale(1.1, .9); } 30% { transform: rotate(-6deg); } 40% { transform: rotate(6deg); }
    50% { transform: rotate(-5deg); } 60% { transform: rotate(5deg); } 70% { transform: rotate(-3deg); } 80% { transform: rotate(2deg); } }
  .a-alarm .arm.l { animation: alarm-al 1.2s both; } .a-alarm .arm.r { animation: alarm-ar 1.2s both; }
  .a-alarm .arm .glove { animation: alarm-glove 1.2s both; }
  @keyframes alarm-glove { 10%, 90% { transform: rotate(0deg); } }
  @keyframes alarm-al { 10% { transform: rotate(150deg); } 25% { transform: rotate(108deg); } 40% { transform: rotate(156deg); } 55% { transform: rotate(112deg); } 70% { transform: rotate(150deg); } 85% { transform: rotate(118deg); } }
  @keyframes alarm-ar { 10% { transform: rotate(-110deg); } 25% { transform: rotate(-154deg); } 40% { transform: rotate(-112deg); } 55% { transform: rotate(-156deg); } 70% { transform: rotate(-116deg); } 85% { transform: rotate(-150deg); } }
  .a-alarm .arm .fore { animation: alarm-f 1.2s both; }
  @keyframes alarm-f { 15% { transform: rotate(-30deg); } 30% { transform: rotate(30deg); } 45% { transform: rotate(-30deg); } 60% { transform: rotate(30deg); } 75% { transform: rotate(-20deg); } }
  .a-alarm .handle { animation: alarm-h 1.2s both; }
  @keyframes alarm-h { 10% { transform: rotate(-10deg); } 25% { transform: rotate(10deg); } 40% { transform: rotate(-8deg); } 55% { transform: rotate(8deg); } 70% { transform: rotate(-5deg); } }
  .a-alarm .bang { animation: bang 1.2s both; }
  @keyframes bang { 0% { opacity: 0; transform: scale(0) rotate(-20deg); } 12% { opacity: 1; transform: scale(1.25) rotate(8deg); } 22% { transform: scale(.95) rotate(-4deg); } 50% { opacity: 1; transform: scale(1.06) rotate(3deg); } 80%, 100% { opacity: 1; transform: scale(1) rotate(0deg); } }
  .a-alarm .eggw { animation: alarm-egg 1.2s both; }
  @keyframes alarm-egg { 14% { transform: translateY(-14px) rotate(-6deg); } 24% { transform: translateY(2px) rotate(3deg); } 36% { transform: translateY(-9px) rotate(4deg); } 46% { transform: translateY(0) rotate(0deg); } }

  /* giggle (a tap): happy squashes and wiggles, eyes ^ ^, blush, hearts */
  .a-giggle .squash { animation: giggle-sq .95s both; }
  @keyframes giggle-sq { 8% { transform: scale(1.08, .92); } 18% { transform: rotate(-5deg) scale(1.04, .96); } 30% { transform: rotate(5deg) scale(1.06, .94); } 42% { transform: rotate(-4deg) scale(1.03, .97); }
    54% { transform: rotate(4deg) scale(1.05, .95); } 66% { transform: rotate(-2deg); } 80% { transform: rotate(1deg); } }
  .a-giggle .arm.l { animation: giggle-al .95s both; } .a-giggle .arm.r { animation: giggle-ar .95s both; }
  @keyframes giggle-al { 15% { transform: rotate(72deg); } 30% { transform: rotate(50deg); } 45% { transform: rotate(70deg); } 60% { transform: rotate(52deg); } }
  @keyframes giggle-ar { 15% { transform: rotate(-72deg); } 30% { transform: rotate(-50deg); } 45% { transform: rotate(-70deg); } 60% { transform: rotate(-52deg); } }
  .a-giggle .heart { animation: float-up .95s ease-out both; }
  .a-giggle .h2 { animation-delay: .15s; }
  @keyframes float-up { 0% { opacity: 0; transform: translateY(8px) scale(.4); } 20% { opacity: 1; transform: translateY(0) scale(1.1); } 100% { opacity: 0; transform: translateY(-38px) scale(.9); } }
  .a-giggle .cheek { animation: blush .95s both; }
  @keyframes blush { 10%, 85% { opacity: 1; } }

  /* shrug (nothing here): upper arms out to the sides, forearms up, palms up, brows up — the pose holds */
  .a-shrug .arm.l { animation: shrug-al 1.4s both; } .a-shrug .arm.r { animation: shrug-ar 1.4s both; }
  @keyframes shrug-al { 30%, 100% { transform: rotate(86deg); } }
  @keyframes shrug-ar { 30%, 100% { transform: rotate(-86deg); } }
  .a-shrug .arm.l .fore { animation: shrug-fl 1.4s both; } .a-shrug .arm.r .fore { animation: shrug-fr 1.4s both; }
  @keyframes shrug-fl { 30%, 100% { transform: rotate(82deg); } }
  @keyframes shrug-fr { 30%, 100% { transform: rotate(-82deg); } }
  .a-shrug .arm .glove { animation: shrug-g 1.4s both; }
  @keyframes shrug-g { 30%, 100% { transform: rotate(0deg); } }
  .a-shrug .squash { animation: shrug-sq 1.4s both; }
  @keyframes shrug-sq { 18% { transform: scale(1.05, .95); } 30% { transform: scale(.98, 1.03); } 42%, 100% { transform: scale(1, 1) rotate(-2deg); } }
  .a-shrug .brow { animation: shrug-brow 1.4s both; }
  @keyframes shrug-brow { 30%, 100% { transform: translateY(-7px); } }
  .a-shrug .m-smile { animation: hide-from-20 1.4s both; }
  .a-shrug .m-flat { animation: show-from-24 1.4s both; }
  @keyframes hide-from-20 { 0%, 18% { opacity: 1; } 22%, 100% { opacity: 0; } }
  @keyframes show-from-24 { 0%, 22% { opacity: 0; } 26%, 100% { opacity: 1; } }

  /* think (busy): elbow down, forearm up, glove on the right cheek, eyes up-left, one brow raised, thought dots */
  .a-think .arm.r { animation: think-ar 2.2s both; }
  @keyframes think-ar { 16%, 88% { transform: rotate(10deg); } }
  .a-think .arm.r .fore { animation: think-f 2.2s both; }
  @keyframes think-f { 16%, 88% { transform: rotate(65deg); } }
  .a-think .arm.r .glove { animation: think-g 2.2s both; }
  @keyframes think-g { 16%, 88% { transform: rotate(105deg); } }
  .a-think .pupil { animation: think-look 2.2s both; }
  @keyframes think-look { 16%, 88% { transform: translate(-5px, -6px); } }
  .a-think .brow.r { animation: think-brow 2.2s both; }
  @keyframes think-brow { 16%, 88% { transform: translateY(-7px) rotate(-6deg); } }
  .a-think .squash { animation: think-sq 2.2s both; }
  @keyframes think-sq { 16%, 88% { transform: rotate(3deg); } }
  .a-think .dot { animation: dot-pop 2.2s both; }
  .a-think .d2 { animation-delay: .25s; } .a-think .d3 { animation-delay: .5s; }
  @keyframes dot-pop { 0%, 16% { opacity: 0; transform: scale(0); } 24% { opacity: 1; transform: scale(1.2); } 30%, 80% { opacity: 1; transform: scale(1); } 92%, 100% { opacity: 0; transform: scale(.6); } }

  /* worried (offline): a sweat drop slides down, a nervous tremble, eyes darting */
  .a-worried .sweat { animation: sweat 2.4s ease-in both; }
  @keyframes sweat { 0% { opacity: 0; transform: translateY(-6px) scale(.6); } 15% { opacity: 1; transform: translateY(0) scale(1); } 85% { opacity: 1; transform: translateY(20px); } 100% { opacity: 0; transform: translateY(24px); } }
  .a-worried .squash { animation: tremble 2.4s both; }
  @keyframes tremble { 10% { transform: rotate(-1.5deg); } 20% { transform: rotate(1.5deg); } 30% { transform: rotate(-1.5deg); } 40% { transform: rotate(1.2deg); } 50% { transform: rotate(-1deg); } 60% { transform: rotate(.8deg); } 70% { transform: rotate(0deg); } }
  .a-worried .pupil { animation: dart 2.4s both; }
  @keyframes dart { 15%, 30% { transform: translate(-5px, 1px); } 40%, 55% { transform: translate(5px, 1px); } 65%, 80% { transform: translate(-3px, 0); } }

  /* look around: left, right (one brow up), back — the body leans with the eyes */
  .a-look .pupil { animation: look 1.9s both; }
  @keyframes look { 12%, 40% { transform: translate(-6px, 0); } 52%, 80% { transform: translate(6px, -2px); } }
  .a-look .face { animation: look-face 1.9s both; }
  @keyframes look-face { 12%, 40% { transform: translateX(-4px); } 52%, 80% { transform: translateX(4px); } }
  .a-look .squash { animation: look-sq 1.9s both; }
  @keyframes look-sq { 12%, 40% { transform: rotate(-1.5deg); } 52%, 80% { transform: rotate(1.5deg); } }
  .a-look .brow.r { animation: look-brow 1.9s both; }
  @keyframes look-brow { 52%, 80% { transform: translateY(-5px); } }

  /* sizzle: the egg trembles, bubbles pop around it */
  .a-sizzle .egg { animation: sizzle-egg 1.4s both; }
  @keyframes sizzle-egg { 10% { transform: scale(1.03, .97); } 20% { transform: scale(.98, 1.02); } 30% { transform: scale(1.03, .97); } 40% { transform: scale(.98, 1.02); } 50% { transform: scale(1.02, .98); } 60% { transform: scale(1, 1); } }
  .a-sizzle .yolk { animation: wobble 1s .1s both; }
  .a-sizzle .bubble { animation: bubble .6s both; }
  .a-sizzle .b2 { animation-delay: .2s; } .a-sizzle .b3 { animation-delay: .45s; } .a-sizzle .b4 { animation-delay: .7s; }
  @keyframes bubble { 0% { opacity: 0; transform: scale(0); } 30% { opacity: 1; transform: scale(1.15); } 60% { opacity: 1; transform: scale(1); } 100% { opacity: 0; transform: scale(1.7); } }
  .a-sizzle .p2 { animation: puff 1.4s .3s both; }

  /* steam: three puffs rise and spread; the pan enjoys the smell (eyes closed) */
  .a-steam .puff { animation: puff 1.8s both; }
  .a-steam .p2 { animation-delay: .4s; } .a-steam .p3 { animation-delay: .8s; }
  @keyframes puff { 0% { opacity: 0; transform: translateY(10px) scale(.5); } 20% { opacity: .95; transform: translateY(0) scale(.85); } 100% { opacity: 0; transform: translateY(-48px) scale(1.25); } }
  .a-steam .eye { animation: steam-eye 2.6s both; } .a-steam .shut { animation: steam-shut 2.6s both; }
  @keyframes steam-eye { 0%, 24% { opacity: 1; } 30%, 80% { opacity: 0; } 86%, 100% { opacity: 1; } }
  @keyframes steam-shut { 0%, 24% { opacity: 0; } 30%, 80% { opacity: 1; } 86%, 100% { opacity: 0; } }
  .a-steam .m-smile { animation: hide-28-82 2.6s both; }
  .a-steam .m-cat { animation: show-28-82 2.6s both; }
  @keyframes hide-28-82 { 0%, 26% { opacity: 1; } 30%, 80% { opacity: 0; } 84%, 100% { opacity: 1; } }
  @keyframes show-28-82 { 0%, 26% { opacity: 0; } 30%, 80% { opacity: 1; } 84%, 100% { opacity: 0; } }

  /* dance: four beats, bounce and lean, arms alternate, music notes */
  .a-dance .rig { animation: dance-rig .7s 4 both; }
  @keyframes dance-rig { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-16px); } }
  .a-dance .squash { animation: dance-sq 1.4s 2 both; }
  @keyframes dance-sq { 0%, 100% { transform: scale(1.06, .94); } 25% { transform: rotate(-6deg) scale(.97, 1.04); } 50% { transform: scale(1.06, .94); } 75% { transform: rotate(6deg) scale(.97, 1.04); } }
  .a-dance .arm.l { animation: dance-al 1.4s 2 both; } .a-dance .arm.r { animation: dance-ar 1.4s 2 both; }
  @keyframes dance-al { 25% { transform: rotate(154deg); } 75% { transform: rotate(60deg); } }
  @keyframes dance-ar { 25% { transform: rotate(-60deg); } 75% { transform: rotate(-154deg); } }
  .a-dance .arm .fore { animation: straight-dance 2.8s both; }
  @keyframes straight-dance { 8%, 92% { transform: rotate(0deg); } }
  .a-dance .handle { animation: wag 1.4s 2 both; }
  .a-dance .note { animation: float-up 1.4s ease-out both; }
  .a-dance .n2 { animation-delay: .7s; }
  .a-dance .eggw { animation: dance-egg .7s 4 both; }
  @keyframes dance-egg { 30% { transform: translateY(3px); } 65% { transform: translateY(-5px); } }

  /* celebrate (something saved): two hops, arms up, sparkles, ^ ^ */
  .a-celebrate .rig { animation: cel-rig 1.8s both; }
  @keyframes cel-rig { 10% { transform: translateY(0); animation-timing-function: ease-out; } 26% { transform: translateY(-50px); animation-timing-function: ease-in; } 40% { transform: translateY(0); animation-timing-function: ease-out; }
    55% { transform: translateY(-34px); animation-timing-function: ease-in; } 68%, 100% { transform: translateY(0); } }
  .a-celebrate .squash { animation: cel-sq 1.8s both; }
  @keyframes cel-sq { 8% { transform: scale(1.1, .9); } 14% { transform: scale(.92, 1.1); } 40% { transform: scale(1.14, .86); } 46% { transform: scale(.94, 1.08); } 68% { transform: scale(1.12, .88); } 78% { transform: scale(.98, 1.02); } }
  .a-celebrate .arm.l { animation: cel-al 1.8s both; } .a-celebrate .arm.r { animation: cel-ar 1.8s both; }
  @keyframes cel-al { 12%, 80% { transform: rotate(152deg); } 26% { transform: rotate(166deg); } 55% { transform: rotate(162deg); } }
  @keyframes cel-ar { 12%, 80% { transform: rotate(-152deg); } 26% { transform: rotate(-166deg); } 55% { transform: rotate(-162deg); } }
  .a-celebrate .arm .fore { animation: straight-cel 1.8s both; }
  @keyframes straight-cel { 12%, 80% { transform: rotate(0deg); } }
  .a-celebrate .spark { animation: cel-spark 1.8s both; }
  .a-celebrate .s2 { animation-delay: .1s; } .a-celebrate .s3 { animation-delay: .2s; } .a-celebrate .s4 { animation-delay: .05s; } .a-celebrate .s5 { animation-delay: .15s; }
  @keyframes cel-spark { 0%, 16% { opacity: 0; transform: scale(0) rotate(0deg); } 28% { opacity: 1; transform: scale(1.25) rotate(50deg); } 70% { opacity: 1; transform: scale(.9) rotate(110deg); } 100% { opacity: 0; transform: scale(0) rotate(140deg); } }
  .a-celebrate .yolk { animation: land-yolk 1.8s both; }
  .a-celebrate .handle { animation: tail-land 1.8s both; }

  /* nod (a toggle registered) */
  .a-nod .squash { animation: nod .65s both; }
  @keyframes nod { 40% { transform: translateY(5px) scale(1.05, .93); } 70% { transform: scale(.98, 1.02); } }
  .a-nod .brow { animation: nod-brow .65s both; }
  @keyframes nod-brow { 40% { transform: translateY(2px); } }

  /* talk (the speech bubble): the mouth opens and closes, a light bob */
  .a-talk .m-o { animation: talk .32s steps(1) 5 both; }
  .a-talk .m-cat { animation: talk-inv .32s steps(1) 5 both; }
  @keyframes talk { 0% { opacity: 1; } 50% { opacity: 0; } }
  @keyframes talk-inv { 0% { opacity: 0; } 50% { opacity: 1; } }
  .a-talk .squash { animation: bob .32s 5 both; }
  @keyframes bob { 50% { transform: scale(1.015, .985) translateY(1px); } }
  .a-talk .brow { animation: talk-brow .8s 2 both; }
  @keyframes talk-brow { 30% { transform: translateY(-4px); } 60% { transform: translateY(-1px); } }

  /* the tap area over the body only */
  .hit { position: absolute; left: 24px; top: 52px; width: 256px; height: 176px; border: 0; background: none; padding: 0;
         pointer-events: auto; border-radius: 40%; cursor: pointer; -webkit-tap-highlight-color: transparent; }
</style>
