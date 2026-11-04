# Motion review, 2026-09-28: what charlie947/motion-graphics-skills does that we don't

> **STATUS 2026-10-01: everything below marked as a gap or bug is closed.** B1 = `render.sh` runs `motion-check.py seam-frames` (6579e31). B2 = `infographic-card.py check_loop_fits()` (6579e31). B3 = the duplicate closing frame is dropped before encoding (6579e31). Gaps 1-4 (morph, return, hold-life, ghost) = `motion_morph` / `motion_return` / `motion_live` (679e2b8). Gap 5 (uniform stagger) is NOT built: reverse exits stagger by a beat, entrances still use fixed steps. Variety is enforced by `motion-variety.py` (68ac510). The text below is the review as written on 2026-09-28.

Source: https://github.com/charlie947/motion-graphics-skills (13 Claude Code skills, 22 commits,
13 stars, last push 2026-09-27). Read in full: README, `skills/motion-effects/SKILL.md`,
`skills/motion-effects/references/effects.md` (16 recipes), `milestone-reveal`, `model-showdown`,
`loop-cover`, `brand-intake`. Author runs a 71k-reader newsletter; the pack is his own
production toolkit, not a vetted OSS library. Verdict: port ideas, do not install it.
Their skills build product-UI mockup videos (button to player, search to results, dashboard
zoom). Our pipeline builds brutalist text-and-data infographics. Different job.

Why this review happened: Anton, 2026-09-27, "the animation is the same on all the recent
posts". Every card since 2026-09-22 reads as: header, then blocks appearing top to bottom,
then a fade to empty.

## Their motion grammar in one table

| Phase | Their 8 s clock | Ours today |
|---|---|---|
| Start | frame 0 is the start state | frame 0 = static header + empty body (fixed 2026-09-27, b7b2bdf) |
| Move | 0.0-2.2 s: ONE object changes shape | 1-15 s: many objects APPEAR (rise/fade/scale/pop/unroll/type/blur) |
| Hold | 2.2-6.6 s: one small thing keeps moving | static; nothing moves once revealed (except the spine/cycle pen) |
| Return | 6.6-8.0 s: every element eases BACK to where it started | everything fades to opacity 0 at a hard-coded time |
| Loop | 8.0 == 0.0, measured | seam measured by hand this session; not gated in render.sh |

## Gaps, ranked by visible impact

1. **No morphs.** Their core rule: "premium means one object changing shape, never a fade
   from one thing to another". Every one of their 16 effects is a morph (bars into a line
   through their own tops, a tile growing from its exact position into a card). Every
   primitive in our runtime is an entrance: `scripts/motion-runtime.js:104` (FX table:
   left/right/scale/pop/unroll/type/blur) plus default rise. Nothing turns one shape into
   another. This is the single biggest reason all cards feel alike.
2. **No return phase.** We dissolve (`data-out`, `scripts/motion-runtime.js:190`) instead of
   easing elements back to their start state. Theirs reads as one continuous motion; ours as
   a build, then a cut to black-ish, then a restart.
3. **Dead holds.** "4.4 of the 8 seconds is the hold. If nothing moves in it, the loop feels
   dead." Our `decisions`/`sort`/`mega`/`flow` layouts have zero motion after the last
   element lands. The only hold-life we own is the `data-draw` pen + ring pulse, used by
   `spine`/`cycle` only.
4. **No ghost of the start state.** A faint outline left where a thing began lets the eye
   follow the change. We never draw one.
5. **Stagger is uniform.** They vary per element with real springs and different damping
   (spring stack). Ours is linear `n * 150ms` everywhere.

## Bugs this review surfaced in OUR pipeline (verified, with lines)

- **B1. The seam gate exists but is never called.** `scripts/motion-check.py:103`
  `check_seam()` has a two-sided self-test (clean passes, seeded break fails), but
  `scripts/render.sh:149-168` records lossless frames into `$FR`, encodes them and then
  `rm -rf "$FR"` without comparing frame 0 to the last frame. That is how
  `jev-infographic-claim-check` shipped a broken seam on 2026-09-27 with QA PASS: its
  `motion_ms` (11500) equalled `BL_DISSOLVE` (`scripts/infographic-card.py:566`), so the last
  captured frame preceded the fade-out. Caught only by a hand-rolled Playwright diff.
- **B2. Dissolve time is decoupled from `motion_ms` in 5 places.** `DISSOLVE_MS=13000`
  (`infographic-card.py:83`, spine), `CY_DISSOLVE=12000` (:370), `BL_DISSOLVE=11500` (:566),
  `MG_DISSOLVE=12000` (:781), flow computed at :1003. A config can set a `motion_ms` shorter
  than dissolve + 380 ms and nothing refuses it. Same bug class as B1, prevented at build
  time instead of detected at render time.
- **B3. Doubled loop frame.** `scripts/record.js:38-40` captures N+1 frames (t = 0 .. dur
  inclusive). When the seam is clean, frame N duplicates frame 0, so the MP4 holds that
  frame twice at every loop: a one-frame stall. Theirs samples [0, dur).

## Things worth taking outright

- **Frame-check protocol.** Capture at fixed phase points (start, mid-move, end of move,
  mid-hold, start of return, end) and require (a) first == last, (b) the move frames differ
  from each other (a stuck element shows up as two equal frames), (c) nothing clipped.
  Point (b) is new to us: we never assert that the animation actually moves.
- **Excursion metric** (loop-cover): the largest pixel change from frame 0 across all frames.
  Near zero means nothing visible moves. Pairs with the seam metric to make a two-sided
  motion gate: seam must be ~0, excursion must be above a floor.
- **Seed everything / load fonts before `seek(0)`.** We already do both (GSAP timeline is
  deterministic; fonts are embedded as @font-face via brandkit).

## New formats, backlog only (not fixes)

- `milestone-reveal`: ~3,200 seeded particles pulling into a real, sourced number. Fits a
  real milestone post (follower count, revenue). Trigger: Anton has a milestone to post.
- `model-showdown`: same brief to three models, first try each, stacked 1080x1920.
  Trigger: a post comparing three AI tools on one task.
- `chart morph` (effect 05): bars thin into a line through their own tops, values unchanged.
  Trigger: a post with a weekly series of real numbers.

## Not taking

The 16 UI-mockup effects themselves, `apple-launch-film`, `vox-explainer`,
`newsletter-promo`, `reel-export`: wrong shape for a single-frame LinkedIn infographic.
Trigger to revisit: Anton starts producing product-demo video (e.g. a gotomoney.io launch).
