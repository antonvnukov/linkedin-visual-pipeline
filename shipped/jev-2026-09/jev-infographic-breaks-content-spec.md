# Jev field guide — infographic CONTENT spec (styling pending Anton's Pinterest refs)

Canvas: portrait 1080x1350 (render @2x = 2160x2700). One frame. Brutalist posture.
Every figure below is verbatim from TypeSafe's docs mirror
((private notes)) and must be ledgered in
`jev-infographic-breaks.claims.json` before render. Nothing here is Anton's own measurement.

## Reading order (top to bottom = animation reveal order later)

### 00 HEADER
- kicker: `[ JEV FIELD GUIDE ]`   right-aligned: `v1.13 / 2026-09`
- title: "Before a decision model gates your revenue"
- one-liner: "Typed answers, one parallel pass, 70-500ms. It never writes prose."

### 01 WHAT YOU ASK  (3-column spec table)
| NOUL | CHOICE | SCORE |
| yes / no | pick one of N | rate on a rubric |
| returns: 1 probability | returns: pick + prob per option + confidence | returns: float + prob per level + confidence |
| NO confidence field | max 255 options | 2 to 10 levels |
Callout under the table: "When nothing may fit, give CHOICE a None option. TypeSafe's own rubrics do." (docs lines 5071, 5092, 5139). Keep NOUL's fact to exactly: "no confidence field".

### 02 HARD LIMITS  (spec strip, mono readouts)
- 64k context total  /  32k for state + longest question
- 250k tokens/sec  /  1,200 requests/min
- text + JSON only  /  no fine-tuning, no weights, no self-hosting
- $0.042 per 1M input tokens  /  output tokens not billed

### 03 BATCH, DON'T LOOP  (one big figure pair)
- 13 questions, 1 call  vs  13 calls
- 11.5x cheaper   9.6x faster   same answers
- source line: "TypeSafe docs, 'Batching doesn't change the answers'"

### 04 NINE WAYS IT BREAKS  (the dense core: 9 rows, name | fix)
1 Literal reading            | Write the exact condition + criteria per option
2 Math and numbers           | Keep the arithmetic in code
3 Date and time comparison   | Extract components; compare in code
4 Indirection                | Reduce hops; point to the relevant state
5 Irrelevant large state     | Filter first; send only what the question needs
6 Adversarial content        | Precise prompts; test edge cases before deploying
7 Contradictory criteria     | Align the criteria and the instruction
8 Structural invariants      | Ask each decision one way; enforce identities in code
9 Generation                 | Use a generative model

### 05 ROUTE ON CONFIDENCE  (threshold bar; the VENDOR'S EXAMPLE, not a rule)
- < 0.5            -> genuinely unsure: route to a human
- low-stakes action (e.g. show a balance) -> act, it's recoverable
- high-stakes action (e.g. approve a transfer) -> > 0.9: proceed WITH confirmation;
  below that: ask the user to confirm first
- label on the bar, mandatory: "TypeSafe's example thresholds. Tune them on your own data."
  (docs: "The correct threshold values depend on your domain ... Start with conservative
  thresholds, test with your own data, and adjust.")
- footnote: "Calibration holds across many predictions, not for the one in front of you."

### 06 FOOTER
- "Measure it on your own labelled decisions before you trust any multiple."
- source: docs.typesafe.ai (jev-1.13 jaggedness + primitives)
- standard linkedin-visuals footer (avatar, name, page mark)

## Density check
6 blocks, ~45 text units. That is a DETAILED infographic, not a card: the existing formats
(card-bar / dashboard / flow / quote) cannot hold it. Needs the new `card-infographic`
format. Clipping gate must run on it (AGENTS.md rule 9).

## Open until Anton's refs arrive
grid (columns / gutters), type scale, how hard the brutalism goes (raw borders, monospace
share, inverted blocks), accent use, texture/noise, dark vs light ground.
