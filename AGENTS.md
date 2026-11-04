# Working on this repo

This file is for an agent **changing** the plugin. An agent **using** it reads
`skills/visual-pipeline/SKILL.md` instead — that is the interface, this is the contract.

Read `docs/how-it-works.md` before your first change: it explains why each stage exists, and
most bad changes here are ones that quietly delete a reason.

## What this is

A brief becomes a rendered social visual, and the rendering is checked hard enough to trust:
deterministic QA assertions, a claims ledger for every number on the card, and a blind
checksummed review loop. Colour, type and footer come from one `brand.json`; the plugin is
brand-agnostic by construction, not by convention.

## The rules

Every one of these exists because breaking it shipped a real bug.

1. **No literal hex, font name or footer string in a builder.** They come from `brand.json`
   through `brandkit`. The whole project exists because a service brand's font was a global
   default and leaked into personal work, invisibly, for months.
2. **Every check is two-sided.** A new check ships with a seeded defect it must catch AND a
   clean control it must pass, in a `--self-test` that runs in CI. A check that has never
   failed is not known to work. Mutation-test it: break the code, confirm the check goes red.
3. **`pipeline.json` is the only file that may name a model.** Not an argparse default, not a
   fallback string. Model ids and aliases both live there; `taste-loop.js` routes on `alias`,
   so anything writing a model must write the alias too.
4. **Verify the path a user takes, not the thing you built.** Every P0 in
   `docs/AUDIT-2026-08.md` came from testing a convenient proxy: `setup.sh` instead of
   `render.sh`, the refuses-early path instead of the happy path, the artboard root instead of
   the elements that actually draw glyphs.
5. **Test on `/bin/bash`, not your shell.** macOS ships bash 3.2.57 and nothing newer; Homebrew
   bash 5.3 shadows it in PATH and hides a whole class of failure. CI is Ubuntu and will not
   catch it either. `"${ARR[@]}"` on an empty array is fatal under `set -u` in bash < 4.4.
6. **A gate whose finding you never read is not a gate.** The impeccable detector was
   silently skipped for weeks: the vendor replaced `detect.mjs` with a CLI that writes every
   finding to STDERR and exits 2, leaving stdout empty, so `2>/dev/null` captured nothing and
   the wrapper printed `ok` on a card it had just flagged twice. Capture `2>&1`, grep the
   finding shape, and never let `|| true` supply a check's result. Same failure at the report
   layer: a blank `--self-test` table and a `checks: 0` nested under `audit.checks` were both
   cited as proof without being read.
7. **Measure the content column, not the canvas.** `layout-check.py` reported a fictional 94%
   fill on all 7 slides of a deck because the corner registration marks are absolutely
   positioned at the live-area edges, so two ~100px decorative L-shapes defined the first and
   last ink rows. A pixel-measuring gate must inset past every decorative frame element
   (`CONTENT_INSET`) or it measures the frame and calls it content.
8. **Assert the SHAPE of each generated CSS property, not just its value.** A property name
   injected into another property's *value* is syntactically valid, renders silently wrong and
   passes every value-matching gate: `font-family:text-wrap:balance;'Space Grotesk'` swapped
   every headline to a system serif while palette, dash, claims and QA all stayed green. A
   `font-family` value can never contain a colon — that assertion is now the `[font]` gate.
   Corollary: `text-wrap` inherits, so declare it once on the card root, never per element.

9. **A gate that runs on one path is not a gate on the other.** `qa-visual.cjs` holds
   `no-ancestor-clipping`, and `render.sh` branches to the carousel builder at line 92 and
   exits before reaching it at line 136 — so no deck has ever been clipping-checked. Chips
   overflowed the frame on slide 2 of a shipped carousel and Anton caught it in a screenshot;
   an ad-hoc checker written afterwards found three more (`.pbignum` heroes bleeding off the
   left: `position:absolute;right:60px;font-size:460px` fits about four characters, and
   `$0.0004` bled 741px). Before adding a gate, enumerate every branch of `render.sh` that
   produces an artifact and wire it into each one.
10. **A gate's ground-truth FILE needs the same live-artifact check its findings do.**
    `brand-drift.py` (rule 6's own fix) ran correctly for 11 days while enforcing the WRONG
    palette, because `brand.json` itself held stale values the gate never thought to question
    — it checked the skills against the file, never the file against anything. Caught by
    checking the live deployed site, not by the gate. Any check whose correctness depends on
    a local file being current needs a periodic or edit-triggered re-validation against the
    real thing that file claims to describe, not just internal self-consistency.
10. **Variety means every axis the viewer perceives, not the axis you measured.**
   `format-variety.py` compares FORMAT. Seven visuals shipped in one session were seven
   different formats, all portrait-square, all the same treatment, and it passed — Anton's
   reply was "why is everything in one format and the old design". The gate's own docstring
   already records this exact class happening before: "Anton spotted it; no gate did." A
   variety check must measure format AND aspect ratio AND treatment.
11. **An unknown config key must fail loud, never be dropped.** `formats.md` documents
   `eyebrow`/`subtext` on a hook slide; `carousel-card.py:241-244` reads `kicker`/`subhead`.
   Copy added under the documented names was silently discarded, so a fill-rate "fix" moved
   27% to 27% and looked like a layout problem. Two fixes, both needed: validate config keys
   against the builder's reader and reject unknowns, and assert in CI that every field name in
   `formats.md` appears in the builder that claims to read it.
12. **A format signifies an argument; read what it MEANS before picking it by slot count.**
   `card-before-after` renders its left column struck-through as the thing being retired.
   Four real, live SEO artifacts placed there turned a positive claim into a confession of
   failure. Nothing in the pipeline can catch this — it is the one check that stays human.

## Before you commit

```bash
python3 scripts/check-spec.py              # Agent Plugins 1.0.0 conformance + manifest drift
python3 scripts/check-spec.py --self-test
bash    scripts/gate.sh --self-test
node    scripts/qa-visual.cjs --self-test
python3 scripts/motion-check.py
python3 scripts/layout-check.py --self-test    # canvas fill + whole-deck top-edge drift
python3 scripts/brand-drift.py  --self-test    # hand-mirrored palettes still match brand.json
python3 scripts/design-brief.py --self-test    # no hex in the brief that is absent from brand.json
for c in brandkit routing claims storyboard gates calibrate; do python3 scripts/$c.py; done
/bin/bash scripts/render.sh examples/bar-card.example.json v /tmp/v   # the documented command
```

The last line is the one that matters most: it is what a stranger runs, and it must print
`claims OK`, three gate `ok` lines and `QA PASS` before it writes a PNG.

## Layout

| Path | What lives there | Watch out |
|---|---|---|
| `scripts/` | builders, gates, QA, motion, routing | `render.sh` is the documented entry point; anything it does not call is invisible to users |
| `skills/` | the only surface an installed agent reads | a script referenced by no skill effectively does not exist |
| `commands/` | `/visual`, `/animate` | Claude Code only; the spec ignores `commands/`, deliberately |
| `gates/` | static critic gates (base + per-format) | free layer of the review; artifact-specific gates are authored per run |
| `remotion/` | self-contained Remotion project | consumes the runtime the built HTML embeds — never re-implement the timing contract here |
| `plugin.json` + `.claude-plugin/plugin.json` | portable and Claude Code manifests | two on purpose; bump **both**, `check-spec.py` fails on drift |

## Adding things

**A card format.** New builder in `scripts/`, a `case` in `render.sh` and `animate.sh`, a row in
`formats.md` and the SKILL table, and a gate file in `gates/`. Emit the `data-s` / `data-d` /
`data-count` / `data-wipe` attributes and the motion runtime and it animates in both renderers
with no React work. If it cannot animate, say so in the docs rather than implying it can
(`card-quote` is static and documented as static).

**A check.** Put it in code, not in a prompt — code is free, so it runs on every artifact
forever, and that is the entire cost design. Two-sided, in CI, with the failure message naming
the file and the fix.

**A doc claim.** Only write what you exercised. "Verified" means you ran it under the conditions
a stranger would, and can say which command produced which artifact.

## Releasing

Bump `plugin.json` and `.claude-plugin/plugin.json` together, add a CHANGELOG section, tag
`vX.Y.Z` and cut a release. Version pinning is why a marketplace exists; a plugin stuck on one
version tells clients nothing ever changed.
