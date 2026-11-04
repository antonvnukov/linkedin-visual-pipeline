# Format reference

## The shell is locked. The composition varies.

Two layers, and confusing them is expensive in both directions.

**Locked (never vary):** the typeface, the palette, the accent, and the avatar +
tagline footer. This is the recognition asset. It is what makes a card identifiably
one person's mid-scroll, and a feed where it changes is a feed with no author.

**Varies (must vary):** composition. Grid, reading path, silhouette, whether there is
a window frame at all.

Over 2026-08-12..14 four of five shipped configs were `card-flow`. Every per-card gate
was green the whole time, because every gate judged one card and none judged the
sequence. Three days of posts went out as one repeated template. The response nearly
made it worse: the first proposed fix was a new silhouette with no window chrome and a
different footer, which would have spent the brand to solve a scheduling problem.

`scripts/format-variety.py` now blocks a third consecutive use of one format at render
time and names what has gone unused. Override a deliberate repeat with
`LV_ALLOW_REPEAT=1`.

Silhouettes available today: the **window** family (`card-bar`, `card-dashboard`,
`card-flow`, `card-quote` — faux-OS chrome, pill, footer) and the **full-bleed split**
(`card-before-after` — no chrome, centred rail, glowing divider). Six further
compositions sit unported in `brand-guide/visual-system/templates/` (evidence map,
portrait comparison, parallel comparison, reset-compound-loop, event-os). Port one when
a post actually needs it, never speculatively.

Four formats, one config shape. Every config starts with `"format"`, and everything else is
content. Nothing brand-related belongs in a config: palette, typeface, footer name, avatar and
tagline all come from `brand.json`. A config that pins a font or a footer name will silently
override the brand for that one card, which is almost never what you want.

Accent words in any headline, note or body string: wrap them in `*asterisks*`.

## Shared keys

| Key | Default | Notes |
|---|---|---|
| `format` | `card-bar` | `card-bar` · `card-dashboard` · `card-flow` · `card-quote` · `card-infographic` · `carousel` |
| `theme` | `brand.rules.defaultTheme` | `light` · `dark` · `both` (single-frame formats) |
| `motion` | `false` | `true` also emits MP4 + GIF |
| `motion_ms` | `5500` | Animation length |
| `fps` | `24` | Playwright path. The Remotion path is fixed at 30. |

---

## `card-bar` — one stat, one part-to-whole bar

1080x1080. Window chrome, big hero stat, headline, source, a two-segment stacked bar, a
centred takeaway, then the footer.

```jsonc
{
  "format": "card-bar",
  "theme": "light",
  "motion": true,
  "window_title": "Citations by page type",
  "pill": "LLM study",              // top-right chip
  "stat": "62.1%",                  // rendered text
  "stat_count": 62.1,               // counts up from 0 in motion; omit to hold static
  "headline": "of LLM citations come from blog & list pages",
  "source": "Source: HubSpot AEO research",
  "green_label": "Blog & list pages",   "green_pct": 62.1,
  "gray_label": "All other page types", "gray_pct": 37.9,
  "note": "Measure citations, mentions, answers. *Not just clicks.*"
}
```

The two percentages must sum to 100. This is a part-to-whole bar, not a chart.

## `card-dashboard` — metric tiles + segment strip

1080x1080. Faux-OS window chrome, headline, eyebrowed metric tiles, a segment strip with
sparklines, a quote note, then the footer.

```jsonc
{
  "format": "card-dashboard",
  "theme": "dark",
  "window_title": "AEO scoreboard",
  "range": "Last 30 days",
  "headline": "Measure the *answer*, not the click",
  "subhead": "What actually moved this month",
  "tiles_eyebrow": "SIGNALS",
  "tiles": [
    { "label": "Citations", "value": "up",    "sub": "vs last month" },
    { "label": "Mentions",  "value": "+38%",  "sub": "across engines" }
  ],
  "strip_eyebrow": "ENGINES",
  "strip": [ { "name": "ChatGPT", "cap": "42%" } ],
  "note": "Direction beats precision when the baseline is new.",
  "note_cap": "METHOD"
}
```

`value` of `"up"` or `"down"` renders an arrow in a tinted island. Any other string renders
as a big accent number. **Use the arrow when direction is the point** rather than inventing a
figure. `strip` is optional; omit it for a tiles-only card.

## `card-flow` — four ordered steps

1080x1080. Window chrome, eyebrow plus title, a 2x2 grid of four connected steps read
clockwise (01 top-left, 02 top-right, 03 bottom-right, 04 bottom-left), a takeaway, then
the footer. Exactly four nodes: the grid and its connectors are built for that shape.

Reach for this when the content's meaning IS the order. A metric grid cannot say "first
this, then that", and flattening a sequence into one loses the argument.

```jsonc
{
  "format": "card-flow",
  "theme": "dark",
  "motion": true,
  "motion_ms": 5200,
  "window_title": "Prospecting stack",
  "pill": "Sequencing",                 // top-right chip
  "eyebrow": "GTM · PROSPECTING · SEQUENCING",
  "title": "The stack that *predicts timing*",
  "nodes": [                            // exactly 4
    { "label": "Intent Signals",
      "sub": "Trigify · PredictLeads · Common Room",   // kicker: name something concrete
      "insight": "Catch the signal before they know they're buying" },
    { "label": "Validate Fit",   "sub": "Apollo · TheirStack · BuiltWith",
      "insight": "Confirm ICP fit only after intent is detected" },
    { "label": "Enrich Contacts", "sub": "FullEnrich waterfall via Clay",
      "insight": "Enrich only what cleared layers one and two" },
    { "label": "One Per Layer",  "sub": "Don't stack",
      "insight": "Sequencing beats collecting more sources",
      "accent": true }                  // the payoff node, on the accent tint
  ],
  "caption": "You don't need more data sources. You need *one per layer, in the right order.*"
}
```

In motion the layers light strictly in sequence, then everything dissolves together so
frame 0 and the closing hold match. Timing constants live at the top of
`scripts/flow-card.py`, which is what the storyboard should quote.

## `card-before-after` — full-bleed split, the second silhouette

1080x1080, **no window chrome**. Centred eyebrow rail, two columns divided by a glowing
rule, footer with a hairline top border. Left is the old way: a slightly crooked pile of
struck-through cards. Right is the new way: a clean vertical pipeline of dotted nodes
ending on an emphasised final node.

Reach for this when the post's argument is a **contrast**, not a sequence or a stat. The
two sides compare effort, so they do not need equal row counts.

```jsonc
{
  "format": "card-before-after",
  "theme": "dark",
  "eyebrow": "GTM  ·  MCP  ·  TOOL ACCESS",
  "before": {
    "pill": "COPY / PASTE",
    "subhead": "You are still the one doing the work",
    "steps": ["Ask ChatGPT", "Copy the output", "Open the tool", "Paste it in"],
    "caption": "4-6 hrs of n8n debugging"
  },
  "after": {
    "pill": "MCP",
    "hero": "*5 min*, and it acts",              // accent with *asterisks*
    "steps": [
      { "label": "HeyReach: triage the inbox", "tag": "drafts" },  // tag is optional
      "n8n: build the workflow"                                     // plain string also fine
    ],
    "caption": "Claude acts inside the stack"
  }
}
```

`hero_size` (default 60) tunes the right-hand headline. Motion is supported: rows stagger
in, then pipeline nodes light in sequence.

- **Feed portrait at 1350 (2026-10-05, opt-in).** `"height": 1350` gives a 1080x1350 canvas. The
  extra height goes to the columns, never to a dead band: the header rows are shared through
  subgrid so both stacks start on one line, rows and pipeline nodes stretch to fill, and the
  connector runs node centre to node centre. Portrait implies `"treatment": "brutalist"` (square
  corners) and `"mobile": true` (30px floor) unless the config sets either one; the rail eyebrow
  is pinned to .05em tracking, because .14em on 30px type trips the impeccable `[wide-tracking]`
  warning. `hero_size` defaults to 76 there. Any height other than 1080 or 1350 fails loud, and
  without the key the card is byte-identical to before. Portrait also takes `"closing"`, one
  full-width line under the columns (it fails loud on a square card). Example:
  `examples/before-after-portrait.example.json`. QA: needs a `<config>.qa.json` with
  `"expectedHeight": 1350` (and `"minFontPx"` if you want the legibility floor checked).
- **`footer_tag` (any height).** Absent = the brand tagline in the footer's right slot, as before.
  `""` omits it and centres the identity so the footer stays balanced; any other string replaces
  the tagline with that plain text. Use `""` when the brand must not be hinted on the card.

## `card-email` — centred template card, the third silhouette

1080x1080, **no window chrome**. Eyebrow, headline, a small kicker line, then a single
centred card holding a label column and a monospace body, set with enough leading that
the lines read one at a time.

Use it when the content IS a template, skeleton or snippet the reader could copy. The
monospace column signals "this is the artefact" rather than prose about the artefact.

```jsonc
{
  "format": "card-email",
  "theme": "dark",
  "eyebrow": "OUTBOUND · COLD EMAIL",
  "title": "The *5-line* outbound email skeleton",
  "kicker": "Most cold emails fail before they're opened.",
  "rows": [
    { "tag": "SUBJECT", "text": "signal-based, under 6 words" },
    { "tag": "LINE 1",  "text": "one specific thing you noticed about them" }
  ]
}
```

Tunables: `body_size` (23), `tag_col` (132), `row_gap` (10), `row_pad` (17).

**The mono face is a BRAND property, not a per-card override.** It comes from
`brand.font.mono` (Space Mono, Colophon's companion to Space Grotesk) and is cached by
`scripts/fetch-fonts.py` like the primary. Declaring it there is what lets the QA font
check keep asserting that every text node renders in a *declared* family; exempting the
mono element instead would have blinded that check to real drift on it forever.

## `card-quote` — quote, with an optional hero stat

1080x1080. Eyebrow, an optional hero stat and label, the quote, the source, an optional
supporting line, the footer.

```jsonc
{
  "format": "card-quote",
  "theme": "dark",
  "eyebrow": "WHAT BUYERS ACTUALLY DO",
  "stat": "70%",                                    // optional
  "stat_label": "of the decision happens before contact",
  "quote": "They are not comparing you. They already decided.",
  "source": "Gartner B2B buying study",
  "accent_line": "3 stages: Awareness • Shortlist • Decision"   // optional, secondary text
}
```

`stat` is optional. Drop it when the quote is the piece, and the quote becomes the hero;
forcing a number into the slot invents emphasis the copy never asked for. Raise
`quote_size` (default 32) when there is no stat competing for the eye. `accent_line`
renders under the quote in brand secondary text, wrapped at `accent_width` (660px) so a
long list breaks into balanced lines instead of orphaning its last word.

## `carousel` — N slides to a PDF

Two families, chosen from the config. Both take a `slides[]` array and ship as a swipeable
LinkedIn document post.

**Square** (default, 1080x1080, always the dark theme):

```jsonc
{
  "format": "carousel",
  "slides": [
    { "type": "title",     "headline": "...", "kicker": "..." },
    { "type": "statement", "headline": "...", "body": "..." },
    { "type": "list",      "headline": "...", "items": ["...", "..."] },
    { "type": "split",     "headline": "...", "left": {}, "right": {} },
    { "type": "versus",    "headline": "...", "left": {}, "right": {} },
    { "type": "close",     "headline": "...", "footer": "..." }
  ]
}
```

Inline SVG icons available on the square family: `gears`, `fire`, `sprinkler`.

**Portrait** (1080x1350, per-slide light or dark), triggered by `"size": "portrait"`:

```jsonc
{
  "format": "carousel",
  "size": "portrait",
  "show_slide_count": true,
  "slides": [
    { "type": "hook",      "theme": "dark",  "eyebrow": "...", "headline": "...", "subtext": "..." },
    { "type": "statement", "theme": "light", "headline": "...", "body": "...", "chips": ["A", "B"] },
    { "type": "bignum",    "headline": "...", "bignum": "4", "body": "..." },
    { "type": "quote",     "headline": "...", "flow": ["Signal", "Trigger", "Reply"] },
    { "type": "cta",       "headline": "...", "body": "...", "button": "...", "source": "..." }
  ]
}
```

Prefer `statement` with `chips` over a bare `bignum` when the point is a part-to-whole
call-out: four platform names as pills beat the number 4 on its own. `chips` is also the
right home for an **evidence pair** (`"20K+ chars: 10.18 cites"` / `"Under 500: 2.39 cites"`),
which a single `bignum` cannot hold — and it is the only way a signal with *no* number stays
a visual sibling of one that has them, by carrying labels instead (`Leader` / `Challenger` /
`Niche player`). Forcing a figure into a slot the copy never claimed is the failure mode.

The portrait family also has **`versus`** — two labelled lanes for an old-way / new-way
contrast, which is neither a sequence (`flow`) nor one set (`list`):

```jsonc
{
  "type": "versus", "theme": "light",
  "kicker": "The Shift",
  "headline": "AI decides *whether* to cite you. Not where you rank.",
  "left":  { "title": "What rank trackers see", "items": ["Ranking position", "Keyword volume"] },
  "right": { "title": "What AI decides on",     "items": ["Citation frequency", "Mention order"] }
}
```

The left lane renders muted on purpose: it is the column being retired. Deliberately not a
table — no cell borders, no header fill — so it survives feed-size reading.

**`versus` means different things in the two families.** Square takes `left`/`right` as
strings plus `left_title`/`right_title`; portrait takes objects with `items[]`. Portrait is
reached only via `"size": "portrait"`, and `versus` is deliberately **not** in `build()`'s
type sniffer, because adding it there would misroute every square carousel that uses it.

Headlines use `text-wrap: balance`, body uses `text-wrap: pretty`.

**Slides are top-anchored, and the type scale is large.** Both were the opposite once, and
the pair of defects only shows up on a deck with sparse copy. Vertical centring split the
leftover space across the top *and* bottom, so a slide holding an eyebrow, a headline and two
lines of body filled **29% of the frame** and read as a square block floating in a portrait
canvas. Centring also let the first content row land anywhere from y=238 to y=366, so the
whole block jumped on every swipe. Anchoring the top collapsed that drift to 9px and moved
the remaining space to the bottom, where the pinned footer already terminates the eye.

Type sizes were raised roughly 1.3x at the same time (`.phook` 88 -> 120, `.ph2` 68 -> 92,
`.pcopy` 30 -> 37, chips 26 -> 31), which took fill from 29-47% up to 48-71%. Going further
is counterproductive: at 150px the hook rag broke to "citations" and "rank in" on their own
lines, which looks worse than the void did.

`scripts/layout-check.py` now measures both properties on the rendered PNGs and blocks the
carousel path before the PDF is copied out. It is the only gate here that judges the space
*around* the content rather than the content itself, and the only one that judges a
whole-deck property — per-slide checks are structurally blind to swipe drift. Thresholds:
`--min-fill 45`, `--max-drift 40`. Two-sided self-test: `python3 scripts/layout-check.py --self-test`.

The portrait footer shows the brand avatar. It used to render one only when a config named
an `avatar` path, so every carousel shipped with the fallback dot while the card formats
showed a face — a silent split in the layer that is supposed to be locked. It now falls back
to `brand.footer.avatar` (already resolved by `brandkit`), and the config key stays as a
deliberate override.

**The two families are separate render paths.** Any change to the portrait path must leave
the square path byte-identical. Re-render the square example and diff after editing the
builder.


## `treatment: "brutalist"` — a posture, not a format

An opt-in override layer on the portrait carousel. Same face, same palette,
opposite posture: radius to zero, every LABEL moved to the mono face inside
`[ brackets ]`, chips boxed in hairlines, corner registration marks framing the
live area, display tracking closed to `-.05em`, hard `#FFFFFF` ground.

```jsonc
{ "format": "carousel", "size": "portrait", "treatment": "brutalist", "slides": [...] }
```

It introduces no colour: everything resolves to existing brand tokens, so the
palette gate still sees only declared hexes. Omit the key and the deck renders
in the default soft-minimal posture. Both were shipped side by side once so the
difference could be judged rather than argued about.

The vocabulary comes from the `industrial-brutalist-ui` skill, which specifies
this direction far more completely (Swiss Industrial Print vs Tactical Telemetry,
tracking ranges, framing devices). **Read that skill before extending this
treatment**; do not re-derive the direction here.

### `dotmatrix` — magnitude contrast without a lying chart

```jsonc
{ "type": "dotmatrix", "theme": "light",
  "headline": "30 searches a month can beat *30,000*",
  "left":  { "filled": 60, "total": 60, "value": "30/mo",     "caption": "Ready to buy." },
  "right": { "filled": 2,  "total": 60, "value": "30,000/mo", "caption": "Ready to read." } }
```

**Both grids are the same size on purpose.** The card that prompted this contrasts
30 against 30,000, a 1000x ratio no grid can draw; drawing it not-to-scale would
be a lying chart. So inked dots encode INTENT DENSITY and the volumes stay as
labels. No dot stands for a fixed quantity, and the claims ledger's
`publicationBoundary` says so explicitly. Any reuse must keep that property.

`value` is set in Grotesk, never mono: a monospace face gives the thousands
comma a full character cell, so `30,000` renders as `30 , 000` and reads like a
typo. The brutalist treatment re-applied mono here once and reintroduced exactly
that defect.

### `verdict` — an inequality, set as one

```jsonc
{ "type": "cta", "verdict": { "win": "Low volume + high intent", "op": ">",
                              "lose": "High volume + zero intent" } }
```

Winning side in accent, operator as the pivot, losing side muted. It exists
because the post's whole thesis was first rendered as a 25px grey footnote below
the CTA button, placed there only to lift a fill percentage from 44% to 45%.
Placing content to satisfy a metric is how that happens; the fill improving to
64% afterwards was a side effect, not the reason.

## The wrap rule

`text-wrap` INHERITS, so it is declared once on each card root rather than on a
list of classes a new element could silently miss:

- **`balance`** on the root: even line lengths for short fragments. A four-word
  chip breaks 2+2, not 3+1 (`"Clay to LinkedIn / Ads"` was the bug).
- **`pretty`** on real paragraphs: orphan prevention without forcing even lines.

All six card builders shipped with ZERO `text-wrap` declarations, so this was a
pipeline-wide defect, not a carousel quirk. `gate.sh` now fails any card missing
the root declaration.

## Gates added while building this

Three, each two-sided self-tested, each from a defect that shipped green:

| Gate | Catches | How it got through before |
|---|---|---|
| `[wrap]` | missing root `text-wrap` | no builder had one |
| `[font]` | a `font-family` value containing a colon | an injected property split the declaration, every headline fell back to serif, and the carousel path runs no `qa-visual` so nothing checked the typeface |
| `layout-check` content inset | decorative frame counted as content | corner marks at the canvas edges defined the first and last ink rows and reported a fictional 94% fill on all seven slides |

`format-variety` also learned two things the hard way: a re-render of one config
is idempotent (`--config`), and `LV_NO_RECORD=1` keeps a regression render out of
the ledger. A/B treatments of ONE post are one post, so they get one row.

## `card-infographic` — a reference sheet, one path, read in order

Portrait 1080x1350, single frame. Layout `"spine"`: header, a three-cell spec strip, a mono
readout row, **5 to 9 nodes strung on one serpentine path** that turns alternately right and
left (each node = a `name` and a `fix`), a 0-to-1 threshold scale, footer. Built for a list
that is READ IN ORDER and where every item carries a two-part payload. A card cannot hold nine
items; a carousel splits a reference across swipes, and a reference sheet is one screen you save.

```json
{ "format": "card-infographic", "layout": "spine", "theme": "light",
  "motion": true, "motion_ms": 14000, "fps": 30,
  "ease": "0.2,0.8,0.2,1", "rise": 16,
  "meta_left": "{jev} / field guide", "meta_right": "[ docs.example.com ]",
  "title": "Nine ways it *breaks.*", "sub": "And the fix for each.",
  "cells": [{"label": "NOUL", "line": "Yes / no", "detail": "returns 1 probability", "emph": "no confidence field"}, "... x3"],
  "readout": "*64K* context · *1,200* req/min",
  "nodes": [{"name": "Literal reading", "fix": "Write the exact condition"}, "... 5 to 9"],
  "scale": {"markers": [0.5, 0.9], "labels": ["...", "...", "..."], "caption": "Whose thresholds these are."},
  "source": "source: ..." }
```

- **Unknown keys FAIL LOUD** (AGENTS.md rule 11). So does a node with any key but `name`/`fix`,
  a node count outside 5-9, a cell count other than 3, and a `scale` with no `caption`: an
  example threshold printed without saying whose it is reads as a rule.
- **Motion.** The path DRAWS at constant speed (`data-draw`, with a pen-tip marker that pulses
  while it moves); each node lands when the pen reaches it, so the reading order IS the
  animation. `"ease"` / `"rise"` carry a MEASURED motion grammar into this one card (they become
  `data-ease` / `data-rise` on the root) without changing the house default for every other card.
  The runtime solves the cubic-bezier itself because GSAP core ignores `cubic-bezier(...)`
  strings; `node scripts/motion-runtime-selftest.cjs` proves the solver against a reference.
- **Loop seam: gated automatically since 2026-09-28.** `render.sh` diffs frame 0 against the
  frame at `motion_ms` on the lossless PNGs (`motion-check.py seam-frames`, tolerance 0) and
  exits 1 on any difference; the builder also refuses a `motion_ms` that ends before the last
  dissolve. Do not use `motion-check.py seam` on the MP4 for this canvas: H.264 drift of 1-3
  levels across the flat background fails it either way.
- **Motion recipes: rotate, don't repeat.** Every Jev card through 2026-09-27 shipped with recipe
  A, which is part of why they read alike. Give each new motion card the next recipe below. Log
  the letter in the card's Notion Notes, and never ship two consecutive posts on the same recipe.

  | Recipe | `theme` | `ease` | `rise` | Feel | Verified |
  |---|---|---|---|---|---|
  | A house | light | `0.2,0.8,0.2,1` | 16 | measured default | 8 Jev cards |
  | B house dark | dark | `0.2,0.8,0.2,1` | 16 | same rhythm, inverted | palette gate only |
  | C glide | light | `0.45,0,0.2,1` | 32 | slow start, long travel | via F |
  | D crisp | dark | `0.9,0,0.1,1` | 6 | hard snap, short travel | not yet rendered |
  | ~~E overshoot~~ | light | `0.3,1.35,0.5,1` | 20 | DO NOT USE: `che-video-brain/MOTION.md` §4 bans bounce | seam OK, banned by doctrine |
  | F glide dark | dark | `0.45,0,0.2,1` | 32 | C on dark (+ `headers_first` on decisions) | claim-check-dark, seam OK |

  Measured limit (claim-check, A vs F, 2026-09-28): the share of pixels changing between
  samples was 3.7/4.1/2.7/0.8% vs 3.5/4.7/2.8/0.9%. Recipes change the LOOK and the feel of each
  entrance. They do not change the build-then-dissolve PATTERN. If "they all move the same" comes back
  after two recipe-rotated posts, that is the trigger for the return/hold-life/morph phases in
  `docs/motion-review-2026-09-28.md`.
- **Motion variety is gated, not remembered (2026-09-28).** `render.sh` runs `motion-variety.py`:
  it BLOCKS a motion signature (layout, theme, ease, rise, style, return, live, morph)
  identical to the last shipped motion card, and WARNs after 3 cards that add no motion option
  never used before (a new layout does not count). `python3 scripts/motion-variety.py suggest`
  lists untried options, then primitives to BUILD next. When the menu runs dry, build one.
  History: `.motion-history.jsonl` (backfilled with the 6 published Jev motion cards).
- **Motion grammar keys (2026-09-28), any layout unless noted.** Rules come from
  `(private notes)` §4 (video SOT) and the gotomoney.io-web `MOTION.md`
  "Premium rules". This file implements them and does not restate them.
  - `"motion_return": "reverse"`: each element exits by playing its own entrance backwards,
    last in first out, one beat apart (pens un-draw, rises sink). Replaces the flat dissolve.
    It makes the loop longer, so the builder tells you the new minimum `motion_ms`.
  - `"motion_live": true`: a ring pulses off the abstain chip through the hold, so no 1.5s
    window freezes. `render.sh` now WARNs on any window that changes under 0.2% (`dead-hold`).
  - `"motion_morph": true` (decisions only, needs an abstain option and `bands`): the abstain
    chip changes shape into the first confidence band and back ("unresolved routes low"). The
    original dims to a ghost and hold-life takes over after it returns. It uses GSAP Flip, which
    `record.js` injects. Taste note: the chip's mono text stretches with the box mid-flight.
  - Proof lives in CI: `examples/infographic-decisions-motion.example.json` uses all three and
    must pass the lossless seam gate.
- QA: portrait needs a `<config>.qa.json` with `"expectedHeight": 1350`. Put the claims you must
  not lose (the scale caption, the first and last fix) in its `requiredText`, and pin
  `selectorCounts` (`.node`, `.item`, `.cell`, `.mark`): a gate then checks what the eye used to.
- The Remotion path (`animate.sh`) refuses this format: it has not been exercised at 1080x1350.

### Layout `"cycle"`: six steps on one hexagonal loop

For a process that REPEATS (calibrate, review, release). Keys beyond the common ones: `steps`
(exactly 6, each `name` + `detail`), `core` (`kicker` + `line`, centred in the inner hexagon),
optional `quote` (`text` + a non-empty `cite`: a quote with no owner is refused) and
`loop_note`. Spine keys in a cycle config fail loud, and vice versa. Steps run clockwise from
the top vertex; text columns start past the widest node plus a 26px gap (a fixed column width
put two nodes flush against their text). Motion: the pen draws the whole hexagon and closes it,
each segment fills as the pen passes its midpoint, then a chevron marks the loop.

### Layouts `"decisions"` and `"sort"`: the save-worthy reference sheets

`"decisions"` also takes `"motion_style": "headers_first"` (optional): instead of one card fully
revealing top to bottom before the next starts, all four numbered headers land in one fast
preview beat, then details cascade in per card. Use it to vary the rhythm on a run of
consecutive `decisions` posts so they don't all play back identically in the feed.

Not a diagram of an idea: the reference itself. Header and body share one flow column, so the
sub-line follows however many lines the title takes (a fixed offset left a 100px void).
`"decisions"`: 3 to 5 `decisions`, each `name`, `type` (`noul`/`choice`/`score`), `ask`,
`route`, plus `options` (2 to 6, forbidden on a `noul`) and an optional `abstain` that must be
one of its options and renders in the accent; then `bands` (`markers`, `labels` = markers + 1,
mandatory `caption` naming whose thresholds they are) and optional `never`. `"sort"`: exactly 3
`columns`, each `label`, `rule` and 3 to 6 `items` (`task` + `why`), plus optional `readout`.
Six items per column fill the frame at the enlarged type; five left a ~180px void.

### Layout `"mega"`: the dense cheat-sheet poster (lead magnet)

Deliberately small in the feed: titles read at feed size, detail does not, and the full file
(2x PNG + a vector PDF) is what a "comment X" reader gets. Exactly 3 `sections` (`label`,
`question`, 3 to 5 `cards`) plus a required `legend` (one line per kind). Each card is `kind`
`typed` (needs `type`, options 2 to 7 unless noul, optional `abstain` that must be an option),
`code` or `human` (neither may carry type/options). Cards are `flex:1 0 auto`: an equal-share
`flex:1` let one card shrink below its text and overflow its border while every gate stayed green.

### Layout `"flow"`: the architecture poster

A top-to-bottom pipeline: 4 to 8 `stages` (`title`, `cards` 1 to 3, optional `note`, `gate`
with `q`/`yes`/`no`, `bands` with `markers`/`labels`/`caption`), a required `legend`, an
optional left `rail` (0 to 4 blocks of `head` + `lines`) and an optional `cta`. Card kinds:
`typed`, `code`, `human`, `llm`. `height` runs 1350 (feed portrait) to 2700; default 2160.

- **Type floor (2026-10-04).** Every small line (kind badges, chips, detail lines, band ticks,
  captions, rail heads, footer role and source) renders at `FL_MIN_PX` = 12.5px, gate 6 of
  `gates/card-infographic.md`. They sat at 10 to 12px before. If a config no longer fits at
  1350, cut words or a card; never lower the constant.
- **Step numbers start at 01 (2026-10-04).** Posts number steps from 1. `"number_from": 0`
  (opt-in, 0 or 1) keeps the old 00-based tags for a poster whose first stage is an intake
  step; `shipped/jev-2026-09/jev-infographic-architecture.json` sets it, so its output did
  not change. Any other value, or the key on another layout, fails loud.
- **Feed portrait at 1350 (2026-10-04, from Taste Loop B, scored 9.1).** At exactly
  `"height": 1350` the builder switches to the `FL_TYPE["portrait"]` profile: small lines
  (badges, legend, chips, rail heads, notes, footer role and source) at 18px, card detail lines
  at 19px in the text colour, card titles 19px, rail lines 21px with proof figures (18, 310K,
  110%) bold in the accent, stage tags 16px, a 270px rail whose blocks spread over the full
  height of the stage column, and heavier dashed connectors with larger arrows. Plan a 1350 card
  for about 4 stages of 1 card each. Any other height keeps the tall set above, so the 2160
  poster renders unchanged.
- QA: a 1350 card needs a `<config>.qa.json` with `"expectedHeight": 1350`; pin
  `selectorCounts` for `.stage`, `.conn`, `.fcard`, `.rblock`.

## Known gaps

- Arbitrary flow-diagram and versus-lane layouts are not config-driven yet. They currently
  need a bespoke build. The next time one comes up, fold a `flow` or `versus-lanes` type into
  the portrait family instead of hand-authoring another one-off file.
- `card-quote` has no motion variant wired into `render.sh` yet.
