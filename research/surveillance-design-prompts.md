# Surveillance Lab: four animation prompts

These four prompts describe docs/surveillance.html. They follow the long, exact style of motionsites.ai prompts.
They are original: they use the site's own tokens and the project's real data, and copy no other site.
All data comes from `docs/data/surveillance.js` (written by `build_surveillance.py`), `docs/data/breakeven.js`
and the result files. No number on the page is invented.

---

## PROMPT 1: Hero, "Two traders. One footprint."

Build the hero for a research page titled "Surveillance Lab" on the existing "Detecting the Unseen" site. Use
plain HTML, CSS and vanilla JavaScript (no framework). Use the site's tokens from assets/site.css: --paper, --paper-2,
--ink, --ink-2, --ink-3, --line, --mark (magenta, reserved for the manipulator), --bid, --ask, --font-display
(Archivo, variable width 62-125, weight 100-900), --font-text (STIX Two Text), --font-mono (JetBrains Mono),
--ease-out cubic-bezier(0.23, 1, 0.32, 1). The page supports light and dark through those tokens. Never hard-code colours.

LAYOUT
Section .sv-hero: min-height 100svh, display grid, align-content end, padding-block 120px 56px, padding-inline var(--gutter),
position relative, overflow clip, isolation isolate. Behind everything, a full-bleed <canvas class="sv-hero__book">,
position absolute, inset 0, z-index -1, aria-hidden.
Content column: max-width 1120px, margin-inline auto, width 100%.

1. Eyebrow: "SURVEILLANCE LAB · SIMULATED MARKET". font-mono, 11px, letter-spacing 0.16em, uppercase, color --ink-3. A 6px
   magenta dot before it (border-radius 50%) breathes: opacity 0.35 to 1 over 2.4s ease-in-out, infinite.
2. Headline h1 on two lines: "Two traders." and "One footprint.". font-display, font-weight 760, font-stretch 112%,
   line-height 0.92, letter-spacing -0.035em, font-size clamp(3.2rem, 11vw, 9.5rem). Line 1 color --ink. Line 2 color
   --mark. Each line sits in a mask (display block, overflow clip, padding-bottom 0.08em so descenders are not cut).
   Line 2 is split into one span per letter (spaces kept as &nbsp; spans) with aria-hidden. The real text goes in a
   visually hidden span for screen readers.
3. Subhead, max-width 34rem, font-text, font-size clamp(1.05rem, 1.6vw, 1.3rem), line-height 1.5, color --ink-2,
   margin-top 28px: "One trader placed an order to mislead. The other changed their mind. A detector built from the law
   sees exactly the same thing in both. Below, the simulator replays them side by side."
4. Action row, margin-top 32px, gap 12px, flex-wrap: a primary link "Watch the replay" (#replay) and a ghost link
   "Why it matters for Economics" (#economics). Use the site's existing .btn and .btn--ghost classes. There are no
   gradients and no glow.
5. Stat strip, margin-top 56px: three columns separated by 1px --line hairlines (border-left on items 2 and 3, padding-left
   24px). Each item has a number (font-display 600, font-size clamp(2rem, 4vw, 3rem), tabular-nums) and a 13px font-mono label
   under it in --ink-3:
     "93%"  "of 16× spoofs flagged"
     "92%"  "of honest changes of mind flagged"   (this number is magenta)
     "0%"   "of genuine large orders flagged"
   Under the strip, a 12px caption in --ink-3: "Law-informed detector, calm simulated market, 16× orders. Source:
   results/teaching.md." The numbers are computed in JS from the score arrays in SURVEILLANCE.scores, never typed in by hand.
6. Scroll cue, bottom centre: a 1px x 48px track (background --line) with an --ink-2 fill. The fill grows from scaleY 0 to 1
   (transform-origin top), then shrinks from the bottom (transform-origin bottom). The loop takes 2.2s, ease-in-out.

BACKGROUND CANVAS (the order book, breathing)
Draw the real spoof replay (SURVEILLANCE.spoof.frames), looping at 5 steps per second, as a soft, calm order-book
silhouette. The canvas runs at devicePixelRatio and resizes with a ResizeObserver. Use 17 rows (SURVEILLANCE.prices),
evenly spaced over 70% of the canvas height and vertically centred. A central vertical axis sits at 62% of the width on
desktop and 50% on mobile. Bids draw to the left of it and asks to the right. Bar length = qty / 60 × 34% of the width.
Bar height is 38% of the row pitch, with 3px rounded ends. Bids use --bid at 16% alpha and asks use --ask at 16% alpha.
Any part of a row that is wall (rows[i][2]) uses --mark at 55% alpha. Between frames, interpolate every bar's length with
an exponential follow: value += (target - value) × (1 - exp(-dt × 9)), so nothing jumps. Each wall bar has a 1px magenta
outline at 30% alpha. At the end of the loop, hold 1.2s on an empty-wall frame, then restart.
Paint a radial vignette over the canvas from transparent at the centre to --paper at the edges (CSS mask-image on the canvas
element), so the book fades into the page.
Read the token values with getComputedStyle once, and again when the theme changes (listen for the theme toggle click and the
prefers-color-scheme change).

ENTRANCE CHOREOGRAPHY (on DOMContentLoaded, after fonts are ready: document.fonts.ready)
- Eyebrow: from opacity 0 and translateY(8px) to rest. 600ms, --ease-out, delay 0ms.
- Headline line 1: from translateY(105%) inside its mask to 0. 900ms, --ease-out, delay 120ms.
- Headline line 2 letters: each from translateY(110%) and rotate(4deg) to 0, with a 34ms stagger. 820ms, --ease-out,
  first letter at 260ms.
- Subhead: opacity 0 and translateY(12px), then rest. 700ms, delay 680ms.
- Buttons: same motion, delays 800ms and 870ms.
- Stat strip: items fade up with delays 1000, 1080 and 1160ms. Each number counts from 0 to its value over 1400ms with
  ease-out-expo (1 - 2^(-10t)), starting when its item begins to appear.
- Canvas: opacity 0 to 1 over 1600ms, delay 200ms.
Use the Web Animations API (element.animate) with fill 'both'. Do not use any library.

SCROLL BEHAVIOUR
Use a single passive scroll listener with requestAnimationFrame batching. Let p = clamp(scrollY / heroHeight, 0, 1).
- Canvas: translateY(p × 35%) and opacity 1 - p × 1.25.
- Headline block: scale(1 - p × 0.04) and opacity 1 - p × 1.4, with transform-origin left bottom.
- Scroll cue: opacity 1 - p × 4.

REDUCED MOTION
Under prefers-reduced-motion: reduce, skip all entrance animations (show the final state) and draw the canvas as one static
frame (the frame where the wall is largest). Show the numbers at their final values. There is no scroll parallax.

---

## PROMPT 2: The twin replay, scroll-scrubbed

Build section #replay: "Watch them side by side". Scrolling the page plays two real simulator episodes in lock-step.
Both come from the SAME random seed (SURVEILLANCE.seed). The left one is a spoof: a 48-lot buy wall placed behind the
best bid, a small 3-lot sell at the best ask, and the wall cancelled once the sell fills. The right one is an honest
trader who places the same 48-lot buy order, changes their mind, cancels it and sells 3 lots.

STRUCTURE
<section id="replay" class="sv-replay"> has height 460vh on desktop and 400vh on mobile. It contains
<div class="sv-replay__stage">, which is position sticky, top 0, height 100svh, display grid, grid-template-rows auto 1fr auto,
and padding 88px var(--gutter) 28px (88px clears the fixed top bar).
Row 1, the header: an h2 "Watch them side by side" (font-display 700, clamp(1.8rem, 3.6vw, 2.8rem), letter-spacing -0.02em)
and, to its right, a live caption region (aria-live="polite", font-text 1.05rem, --ink-2, max-width 30rem, min-height 3.2em).
Row 2, the twins: a two-column grid, gap clamp(16px, 3vw, 40px). Each column is a card .sv-twin with a 1px --line border,
a radius of 14px, background --paper-2 and padding 18px 18px 14px. Below 760px, show only one card at a time. A segmented
control above (two outlined buttons, "Spoofer" | "Changed mind", aria-pressed) chooses which card is shown. Both cards
keep scrubbing.
Row 3, the timeline: a 1px --line track spanning the width, a 9px --ink playhead dot, and event pins. Pins for the spoof
are magenta and sit above the track. Pins for the honest trader are --ink-2 and sit below it. Each pin is a 1px x 10px tick
with a 10px mono label: "order placed", "sell fills", "cancelled", "changed mind: cancel + sell". To the left, a mono step
counter "step 1031 / t+0" in tabular-nums. To the right, a Play/Pause button (outlined, 32px tall). Play animates the
scroll position so the replay runs at 6 steps per second, and it stops if the user scrolls. Left and right arrow keys step one
frame when the section has focus.

CARD CONTENTS (each twin)
- Top line: a name in font-display 600 1rem ("The spoofer" / "The trader who changed their mind"), and on the right a mono
  chip ("one account"), 11px, 1px border --line, radius 999px, padding 2px 8px.
- The ladder: 17 rows, one per price in SURVEILLANCE.prices (highest at the top). Each row is a 3-column grid:
  [bid bar area | price | ask bar area], grid-template-columns 1fr 56px 1fr, height clamp(14px, 2.2vh, 22px), gap 2px.
  The price is font-mono, 11px, centred, --ink-3. The best bid and best ask rows put the price in --ink at weight 500, and the
  row has a 1px --line rule underneath.
  The bid bar grows from the right edge of its cell leftwards, and the ask bar from the left edge rightwards.
  Width = min(qty / 60, 1) × 100% of the cell. Animate the width with transform: scaleX() (transform-origin at the centre
  edge) and transition 180ms --ease-out. Never animate width itself.
  Within a bid bar, the wall portion (rows[i][2]) is a separate inner layer in --mark, with the ordinary depth in --bid at
  70% opacity. The honest trader's large order is drawn in --ink-2 with a 45° hatch (repeating-linear-gradient, 2px lines every
  5px) so the two look alike but are visibly labelled. The spoofer's genuine small order (rows[i][3]) is a magenta outline
  (inset box-shadow 0 0 0 1px var(--mark)) on the ask side.
  Trades: when frame.traded > 0, a small mono tag "×N" appears at the touch row and slides 10px outward, fading out over 700ms.
- The three clauses of the law-informed detector, under the ladder, as a 3-row list. Each row: a 10px circle, a label and a
  mono value on the right.
    "1  Showed buying interest"   value = clauses[f][0] + " lots"
    "2  Withdrew it"              value = clauses[f][1] + " lots"
    "3  Traded the other way"     value = clauses[f][2] + " lots"
  While the value is 0, the circle is hollow (1px --ink-3 border). When the value first becomes > 0, the circle fills with
  --mark in a 260ms scale(0.4 → 1) with --ease-out, and the label turns --ink. No bounce and no overshoot.
- The score meter: a 6px-tall track, radius 3px, background --paper-3. The fill is scaleX(score / 50) with a 220ms
  transition. A 1px x 12px threshold tick sits at 10/50 of the width, with a 10px mono label "alert line: 10 lots". When score ≥
  SURVEILLANCE.threshold, an outlined badge "ALERT" (mono 11px, letter-spacing 0.14em, 1px --mark border, --mark text,
  radius 4px) appears with opacity 0 → 1 and scale 1.12 → 1 over 260ms, and the card border turns --mark.

SCROLL MAPPING
progress = clamp((scrollY - section.offsetTop) / (section.offsetHeight - innerHeight), 0, 1).
frame = round(progress × (frames.length - 1)). Both cards render the same frame index, because their frames share the same
time steps. Render only when the frame index changes.
Captions change by frame time t, relative to start = SURVEILLANCE.spoof.start:
  t < start                         "Before: an ordinary order book. Nobody has done anything yet."
  start ≤ t < spoof.end             "Both traders place a 48-lot buy order two ticks behind the best bid. Only one of them
                                     never meant it to trade."
  spoof.end ≤ t < reversal.end      "Left: the small sell fills and the wall is cancelled at once. Right: the order is still
                                     resting."
  t ≥ reversal.end                  "Right: news arrives, the trader cancels and sells 3 lots. Both accounts now read: showed
                                     45, withdrew 48, sold 3. Both alert."
The caption crossfades: the old text gets opacity 0 and translateY(-4px) over 160ms, then the new text gets opacity 0 → 1 and
translateY(6px → 0) over 260ms.

AFTER THE STICKY STAGE
A closing paragraph (font-text 1.15rem, max-width 38rem): "The difference is in the trader's head. The spoof's order was never
meant to trade; the honest one was, until the news changed. Nothing in the order data records that. This is why an alert is a
reason to look closer, not proof." Under it, a muted mono line: "Real simulator episodes, seed {seed}. Calm market, 16× orders."

REDUCED MOTION: no sticky scrubbing. The section height is auto, and the cards show the final frame plus a range input slider
to step through the frames by hand.

---

## PROMPT 3: "Where would you set the alarm?", the regulator's dial

Build section #dial. It is an interactive dot plot of every tested episode's detector score from results/teaching.md, with a
draggable alarm threshold. Its purpose is to show that no threshold separates spoofs from honest changes of mind, because they
score the same.

DATA
SURVEILLANCE.scores has keys such as spoof_16, layer_16, reversal_16, withdrawal_16 and control_16 (and the _8 versions). Each
is a sorted array of scores in lots. A size toggle (two outlined buttons, "8× orders" / "16× orders", aria-pressed, default 16)
switches between them.

LAYOUT
Heading h2 "Where would you set the alarm?" Under it, a lead paragraph: "Every dot is one tested episode. Drag the line: dots to
its right are flagged. A regulator chooses this line, and pays for every honest trader it catches."
The plot is an inline SVG with viewBox 0 0 1000 H, where H = 5 rows × 92 + 60. Each row is a band 92 units tall. The row
label sits at the left in font-display 600 15px, with a mono count under it ("80 episodes"). The plot area runs from x=220 to
x=900. The x scale maps 0 to 50 lots onto 220 to 900. The axis at the bottom has ticks at 0, 10, 20, 30, 40 and 50, in mono 11px
--ink-3, with 1px --line gridlines running up through every band at 15% opacity.
Rows, in this order: "Spoofs" (magenta), "Layered spoofs" (magenta), "Honest: changed mind" (--ink), "Honest: quick withdrawal"
(--ink-2), "Honest: genuine large order" (--ink-2).
Dots: radius 4.2. Because scores pile up at a few exact values, stack them as a beeswarm. Dots with the same score fan out
vertically in a compact hex packing around the band's centre line. Spacing is 9 units. Place dots alternately above and below
the centre. Once a column holds 9 dots, start a new column 9 units to the right. Each dot keeps its score's x position for the
first column.
Flagged dots (score ≥ threshold) are filled with the row colour. Unflagged dots are hollow (fill --paper, 1.2px stroke in the
row colour). On the right, for each row, a mono readout "74 / 80 flagged · 93%" with tabular-nums. When the percentage changes, it
tweens over 240ms.

THE ALARM LINE
A vertical 1.5px --ink line spans all bands, with a round 14px handle at the top that has a 1px --line ring. Above the handle, a
mono label shows "alarm at 10 lots". It is draggable with pointer events (setPointerCapture). It is also mirrored by a visible
<input type="range" min="0" max="50" step="1"> under the plot for keyboard and screen-reader users. The two stay in sync. The
default is SURVEILLANCE.threshold (10, the detector's real calibrated value, marked with a small "calibrated" tick that stays put).
While dragging, dots crossing the line change state with a 160ms fill transition.

LIVE READOUT (aria-live polite), under the plot, font-text 1.1rem:
"At {x} lots you catch {a}% of spoofs and {b}% of layered spoofs, and you wrongly flag {c}% of honest traders who changed their mind."
When a and c are both 0 or both > 80, add a second sentence in --ink-3: "Spoofs and changes of mind move together. Both score the full
size of the withdrawn order, so no line can split them."

ENTRANCE
When the section is 25% visible (IntersectionObserver, once), the dots fly in. Each dot starts at x = 220 with opacity 0 and moves to
its place over 700ms --ease-out, staggered by 4ms in row order. The rows fade in 80ms apart. The alarm line then slides from x = 900
to its default position over 900ms, delay 500ms. Under reduced motion, there is no fly-in.

SOURCE LINE (mono 12px --ink-3): "Scores from results/teaching_episodes.csv, law-informed detector, calm market. Every honest case here
is simulated. A score is a number of lots, not a probability."

---

## PROMPT 4: From a pattern to a payoff, sticky stacking evidence cards

Build section #economics. Four cards stack as you scroll, each one tucking under the next. They link the detection work to the
Economics proposal "When Does Market Manipulation Pay?". Every card carries an honesty chip saying what kind of evidence it is.

STRUCTURE
Heading h2 "From a pattern to a payoff" and a lead line: "Detecting a pattern and knowing whether it pays are different questions.
The Economics proposal is about the second one."
A container .sv-stack with the cards as siblings. Each card wrapper .sv-stack__item is position sticky,
top calc(96px + var(--i) × 22px), with height 78vh on desktop (auto with no stickiness on mobile under 760px, where the cards simply
follow one another with 16px gaps). Card: radius 22px, 1px --line border, background --paper (opaque, so the cards cover each
other), box-shadow var(--shadow), padding clamp(22px, 4vw, 48px). Inside is a 2-column grid: text on the left (1.1fr), a figure on the
right (1fr). It becomes one column under 900px.
Scale effect: as card i+1 scrolls into its sticky position, card i scales from 1 to 1 - (n - 1 - i) × 0.035, and its content dims to
opacity 0.55. Compute this from each card's getBoundingClientRect in one rAF-batched scroll handler. Use transform-origin top center.

Every card has a top row: a big mono index "01" … "04" (font-display 300, font-stretch 75%, 2.6rem, --ink-3), then the honesty chip on
the right. The chip is mono 10.5px, uppercase, letter-spacing 0.12em, 1px border, radius 999px, padding 3px 10px. Chip types:
  MEASURED · SIMULATION    (border --ink-2)
  DEVELOPMENT DATA ONLY    (border --mark, text --mark)
  PROPOSED · NOT YET RUN   (dashed border --ink-3)

CARD 01, "A fake order changes what others do" (chip MEASURED · SIMULATION)
Text: "With a large fake buy order on the book, the trader's genuine sell order filled 81% of the time. In the matched honest run,
without it, 69%." The big number "+12 points" counts up when the card becomes active. Under it, a small mono note: "95% interval +6
to +20 points · 8× wall, calm market · results/summary.md".
Figure: two horizontal bars (81% and 69%) drawn as SVG rects that grow from 0 over 900ms --ease-out when active. The 81% bar is magenta
and the 69% bar is --ink-2, each with a value label at its end.

CARD 02, "An effect is not a profit" (chip DEVELOPMENT DATA ONLY)
Text: "The Break-Even pilot subtracts the cost of the fake order itself being traded by accident. Across 48 simulated markets, the net
payoff's 95% interval sat above zero in 5, all with 16× walls and calm or very responsive books. In volatile markets the fake order was often
traded by accident: 18 of the 24 volatile cells were clearly negative." Then a muted line: "With 48 intervals, about one could sit above zero by chance. The test on
untouched seeds has not been run." Link: "Open the Break-Even Lab →" (break-even.html).
Figure: a 2 × 24 mini heatmap of the real 48 cells (from window.BREAKEVEN if loaded, or a compact copy in SURVEILLANCE). Cells
where it pays are magenta, unclear ones --paper-3 with a 1px --line border, and the rest --paper-2. The cells fade in row by row,
12ms apart.

CARD 03, "A suspicious pattern is not proof" (chip MEASURED · SIMULATION)
Text: "The law-informed detector flags 93% of 16× spoofs. It also flags 92% of honest traders who changed their mind. Asked to tell the
two apart, it scores 0.50: a coin toss." The number "0.50" counts up from 0.00.
Figure: a small coin-toss gauge. A semicircle arc (stroke --line) with a needle that swings from 0 to the middle (0.5) over 1100ms
with --ease-out and settles without overshoot. Labels "0 · always wrong", "0.5 · coin toss", "1 · perfect".

CARD 04, "So: when does it pay, and what should deter it?" (chip PROPOSED · NOT YET RUN)
Text: "Becker (1968): a rational trader weighs the gain against the chance of a penalty times its size. My model: expected extra payoff =
G − U − C − pF. In my pilot G and U are measured in lots, C is zero (the simulator has no fees), p is my detector's alert rate and F is a
scenario, not a real fine. Raising p with this detector also raises false alarms on honest traders, and that cost belongs in the model
too. Testing this properly is the Sixth Form project."
Figure: the equation set large in font-display 600, with each term in its own span. When the card becomes active, the terms light one by
one (opacity 0.25 → 1, 140ms apart). Then a hairline bracket draws under "pF" (SVG path, stroke-dashoffset from length to 0, 600ms) with
a mono caption "alert rate × hypothetical sanction".

ACTIVE DETECTION: a card is active when its top is within 120px of its sticky top. Trigger each card's animations once.
REDUCED MOTION: no scaling or dimming. Numbers and figures appear in their final state.

Close the page with a two-link row: "Break-Even Lab →" and "Read the detection study →" (teaching.html), and the shared site footer.
