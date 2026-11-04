---
name: visual-pipeline
description: >
  Turn a rough brief into a ship-ready social visual on YOUR brand: a PNG card or a swipeable
  PDF carousel. Renders one of four formats from a JSON config, then runs the mandatory chain:
  a deterministic QA gate, a claims ledger, and a blind checksummed review loop that iterates
  until the render scores 9.0 or better with no high-severity issue. Every colour, typeface and
  footer comes from brand.json, so nothing is hardcoded to one company.
  Use when asked to "make a visual for this post", "turn this stat into a card",
  "build a carousel", or when handed a visual brief. For motion, use visual-motion.
---

# Visual pipeline

Brief in, ship-ready asset out. The mechanics are deterministic and gated; the judgment is a
loop. Never hand-author a card's HTML: extend a builder instead, or the gate and the taste
loop have nothing to hold onto.

## Setup (once)

```bash
bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/setup.sh"                # installs Playwright + Chromium, then PROVES it by
                                     # rendering a real card and asserting the PNG
cp brand.example.json brand.json     # then edit: palette, font, footer, avatar
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/brandkit.py"          # self-check: prints the resolved brand
```

`bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/setup.sh" --check` reports what is missing and the exact command for each, and
changes nothing. Run it first when anything fails to render.

`brandkit.py` is the only place the pipeline learns what a brand looks like. Point at a
different `brand.json` (via `--brand`, `LV_BRAND`, or cwd) and every format re-skins. If you
ever find yourself typing a hex or a font name into a builder, that is the bug.

---

## The loop

### 1. Get the input

A config JSON, or a rough brief you map to one. If it is a brief, confirm the honest-data
call before building: never ship a number you have not sourced, and prefer a two-value split
derived from one real stat over an invented multi-bucket breakdown. Show the source on the
card, or keep it in the post copy, but know it either way.

**Fact-check the premise before you build.** A pasted brief is a hypothesis. Verify its core
claim against a primary source, not against the brief. Getting this wrong costs you the whole
build, three times over.

### 2. Pick the format

| `format` | Canvas | Shape | Ships as |
|---|---|---|---|
| `card-bar` | 1080x1080 | One hero stat + a two-segment part-to-whole bar | PNG (+ MP4/GIF) |
| `card-dashboard` | 1080x1080 | Metric tiles + a segment strip with sparklines | PNG (+ MP4/GIF) |
| `card-quote` | 1080x1080 | Hero stat + divider + quote + source | PNG (static only) |
| `card-infographic` | 1080x1350 | Dense reference sheet: 3-cell spec strip, 5 to 9 nodes on ONE serpentine path (name + fix each), a 0-1 threshold scale | PNG (+ MP4/GIF via render.sh) |
| `carousel` | 1080x1080 or 1080x1350 | N slides, per-slide themed | PDF document post |

Field-level schemas and slide types: [formats.md](formats.md).

Two more choices: `theme` (`light` / `dark` / `both`) and `motion` (`true` adds MP4 + GIF).
Dark reads as opinion and leadership; light reads as data and evidence. A single frame ships
as a **PNG**, never a one-page PDF. A one-page PDF is not a carousel.

**The title implies the layout.** If the brief's headline contains a relationship word (`vs`,
`versus`, `two X`, `compared to`), build a parallel or versus structure, not a linear chain,
even when the brief lists its points as a flat sequence. If it is genuinely ambiguous, say
which reading you picked and why before rendering.

### 3. Render + gates (one command)

```bash
bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/render.sh" <config.json> <basename> <outdir> [brand.json]
```

Three enforcement layers run inside, in order, and a failure in any of them exits non-zero
with no shipped file:

1. **Claims** — if the config renders figures, `<config>.claims.json` must exist and pass
   `claims.py check` (see step 4 for authoring it).
2. **Palette/dash gate** — every literal hex legal for this theme in `brand.json`, no em or
   en dashes, plus the `impeccable` anti-slop detector if installed. Carousels are per-slide
   themed, so they gate against the union of both theme palettes.
3. **QA** — the deterministic assertion suite (`qa-visual.cjs`) runs on every card render and
   emits an immutable candidate directory (`<base>-<theme>-candidate-<ts>/` with
   `qa-report.json`, `feed-preview.png`, `native-2x.png`, checksummed). The shipped PNG is
   copied out of that candidate, so the artifact IS the certified render. The candidate is
   the round-1 evidence bundle step 5 hands the loop. (Per-slide carousel QA is not built yet.)

**These are a floor, not a taste check.** They catch literal anti-patterns. They do not
judge composition, whether the layout suits the content, or whether the card is merely
competent. A card can be 100% gate-clean and still be so-so. That is what step 5 is for.

### 4. Claims ledger (enforced at render)

Every figure the card renders needs a claim: a classification, a source, and a cap on how
often it may appear prominently. `render.sh` refuses a figure-bearing config without it.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/claims.py" init <config.json>     # pre-filled draft, all `unverified`
# edit: set each classification, add sources, write publicationBoundary
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/claims.py" check <config.json> <config.claims.json>   # render.sh runs this too
```

**A generated draft cannot satisfy this.** Every generated claim lands as `unverified` and the
check fails while any remain. If a model could both write and satisfy the ledger, the ledger
would be theatre. A human says where each number came from.

### 4b. Concept check before the loop (added 2026-10-06)

The loop costs about 1.5M tokens a card and scores gate compliance, not the owner's taste (a card that
reached 8.7 was rejected on sight; a one-shot image-model concept was accepted at first look). Before the
loop: view the built card. If the builder reports empty or repeated blocks, the format is wrong for the
post: change the format, do not iterate. Cheap alternative that shipped four cards on 2026-10-05/06:
generate two concept images with an image model (4:5), pick one, redraw it as self-contained HTML at
1080x1350 with the brand fonts, the avatar and the footer tag, run `scripts/gate.sh` on the HTML, and list
every string against the post text. Tell the loop's fixer to change only its working copies, never files
in this repository.

### 5. Taste Loop B (the only loop)

There is no cheap tier and no bypass. Freeze the candidate, checksum it, hand independent
critics a blind evidence bundle and numbered gates, iterate `v1..vN` until it scores 9.0 or
better with no high-severity issue. The **best-graded** version ships, not the last one.
`candidate`, `qaReport` and `feedPreview` are the candidate directory step 3 printed —
`render.sh` already produced round 1's evidence; do not re-run `qa-visual` by hand.
Pass `candidate` as the FILE `<candidate dir>/final.png`, never the directory: `gates.py assemble`
hashes it, a directory raises `IsADirectoryError`, no critic brief is written and every critic returns
`checksumVerified:false` (2026-10-17: a whole round, 564k tokens, produced no score).

```
Workflow({ scriptPath: "<plugin>/skills/visual-pipeline/taste-loop.js",
           args: { candidate, configPath, claimsPath, format, theme, outdir, brief,
                   pluginDir, brandPath, evidence: [qaReport, feedPreview],
                   routes, critics: 3, maxRounds: 3, passScore: 9.0 } })
```

Every format `render.sh` builds runs in the loop (`check-spec.py` fails CI on drift). The fixer
re-renders through `gate.sh` and `qa-visual` with the `<config>.qa.json` beside `configPath`,
as `render.sh` does, so a portrait or tall card keeps its real `expectedHeight`.

Pass `routes` from `python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/routing.py"` so the loop honours `pipeline.json` instead of
inheriting the session model. Without it every agent silently runs on the session tier and the
cost design does nothing.

Gates come in three layers and only one costs anything: `gates/base.md` and
`gates/<format>.md` are static files, and the loop authors 3-6 artifact-specific gates per run.
A typical brief is 18 gates of which 12 are free.

It returns `{ converged, bestCandidate, bestScore, rounds[], escalationSuggested }`. Look at
`bestCandidate` yourself before shipping. `escalationSuggested` means two rounds stalled, which
is the one case worth paying the expensive tier for.

### 6. Animate (optional)

Two paths, same timing contract, so the animation is identical either way:

```bash
bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/render.sh"  <config.json> <base> <outdir>   # motion:true -> Playwright, quick
bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/animate.sh" <config.json> <base> <outdir>   # Remotion, frame-accurate
```

Reach for **Remotion** when you want to scrub timing live (`npx remotion studio`), sequence
several cards into one video, or add audio. It renders the same built HTML through the same
`data-s` / `data-d` / `data-count` / `data-wipe` attributes, so a new card format gets a
Remotion animation for free, with no React work. See [motion.md](motion.md).

Posting a video: upload the **MP4** as a video post and **set the custom thumbnail to the
PNG**. Frame 0 is the empty pre-animation state, so without a custom cover the still preview
looks blank.

### 7. Handoff (optional)

To keep tuning by hand, push the **gated** output into a design tool:

```bash
bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/handoff.sh" paper  <card.html> [outdir]
bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/handoff.sh" figma  <card.html> [outdir]
```

Both need an MCP server the plugin cannot install, so the script prepares the artifacts and
prints the remaining steps. Adapter gotchas that cost real debugging live in
[../../docs/paper-adapter-rules.md](../../docs/paper-adapter-rules.md).

**Only ever hand off gated output.** Authoring a card inside Paper or Figma skips the palette
check, the claims ledger and the loop, which is the entire point of having them.

### 8. Ship

Copy the finals somewhere permanent, never leave them in `/tmp`. Then say which file is the
deliverable and what it should be posted as.

---

## Cost and model routing

`pipeline.json` is the only file that names a model. Deterministic stages are free and always
run; only judgment pays.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/routing.py"                        # show the routing, and whether it is calibrated
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/routing.py" --report-cost u.jsonl  # price a usage log YOU recorded (log_usage)
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/calibrate.py" fixtures             # build the seeded-defect set
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/calibrate.py" run --apply          # pin the cheapest tier that catches them all
```

If `routing.py` prints `calibrated: NO`, the critic tier is an untested default rather than a
measurement. Say so rather than implying the tier was verified.

## Hard rules

- **No hardcoded brand.** Colours, typeface and footer come from `brand.json` through
  `brandkit`. A builder containing a literal hex is a bug, not a shortcut.
- **No em or en dashes in copy.** The gate greps for them. Use commas, periods, hyphens.
- **No fabricated numbers.** Use a directional arrow when direction is the point.
- **A brief describes mood, not palette.** "Earthy tones", "Builder's Journal feel" tells you
  the register. It does not authorise new colours. The only valid override is the user
  explicitly naming one after seeing a render.
- **A brief's footer text never overrides the locked footer.** A line like "Dana Reyes ·
  Revenue Architecture" in a brief is describing content, not brand.
- **Verify every render before shipping.** Read the PNG. Playwright's clipped
  element-screenshot path can paint a ghost duplicate of an image element at the wrong
  position; it is a Chromium bug, not a source bug, and only a look catches it.
- **Match content to an existing format before building.** Do not iterate through formats by
  rendering them.

## Related

Generated imagery (photoreal, illustration, text-inside-image) is not this pipeline's job.
This kit renders typographic, data-driven cards from structured config.
