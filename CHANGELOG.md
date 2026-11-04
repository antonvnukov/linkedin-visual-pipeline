# Changelog

## Unreleased

**Last two motion builders loop cleanly (2026-10-01).** `card-email` and `card-before-after` had no
fade-out, so the lossless seam gate (correctly) failed every motion render of them. Both now
dissolve before `motion_ms`, like bar and dashboard. Proof: the pre-fix email builder FAILS
`seam-frames`, the new one passes; both motion examples render in CI. Every motion-capable
builder now passes the seam gate.

**White-canvas frame completed for dashboard-card and email-card.** Same 1px
inset box-shadow in the theme `border` token as bar/quote/infographic (f51b084).
Verified: edge pixel (228,228,231) vs inner (255,255,255) on both, light theme.

**"mobile" opt-in mode on before-after, dashboard, email and flow cards
(unclaimed WIP, committed 2026-09-29 after review).** No session or transcript claimed
ownership; work was sitting uncommitted since 09-27/28 with no test coverage. Reviewed,
tested against real renders, and committed because it is additive and inert by default
(`cfg.get("mobile")`, old configs unchanged).

Verified: `before-after-card` and `email-card` mobile mode render clean and pass QA.
`dashboard-card` (paired with `"height": 1350` and a `<config>.qa.json` `expectedHeight`,
per the WIP's own comment) and `flow-card` (1080 square) both FAIL QA: the mobile footer
(60px avatar, 30px name/tagline) overflows the space left after the larger body content,
by ~33-50px. Not guessed at a fix for code I didn't write; left as an open item.

**Palette migrated to System A, white light canvas, red loss signal (2026-09-28, Anton D1-D3).**
`brand.json` had held the May-13 values (`#0F0F0F` / `#03D08C`) since Aug 18, missing the D7 and
System A decisions, and `brand-drift.py` enforced that inverted state. Now: dark `#18181B` /
`#00AD74`, light canvas pure `#FFFFFF`, `negative` token (`#B91C1C` light, `#F87171` dark) for
loss/before values only, fonts locked to Space Grotesk + Space Mono. `brand-drift.py` gained two
checks: a RETIRED value that is also live fails the run, and a ban list that bans a live value
fails. Dated rulings now travel in `DESIGN-BRIEF.md` under "Decisions".

**Motion variety gate (2026-09-28).** `motion-variety.py`, wired into `render.sh`: blocks a motion
card whose signature matches the last shipped one, warns after 3 cards with no never-used motion
option (layout excluded: five Jev cards changed layout and still moved alike), and `suggest`
names untried options plus a backlog of primitives to build. Two-sided self-test, both rules
mutation-tested, in CI.

**Motion grammar: return, hold-life, morph (2026-09-28).** New opt-in `card-infographic` keys:
`motion_return: "reverse"` (entrances play backwards, last in first out), `motion_live`
(ring pulse through the hold), and `motion_morph` (decisions: the abstain chip changes shape
into the first confidence band and back, with a ghost left behind; GSAP Flip, injected by
`record.js`). New report-only `motion-check.py dead-hold` (a 1.5s window changing under 0.2%,
the che-video-brain MOTION.md rule). Every pre-existing card fails it; the new example passes at
0.3%. 3 more seeded self-test cases. CI renders the example through the lossless seam gate.

**Loop seam is gated on every motion render (2026-09-28).** `render.sh` now runs
`motion-check.py seam-frames` on the lossless PNGs before encoding, and exits 1 on any
pixel difference between frame 0 and the frame at `motion_ms`. `check_seam()` had a self-test
but nothing called it, which is how claim-check shipped a jumping loop with QA PASS. That last
frame is then dropped (it duplicated frame 0, a one-frame stall on every loop).
`card-infographic` refuses a `motion_ms` that ends before its last dissolve (all 6 layouts,
12 seeded cases). New report-only `excursion` check flags a card that barely moves. The gate
found that `bar-card` and `dashboard-card` never dissolved, so their loops jumped. Both now
fade out before `motion_ms`. `before-after-card` and `email-card` have the same gap and are
left alone (another lane is editing them). CI renders `flow-card` and a must-fail
`seam-regression` fixture.

**`decisions` layout gains `motion_style: "headers_first"`** — a preview-beat entrance (all headers
land together, details cascade after) as an alternative to the default per-card cascade, so
consecutive decisions posts can read differently in the feed. 3 more seeded self-test assertions.

**Brutalist treatment + three gates born from defects that passed every gate (2026-09-17).**
`"treatment": "brutalist"` on carousel, flow and before-after (opt-in config key, brand layer
unchanged). Carousel slide types `versus`, `dotmatrix` (equal grids, deliberately not to scale),
`verdict`. New gates, each with a two-sided `--self-test`: `layout-check.py` (content fill and
top-edge drift measured on rendered PNGs, inset past the registration marks), `brand-drift.py`
(every `.md` inside a mirroring skill vs `brand.json`, `file:line` findings), `design-brief.py`
(generated, paste-able brief). `gate.sh` gained `[wrap]` and `[font]`, and the impeccable
detector now reads stderr (it had printed ok on flagged cards for weeks). Motion gate moved out
of static `card-flow`'s rubric; unknown formats throw instead of falling back to bar-card.
AGENTS.md rules 6-8.

**`card-infographic` gains layout `"mega"`** (dense 3-column cheat-sheet poster, typed / code /
human cards, legend required). 5 more seeded violations in the self-test (24 total).

**`card-infographic` gains layouts `"decisions"` and `"sort"`** (copyable reference sheets: typed
questions with the abstain option highlighted + confidence bands; a three-column sort table).
7 more seeded violations in the builder self-test (19 total).

**`card-infographic` gains layout `"cycle"`** (six steps on one hexagonal loop, pen draws the
ring and closes it, segments fill in turn, verbatim quote with mandatory source). Per-layout
allowed keys, 5 more seeded violations in the builder self-test (12 total). Spine output is
byte-identical (static PNG sha256 unchanged).

**New format: `card-infographic` (1080x1350).** A dense reference sheet: a three-cell spec
strip, 5 to 9 nodes on ONE serpentine path (each a name + a fix), a 0-1 threshold scale.
Unknown config keys fail loud; the scale refuses to render without a caption saying whose
thresholds they are. Builder carries a two-sided `--self-test` (7 seeded violations), in CI;
the example renders through `render.sh` in CI.

**Motion runtime: `data-draw` + per-card measured easing.** A path draws at constant speed with
a pen-tip marker (one pulse, while it moves); nodes land when the pen reaches them. A card can
carry `data-ease="x1,y1,x2,y2"` / `data-rise` so a MEASURED grammar (e.g. aimindset's
0.2,0.8,0.2,1, 16px rise) applies to that card only. The runtime solves the bezier itself
because GSAP core silently ignores `cubic-bezier(...)` strings; `motion-runtime-selftest.cjs`
proves it against an independent reference and catches a seeded wrong curve (in CI).
Fixed a real loop-seam break the lossless frame diff exposed: the draw path rendered a 1x2 px
sliver at its start on frame 0.

**Three silent passes closed.**
- `render.sh` emitted a GIF it never checked. The fixed 720px / 18fps GIF was over LinkedIn's
  pixel budget for EVERY motion card (a 5.5s card = 142%, a 14s infographic = 453%). It is now
  sized from the budget by `motion-check.py gif-spec` and asserted with `budget`; an oversized
  GIF fails the render.
- `gif_spec` under-counted frames by one (`round` vs the master's inclusive 0..N frames), so its
  own "compliant" spec shipped at 100.9%. Fixed, with a regression test that runs the real
  record-style master through ffmpeg and counts the frames it emits.
- `claims.py` read "1,200" as the figure "200", so a ledger had to vouch for a number the card
  never shows. Thousands separators after a one-digit lead now parse as one figure (tested).

Pre-existing, NOT fixed here (verified identical on a clean HEAD worktree): the
`quote-card` example renders a hero stat with no ledger, and `social-seo-carousel` fails the
portrait layout fill gate on slides 2, 4 and 6. Both make the CI render step red on main.

## 1.2.0

**The documented command now runs the machinery the README always claimed (P0-4).**
`render.sh` runs, in order: the claims ledger (a figure-bearing config refuses to render
without a verified `<config>.claims.json`), the palette/dash gate, and the QA assertion suite —
and the shipped PNG is copied out of the QA candidate itself, so artifact and evidence are the
same pixels. Carousels, previously ungated, gate against the union of both theme palettes.
The candidate directory is the taste loop's round-1 evidence bundle; nothing needs to run
`qa-visual` by hand. CI renders every example through `render.sh` instead of calling builders
directly. Example ledgers ship for the two figure-bearing examples.

**Four P1 integrity fixes.** Calibration's `--apply` now writes the `alias` the loop actually
routes on (it silently pinned nothing) and takes its tier/voter defaults from `pipeline.json`;
`--report-cost` docs state what really exists (a reporter you feed, not automatic measurement);
`gate.sh` gained a mutation-tested two-sided `--self-test` (in CI); Remotion now extracts and
executes the motion runtime embedded in the built HTML — the hand-synced copy in `Card.tsx` is
deleted, so the recorder and Remotion animate with literally the same code.

**Three defects the new CI step found within minutes of landing.** `brandkit`'s `structural`
token fell back to the *light* theme's accent, so every dark quote card rendered a hex its own
palette forbids; the quote mark carried a hardcoded `Georgia` (a literal font in a builder) and
overflowed its clipping ancestor. Fixed, with a brandkit assertion that every token in a theme
resolves to a hex legal in that theme.

**Repo shape.** `AGENTS.md` (with `CLAUDE.md` pointing at it) states the five rules and the
pre-commit battery for anyone changing the plugin — the repo is driven by agents and had no
contract for them. A social preview generated **by the pipeline itself** lives at
`assets/social-preview.png`, regenerable from its committed config.

**Honesty corrections.** `card-quote` is documented as static (its builder refuses `--motion`);
the 994,505-token cost figure carries its provenance; remaining open P1 items are listed in
`docs/AUDIT-2026-08.md` → Status.

## 1.1.0

**Agent Plugins 1.0.0 conformance.** The package previously had a manifest only at
`.claude-plugin/plugin.json` and no `$schema`. Under the spec that is two fatal errors: the
portable manifest must be at `plugin.json` in the plugin root (§4.1.2, §5.1), and a missing
required field means "clients MUST reject the plugin and MUST NOT discover or execute any of
its components" (§5.3). It loaded in Claude Code and would have loaded nowhere else.

- Added the portable root `plugin.json` with `$schema`, `homepage` and `repository`
- Kept `.claude-plugin/plugin.json` for Claude Code; `check-spec.py` now fails on drift between them
- Added `scripts/check-spec.py`, a two-sided validator for both the plugin and skills specs
- Added CI running every self-check, the spec audit, and a full render matrix
- Added `SECURITY.md` and this changelog

**Fixed: the skill doc described a pipeline that no longer existed.** `visual-pipeline/SKILL.md`
still advertised a two-tier "three-lens" taste critique after that design was replaced by
Taste Loop B, and five scripts (`claims.py`, `routing.py`, `setup.sh`, `handoff.sh`,
`calibrate.py`) were referenced by no skill or command. The skill is the only interface a model
reads, so an unreferenced script does not exist to an installed agent.

- Rewrote steps 4-8: mandatory claims ledger, Taste Loop B, handoff, cost and routing
- Resolved a trigger collision: both skills claimed "animate this card"; `visual-motion` owns motion now
- Added `docs/chaining.md` documenting the content-pipeline seam as a chain, not a dependency

## 1.0.0

Initial release: four card formats, deterministic QA gate, claims ledger, Taste Loop B,
Remotion motion with seam and GIF-budget assertions, Paper and Figma handoff.
