# Animated report style

The default look for diagrams in a report: inline SVG that moves a little, with small playful characters, step
controls, and hover inspectors. Read this when the report has a mechanism, a timeline, a flow, or a chart to show
(Step 5 of the core). The report's profile still sets sections, titles, and file name, and the core's hard rules
still apply. This file only says how the visuals look and move.

The page must be correct, complete, and readable with no motion at all: printed, with reduced motion, and with
scripts off. Animation adds orientation. It never holds content back, and it never invents data.

## Contents

1. Report rules that outrank this file
2. Tokens and dark mode
3. Blob characters
4. Animated diagram anatomy
5. Stories, inspectors, simulators
6. Micro-interactions
7. Motion rules
8. Layout gotchas
9. Verification

## 1. Report rules that outrank this file

- **Self-contained single file.** Inline CSS and a small inline script. No external fonts, scripts, images, or libraries.
- **Escape everything from telemetry.** Inspector text, tooltips, step narration, and table cells that carry queries,
  log lines, or tag values are written with `textContent` (or escaped at generation time). Never `innerHTML` on them.
  Authored labels the skill itself wrote may sit in `data-info`, but no telemetry may.
- **No invented data.** Moving packets show a mechanism and are labelled "illustrative" in the caption unless each one
  is a retrieved event. A chart animation may only reveal retrieved points: draw discrete points for sparse samples,
  leave gaps as gaps, never smooth, interpolate, or ease a value past what was measured. A count-up ends on the real
  value and the real value is in the markup.
- **Status is never colour alone.** Every status carries an icon and a text label.
- **Profile limits win.** If the profile restricts script (the postmortem profile allows only its expand-all toggle and
  rail highlight), use CSS-only motion there: crawling dashed edges, pulses, hover wiggles. Skip stepper controls,
  scroll stories, and simulators for that profile, and keep the static diagram complete.
- **Keep the producer's structure.** Evidence IDs, hypothesis order, and tree nesting stay exactly as given.
- **Print.** `@media print` shows every step, hides controls, and keeps the dark diagram panels with
  `print-color-adjust: exact`; a flat light fallback is acceptable.

## 2. Tokens and dark mode

Page chrome uses tokens on `:root` with a dark variant, and `data-theme="dark"` on `<html>` forces dark:

```css
:root { color-scheme: light dark; --bg:#f7f5f1; --surface:#fff; --ink:#1f2933; --muted:#5b6770; --line:#d8d3ca; --accent:#c4561a; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#14191d; --surface:#1b2227; --ink:#e4ebee; --muted:#9aa9b2; --line:#2e3a41; --accent:#f08a45; } }
:root[data-theme="dark"] { --bg:#14191d; --surface:#1b2227; --ink:#e4ebee; --muted:#9aa9b2; --line:#2e3a41; --accent:#f08a45; }
body { background: var(--bg); color: var(--ink); }
```

(A profile's own palette replaces these values; keep the token names and the dark variants.)

Diagram panels stay dark in both themes so one fixed palette works. Check it against the panel colour:

```css
.rp { --rp-panel:#1c2a32; --rp-box:#24363f; --rp-line:#4c6671; --rp-ink:#eef4f6; --rp-mut:#c4d3da; --rp-lab:#9db7c2;
  --rp-bl:#2a9fd0; --rp-bl-t:#7fd0f2;  /* automatic / healthy flow      */
  --rp-or:#f29a52; --rp-or-t:#f5ab70;  /* a person acts / attention      */
  --rp-vi:#9a6ce6; --rp-vi-t:#c9adff;  /* contributing / secondary       */
  --rp-ti:#b8860b; --rp-ti-t:#f2c75c;  /* timers, waiting, planned       */
  --rp-ok:#2fa865; --rp-ok-t:#6ee7a0;  /* validated, done                */
  --rp-bad:#e5484d; --rp-bad-t:#ff8a8d;/* failure, impact                */
  --spd:1; }
```

- Fills and strokes use the base colour; text and arrowheads on the panel use the `-t` tint.
- One meaning per colour across the report, a legend under each diagram, and a label on every node.
- Text in SVG: 11px mono for labels, 13px mono for node titles, 13 to 14px sans for body. Add a `.halo`
  (`paint-order: stroke`, panel-coloured stroke) to text that crosses a line.

## 3. Blob characters

One happy and one sad symbol, drawn on `currentColor`, defined once in a hidden SVG with a page prefix:

```html
<svg class="rp-defs" aria-hidden="true" focusable="false" style="position:absolute;width:0;height:0"><defs>
  <symbol id="rp-blob" viewBox="-13 -13 26 26"><path d="M-11 3C-11-6-6-11 0-11S11-6 11 3C11 9 6 11 0 11S-11 9-11 3Z"
    fill="currentColor" stroke="#0f1a1f" stroke-width="1.5"/>
    <ellipse cx="-5" cy="-6" rx="3" ry="1.6" fill="#fff" opacity=".4"/>
    <circle cx="-4" cy="0" r="2.2" fill="#0f1a1f"/><circle cx="4" cy="0" r="2.2" fill="#0f1a1f"/>
    <circle cx="-3.3" cy="-.8" r=".7" fill="#fff"/><circle cx="4.7" cy="-.8" r=".7" fill="#fff"/>
    <path d="M-4 4.5Q0 7.5 4 4.5" fill="none" stroke="#0f1a1f" stroke-width="1.6" stroke-linecap="round"/></symbol>
  <symbol id="rp-blob-sad" viewBox="-13 -13 26 26"> same body, two brows, round eyes, a frown </symbol>
</defs></svg>
```

Colour with a class (`.c-bl { color: var(--rp-bl); }`). A blob is a request, task, message, or person; the sad blob is
failed, stuck, or dropped. Never make a blob carry meaning alone: name what it is in the legend.

**Viewbox rule.** The symbol is centred on the origin. An SVG that shows a `<use>` of a `viewBox="-13 -13 26 26"`
symbol as its whole content must itself have `viewBox="0 0 26 26"`. Otherwise the blob is clipped to a quarter:

```html
<svg viewBox="0 0 26 26" width="24" height="24" aria-hidden="true"><use href="#rp-blob"/></svg>   <!-- right -->
<!-- inside a larger diagram, give the use an explicit box: <use href="#rp-blob" x="-9" y="-9" width="18" height="18"/> -->
```

## 4. Animated diagram anatomy

Inline SVG in a `<figure>` with a dark panel, a caption, and controls. Ids carry a page prefix and a figure prefix
so two diagrams never share an id:

```html
<figure class="rp-fig" id="rp-flow" data-steps="5" data-dur="2400">
  <div class="rp-panel"><svg viewBox="0 0 480 300" role="group" aria-labelledby="rp-f-t rp-f-d">
    <title id="rp-f-t">Short name of the flow</title>
    <desc id="rp-f-d">One full sentence per hop, so a screen reader gets the whole mechanism.</desc>
    <path id="rp-f-e1" class="edge on1" d="M124 116V168" marker-end="url(#rp-ar)"/>
    <g class="rp-node on1" tabindex="0" role="button" aria-label="Gateway" data-info="Authored one-line explanation."> ... </g>
    <g class="tk c-bl" data-path="rp-f-e1" data-dur="1600" data-off=".5" transform="translate(-40 -40)">
      <use href="#rp-blob" x="-9" y="-9" width="18" height="18"/></g>
  </svg></div>
  <figcaption>What to look at, and whether packets are illustrative.</figcaption>
  <div class="rp-ctrl" role="group" aria-label="Controls for this diagram"> play/pause, prev, next, replay, speed </div>
</figure>
```

- **Edges** are dashed paths that crawl: `stroke-dasharray: 7 6; animation: rp-dash 1.1s linear infinite;` with
  `@keyframes rp-dash { to { stroke-dashoffset: -26 } }`. Brightness follows `--hot`:
  `stroke-opacity: calc(.45 + .55 * var(--hot, 0))`.
- **Travelling packets** are `.tk` groups holding a blob. One script samples each referenced path into about 80 points
  (`getTotalLength`, `getPointAtLength`) and sets `transform="translate(x y)"` each frame.
- **Steps** are cumulative classes `s1..sN` plus `data-now` on the figure. Elements with `atN` appear from step N,
  `onN` are lit while step N is current:

```css
.rp .rp-anim:not(.s3) .at3 { opacity: var(--ghost, 0); }   /* hidden until step 3, only while stepping */
.rp [data-now="3"] .on3 { --hot: 1; }
.rp .rp-fig:not(.rp-anim) { --hot: 1; }                    /* no script, print, reduced motion: all lit, none hidden */
```

- **Narration** is an `<ol>` of `<button data-go="N">` items next to the SVG: current is `is-now`, earlier ones
  `is-done` (check mark), a counter reads "Step 3 of 5". The narration states every step in words, so it also works as
  the static explanation.
- **Controls**, in order: Pause/Play, previous, next (icon buttons with `aria-label`), Replay, Speed 1x / 2x / half
  (sets `--spd` on the figure; every duration divides by it). Native `<button type="button">`, visible focus ring,
  hidden with no script and with reduced motion.
- **Timelines** reveal left to right with a clipping rect whose width follows progress, markers for events (numbered,
  focusable, each with a tooltip and a matching list entry), and a head that fades at the end.
- **Charts** keep their axes, values, and a data table. The animation only reveals what is there: points pop in,
  paired bars grow with `scaleY`, nothing between samples is drawn.

## 5. Stories, inspectors, simulators

**Sticky story (use for long mechanisms).** A tall wrapper holds a sticky stage; scroll position picks the step:

```css
.rp.rp-js:not(.rp-still) .rp-scrub { height: 230vh; }
.rp.rp-js:not(.rp-still) .rp-sticky { position: sticky; top: 14px; }
@media (max-width: 899px) { .rp.rp-js:not(.rp-still) .rp-scrub .rp-narr li:not(.is-now) {
  position:absolute; width:1px; height:1px; overflow:hidden; visibility:hidden; } }  /* not display:none: counters keep counting */
```

Progress is `clamp((stickyTop - wrap.top) / (wrap.height - sticky.height), 0, 1)` in one rAF-throttled passive scroll
handler. Without script, reduced motion, or print the wrapper has no extra height and all steps show.

**Hover and focus inspector.** Nodes are `tabindex="0" role="button"` with `aria-label` and `data-info`. On
`mouseenter`, `focus`, and Enter or Space, mark the node `is-pick` and write its label and info into one box under
the figure with `textContent`. Hover wiggles the node and glows its outline; `svg:has(.is-pick) .rp-node:not(.is-pick)`
dims the rest. Every fact in an inspector is also in the narration or a table, never only on hover.

**Simulators (use only when the reader can change a real input).** Sliders and preset buttons feed one `render()`:

```js
[slider, toggle].forEach(function (i) { i.addEventListener('input', function () { render(); }); });
presets.forEach(function (b) { b.addEventListener('click', function () { applyPreset(b); }); });
```

Show a tabular-number readout and a verdict box that changes border and text. Each control has a `<label>` and an
`<output>`. A simulator models only relationships the findings support; its default state equals the measured case.

## 6. Micro-interactions

All wrapped in `safe(name, fn)` (try, catch, `console.warn`) so one failure cannot stop the others.

- **Staggered entrances:** the container gets `rp-rvp`, children get `--i` (capped at 10), an IntersectionObserver adds
  `is-in`. Hidden state is scoped to `.rp-js:not(.rp-still)`, so no-script and reduced motion show everything.

```css
.rp.rp-js:not(.rp-still) .rp-rvp > * { opacity:0; transform:translateY(16px); transition: opacity .5s, transform .6s cubic-bezier(.2,1.3,.4,1); transition-delay: calc(var(--i,0) * 70ms); }
.rp.rp-js:not(.rp-still) .rp-rvp.is-in > * { opacity:1; transform:none; }
```

- **Count-ups:** the final value sits in the markup for screen readers, and an `aria-hidden` twin animates:

```html
<b><span class="rp-sr">13,686</span><span data-count="13686" aria-hidden="true">13,686</span></b>
```

  The script sets the twin to 0 on load and rolls to the end at 50% visible with an ease-out cubic. With reduced motion
  it does nothing. Only roll numbers that are retrieved values.
- **Animated divider:** a dashed rule with a blob running along it (`translateX(calc(100cqw - 24px))`,
  `container-type: inline-size` on the rule); paused until in view.
- **Reading progress:** fixed 4px bar, `transform: scaleX(p)`, `transform-origin: 0 50%`, `pointer-events: none`.
- **Copy-button feedback** on code blocks: a 600 ms pop and green ring after click, skipped for reduced motion.
- **Pause all motion:** a button near the top toggles `rp-allpaused` on the root, flips to "Resume all motion", sets
  `aria-pressed`, and the frame loop skips. Hidden with no script and with reduced motion.

## 7. Motion rules

- **Animate only `transform` and `opacity`.** Bars grow with `scaleX/scaleY` and a `transform-origin`. The one allowed
  extra is `stroke-dashoffset` on SVG dashes. Never animate width, height, top, left, blur, or box-shadow in a loop.
  On SVG shapes set `transform-box: fill-box; transform-origin: center`.
- **requestAnimationFrame with a clamped dt.** The rAF timestamp can be earlier than the `performance.now()` taken
  when the loop started, giving a negative dt and a TypeError later. Clamp it and run one loop for the page:

```js
function kick() { if (!raf && !still) { last = performance.now(); raf = requestAnimationFrame(frame); } }
function frame(now) { raf = 0; var dt = Math.max(0, Math.min(64, now - last)); last = now; /* work with dt */ if (anyRunning) raf = requestAnimationFrame(frame); }
```

- **Pause what is off screen.** An IntersectionObserver per figure (threshold about .05) toggles a paused class that
  sets `animation-play-state: paused !important` on the children, and the frame loop skips that figure's work.
- **Reduced motion and no script show the static, complete, readable end state:**

```js
var still = matchMedia('(prefers-reduced-motion: reduce)').matches;
root.classList.add('rp-js'); if (still) root.classList.add('rp-still');
```

```css
.rp:not(.rp-js) .tk, .rp.rp-still .tk, .rp:not(.rp-js) .rp-ctrl { display: none; }
@media (prefers-reduced-motion: reduce), print { .rp *, .rp *::before, .rp *::after { animation: none !important; transition: none !important; } }
```

  Every step-hidden element is visible without `rp-anim`. Every counter shows its final value. Moving blobs are replaced
  by resting blobs or by the finished edge. Keep loops calm: nothing flashes more than 3 times a second.

## 8. Layout gotchas

- **Inline pills in headings use `display: inline-block`,** not `inline-flex`. An empty flex child (a status dot) puts the
  pill on the dot's bottom edge instead of the text baseline. Add `vertical-align: baseline; line-height: 1.1`.
- **Child selectors for nested text:** `.rp-stat > span`, not `.rp-stat span`. The descendant form also matched the
  count-up's inner span and shrank the big numbers.
- **Check for label collisions and clipping** in every SVG at desktop and phone width: long labels over edges, text past
  the viewBox, a sticky stage taller than the viewport (`max-height: 76vh`, 54vh on phones), a moving head sitting on
  the final labels.
- Put wide tables, code, and diagrams in their own `overflow-x: auto` containers so the page never scrolls sideways.
  Long queries and IDs wrap with `overflow-wrap: anywhere`.
- Do not hide steps with `display: none` if a counter reads them; use the 1px visually-hidden pattern.

## 9. Verification

Do these after the core's own checks.

1. **Screenshots** at desktop width (about 1440) and 390px, in light and dark, plus one reduced-motion pass. Look at
   every diagram at full size, not only the top of the page.
2. **Force reduced motion in headless shots** (for Chrome, `--force-prefers-reduced-motion`). Without it a headless shot
   freezes mid-animation with half-hidden content. Judge the saved page by this shot: it is the static end state.
3. **Iframe harness when the browser window will not resize:** a scratch HTML page with iframes at 390 and 1440 wide
   pointing at the report. Keep it outside the report folder.
4. **Console and overflow check:** no errors or warnings logged, and
   `document.documentElement.scrollWidth === document.documentElement.clientWidth` at 390px.
5. Click each control once (step, play, speed, replay, pause-all, any slider). Tab to the nodes and confirm a focus ring.
6. Print preview or `emulateMedia print`: every step visible, no controls, nothing cut off.
7. With script disabled the report reads in full, with no blank gaps and no dead buttons.
