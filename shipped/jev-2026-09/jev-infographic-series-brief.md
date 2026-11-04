# Jev field guide: infographic #1 "Nine ways it breaks": VISUAL PROMPT + ANIMATION PLAN
# READ THIS, APPLY IT, DO NOT EDIT IT.  (build brief for linkedin-visuals, 2026-09-22)

Companion to Content Idea 3e355c40-e4e7-81f2-9a01-fda5750fbed3 (the post says "the fixes are on
the graphic", so THIS image must carry all nine fixes verbatim).
Build as HTML/CSS in linkedin-visuals, NOT with an image model: every word and number must be
exact, and image models garble small text.

## 1. Where the design language comes from (Anton's refs, 2026-09-22)

| Trait | Seen in | How it lands here |
|---|---|---|
| Serpentine S-path, nodes alternating left/right | ref "Option A-D" S-curve (Anton: "easier to animate") | the spine of the whole image: 9 nodes on one continuous path |
| Technical-drawing brutalism: hairlines, registration marks, dimension ticks, visible grid | Pinterest board "brutalism" (47 pins) | 1px grid at 8% ink, corner reg marks, tick marks on the path |
| Huge tight grotesk display, mono micro-labels | board + s26.aimindset.org ("поток в эпоху агентов") | Space Grotesk 700 at -0.05em for the title; Space Mono labels |
| Curly-brace / bracket tokens in metadata | space.aimindset.org `{space}`, marketing `{sprint}`, board `[ PROJECT ]` | `{jev} / field guide`, `[ 01 ]` node labels |
| Spec-sheet readouts, big numerals | board ("72/48/32 type scale", "POLYMER 48", data tiles) | limits strip as mono readouts; node numbers as big outlined numerals |
| ONE accent per composition | each aimindset site uses exactly one (purple / red / yellow) | brand accent in the slot; everything else ink |

Brand constraints win over the refs where they conflict (DESIGN-BRIEF.md is the SOT):
- Accent = `#047857` on light ground (the board's acid lime and aimindset's warm paper are NOT
  brand values; the palette gate matches literal hexes and would fail them).
- Canvas `#F8FBFF`, ink `#0C0C0C`, muted `#6B6B6B`, faint `#A0A0A0`, border `#E5E5E5`.
- Type: Space Grotesk 400/500/600/700 + Space Mono 400/700. No other faces.
- No gradients, no shadows, zero border radius, no em/en dashes, `text-wrap: balance` on root.

## 2. Canvas + grid
Portrait 1080x1350 CSS px (render @2x = 2160x2700). 12-col grid, 64px outer margin,
24px gutter. Visible 1px grid lines at 8% ink behind everything. Corner registration marks.

## 3. Layout, top to bottom (heights are targets; layout-check + clipping gates decide)

### A. Header (0-210)
- mono meta, left: `{jev} / field guide · v1.13 · 2026-09`   right: `[ docs.typesafe.ai ]`
- title, Space Grotesk 700, 96px, -0.05em, 2 lines: **Nine ways it breaks.**
- sub, Space Grotesk 400, 24px, muted: "And the fix for each, from TypeSafe's own docs."
- 1px ink rule full width.

### B. Spec strip (210-380): what you ask, what the ceilings are
Three bordered cells, 1px ink, zero radius, mono label in brackets:
- `[ NOUL ]` yes / no · returns 1 probability · **no confidence field**
- `[ CHOICE ]` pick one · prob per option + confidence · **max 255 options**
- `[ SCORE ]` 2 to 10 levels · float + prob per level + confidence
Under the cells, one mono readout row, accent on the numerals only:
`64K CONTEXT · 32K STATE+Q · 1,200 REQ/MIN · $0.042 / 1M INPUT · OUTPUT NOT BILLED`

### C. The spine (380-1110): 9 nodes on one S-path
- Path: 2px accent stroke, continuous, runs down in a serpentine: row 1 left to right, U-turn,
  row 2 right to left, and so on. U-turns are true semicircles drawn as technical arcs (thin,
  with a small tick at each quadrant), NOT soft blobs. Tick marks every 40px along the path.
- 9 nodes, alternating sides, ~80px row pitch. Node = 56px square, 1px ink outline, mono
  numeral inside (`01`..`09`), crosshair reg mark at the top-left corner.
- Beside each node: failure NAME (Space Grotesk 600, 24px, ink) over its FIX (Space Mono 400,
  15px, muted). Copy, verbatim from docs lines 12762-12773:
  01 Literal reading            / Write the exact condition and criteria for each option
  02 Math and numbers           / Keep the arithmetic in code
  03 Date and time comparison   / Extract components; compare in code
  04 Indirection                / Reduce hops; point to the relevant state
  05 Irrelevant large state     / Filter first; send only what the question needs
  06 Adversarial content        / Precise prompts; test edge cases before deploying
  07 Contradictory criteria     / Align the criteria and the instruction
  08 Structural invariants      / Ask each decision one way; enforce identities in code
  09 Generation                 / Use a generative model
- Node 09 is the only inverted cell (ink fill, canvas numeral): the one failure whose fix is
  "wrong tool", so it reads as the exit.

### D. Routing bar (1110-1230): TypeSafe's EXAMPLE thresholds
- Horizontal 0 to 1 scale, 1px ink, ticks every 0.1, accent markers at 0.5 and 0.9.
- labels: `< 0.5 → a human reviews` · `low stakes → act, it's recoverable` ·
  `high stakes → act above 0.9, still confirm`
- Mandatory caption, mono, muted: "TypeSafe's example thresholds. Tune them on your own data."
  (Omitting this caption turns an example into a rule. It is a claims-gate item.)

### E. Footer (1230-1350)
Standard linkedin-visuals footer (avatar, name, page mark). Source line above it, mono faint:
`source: docs.typesafe.ai · jev-1.13 jaggedness + primitives`

## 4. Claims ledger (jev-infographic-breaks.claims.json): every figure must have a row
64k, 32k, 255, 1,200, $0.042, 0.5, 0.9, 2 to 10, and all nine name/fix pairs, each pointing at
the docs mirror line. The 0.5 / 0.9 row must carry the "example, tune on your data" note.

## 5. Gates that must run (and what they do NOT check)
palette, dashes, wrap, font, impeccable, claims, layout-check, AND the clipping check
(AGENTS.md rule 9: it does not run on every path today; wire it for this new format).
They do NOT check: whether the S-path reads left-to-right in the right order, whether node
text sits on the correct side, whether the routing caption is present. Eyeball those three.

## 6. Build cost
New single-frame format `card-infographic` (the existing card-bar / dashboard / flow / quote
cannot hold 9 nodes + a spec strip). First build ~2-3 h including gates; later infographics
~20 min each as configs.

---

# ANIMATION PLAN

Deliverable: native LinkedIn video, MP4, 1080x1350, 30 fps, ~14 s, loops cleanly.
Engine: linkedin-visuals motion runtime (GSAP, deterministic seek, `record.js` or `animate.sh`
via Remotion).

## Motion grammar: MEASURED from Anton's refs, not chosen by eye
Source: (private notes)
(che-video-brain lane, designlang 12.21 --deep-interact on all three aimindset sites, 2026-09-22;
raw tokens in (private notes)).
- ONE easing for everything: `cubic-bezier(0.2, 0.8, 0.2, 1)` (all three sites use this family;
  space 0.16/0.8/0.2/1, s26 0.2/0.8/0.2/1, marketing 0.2/0.8/0.3/1). Replaces the runtime's
  house default `power2.out` FOR THIS PIECE ONLY.
- Durations: md 280 ms is the workhorse (every rise/fade); lg 480 ms for section reveals
  (spec strip, routing bar). xs 120 / sm 160 for ticks and markers.
- THE entrance: slide up 16 px + fade, at md. Cards/cells: scale-in from 0.96.
- Stagger: 260 + n*150 ms (marketing's chip stagger) for the three spec cells and the three
  routing labels. Inside each node: name first, fix at +150 ms.
- No springs, no bounce, no overshoot (none of the three sites use one).
- ONE pulse, on ONE live element only (their shared rule: `topic-pulse` on the active node):
  here the pen-tip dot at the head of the S-path pulses a 0 to 15 px ring while drawing, then
  stops. Nothing else pulses.

GOTCHA that would silently void the easing: GSAP core does NOT parse "cubic-bezier(...)" strings
(motion-runtime.js says so in its own header; the tween falls back to default with no error).
Register the curve with GSAP's CustomEase plugin, or the "measured grammar" is a comment, not an
ease. Verify by sampling one tween's progress at t=0.5 against the curve's value.

## Timeline
| t (s) | What happens | Primitive |
|---|---|---|
| 0.0-0.6 | grid lines and registration marks fade in | `data-s` |
| 0.4-1.2 | meta line, then title rises 16 px + fades (md 280 ms), then sub | `data-s` |
| 1.2-2.4 | three spec cells scale-in from 0.96, stagger 260 + n*150 ms; readouts count up (64, 32, 1,200, 0.042) | `data-s`, `data-count` |
| 2.2-8.6 | the S-path DRAWS top to bottom at constant speed (linear, the pen should feel mechanical) | **NEW `data-draw`** |
| 2.2-8.6 | each node rises 16 px + fades (md) the moment the pen reaches it; fix at +150 ms; pen-tip dot carries the ONE pulse | `data-s` keyed to path length |
| 8.6-10.0 | routing bar wipes 0 to 1; 0.5 and 0.9 markers pop; caption fades last | `data-wipe`, `data-s` |
| 10.0-13.0 | HOLD on the full frame (this is also the static poster) | none |
| 13.0-14.0 | dissolve back to the frame-0 state so the loop seam is invisible | `data-out` |

## What has to be built first
0. Per-config easing override (`"ease": "cubic-bezier(0.2,0.8,0.2,1)"`) via GSAP CustomEase, so
   this piece uses the measured curve without changing the house default for every other card.
1. `data-draw` primitive in `scripts/motion-runtime.js`: tween an SVG path's
   `strokeDashoffset` from its length to 0 (GSAP handles this natively). Node reveal times are
   computed from each node's fractional position along the path, so the pen and the nodes stay
   in sync at any duration.
2. `card-infographic` format with motion wiring (render.sh `"motion": true`).
3. motion-check must pass: seam (last frame == first frame) and budget.

## LinkedIn specifics
- MP4 is the deliverable. A full-size GIF is impossible: motion-check's LinkedIn budget is
  36,152,320 total pixels, and at 1080x1350 that is only 24 frames. A preview GIF fits at
  540x675 (up to ~99 frames, about 10 s at 10 fps) if one is wanted.
- LinkedIn uses the first video frame as the thumbnail, and frame 0 is nearly empty by design
  (the loop seam). Upload the static PNG render as a custom thumbnail.
- Autoplay is muted: no audio needed.

## Sequencing
Static PNG first (it goes through every gate and is the fallback + thumbnail), THEN the MP4
from the same config. One config, two outputs.

---

# SERIES MAP: one Jev infographic per structure Anton supplied (2026-09-22)
All share ONE design language (Pinterest "brutalism" board + aimindset grammar + brand palette) so
they read as a series. Every figure still comes only from the docs mirror; any example value is
labelled "illustrative". Differentiated from Deepshikha Dhankhar's Jev AEO/GEO infographic (which
has no numbers, no limits, no fixes, no calibration method).

| # | Anton's ref (structure) | Jev content | Output |
|---|---|---|---|
| 1 | S-curve, options alternate L/R ("easier to animate") | Nine ways it breaks + the fix for each | PNG + MP4 (pen draws the path) |
| 2 | Sreeverse "contrast cheat sheet" (headline + 6 demo columns + low/strong compare panel) | Three question types: what each returns, a mini demo per type (probability bar / per-option distribution / level scale, values labelled illustrative), bottom panel "generate a paragraph" vs "return a typed answer" | PNG |
| 3 | "Skill as workflow" vertical pipeline (input, context, rules... output) | One call, end to end: state in, typed questions, ONE parallel pass, typed answers + probability, YOUR thresholds, act / confirm / human | PNG + MP4 (steps light up top to bottom) |
| 4 | Rational Lab arc with giant numerals 01/02/03 | The hard limits as giant readouts on an arc: 64K, 32K, 255, 1,200/min, $0.042 per 1M input | PNG |
| 5 | Hexagon cycle (6 segments around a core) | Calibrate before you trust it: count your labels, run Jev on them, measure error vs threshold, set the threshold, shadow run, cut over (Anton's own method from the plan) | PNG + MP4 (segments fill in turn) |
| 6 | Dieter Rams "10 rules" / "5 pillars" arc | TypeSafe's best practices: code owns control flow, one-second questions, select never generate, a None option, batch the questions, threshold on risk, questions + thresholds as constants in one place | PNG |
| 7 | Zigzag chevron stack (ref 10) | Alternate animated take on #3 or #5 if the hexagon reads too busy at 1080 wide | MP4 option |

Not used as a structure: the pastel "lead capture" flow (overlaps the GTM-wave angle and
Deepshikha's "how it works" row) and the dark chart kit (no real time-series data to chart
honestly; a bar chart of two vendor multiples would dress one claim up as data).

Build order recommendation: 1 (goes with the Publish Ready post), then 3 and 5 (the two that
animate well and carry Anton's own method), then 2, 4, 6 as the static set.
