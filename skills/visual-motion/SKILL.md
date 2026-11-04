---
name: visual-motion
description: >
  Animate a branded card into a feed-ready loop: master MP4 plus a LinkedIn GIF that
  fits the platform's pixel budget, rendered with Remotion (frame-accurate, scrubbable,
  parallel) or Playwright (quick). Requires a storyboard and a timing file before it will
  render, and asserts the loop seam and GIF budget deterministically.
  Use when asked to "animate this card", "make it move", "turn this into a video",
  "remotion", "video post", "make a looping GIF", or when a visual brief implies motion.
---

# Visual motion

Static cards come from [visual-pipeline](../visual-pipeline/SKILL.md). This skill is the
motion half. It shares that pipeline's brand, gate and claims ledger, and adds the three
things motion needs that a still does not: a design stage, a loop seam, and a pixel budget.

## Why there is a design stage at all

Motion fails differently from a still. A still is wrong in space; a loop is wrong in time,
and you cannot see it in a screenshot. So the timing is authored and reviewed as a document
*before* anything renders. `animate.sh` refuses to run without one, because "we will tune it
after we see it" is how six render cycles get spent on a decision that a paragraph would have
settled.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/storyboard.py" init <config.json>    # fill-in template, not a blank page
```

A storyboard states four things:

1. **Motion thesis** — one sentence on what the movement is *saying*. If the animation does
   not say anything the still does not, ship the still.
2. **Timing table** — second by second, what enters and what resolves.
3. **Motion rules** — what is banned for this piece. The house defaults: no decorative wipes,
   no zoom packs, no particles, no gradient sweeps, no spring overshoot. Movement earns its
   place by carrying meaning; everything else is noise that reads as template.
4. **Delivery targets** — master and GIF dimensions, fps, frame counts.

## The loop seam

**Frame 0 and the closing hold must be pixel-identical.** A loop that ends one pixel away from
where it started jumps on every repeat, and in a feed that repeat happens constantly. This is
checked, not eyeballed:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/motion-check.py" seam --video out/card-motion.mp4
```

## The GIF budget

LinkedIn caps a GIF by total pixels (width x height x frames) and file size. Over the cap it
gets re-encoded to mush or rejected. Checked **before** rendering:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/motion-check.py" budget --width 552 --height 690 --frames 94 --fps 15
```

The ceiling is 36,152,320 pixels and 5MB. A 4:5 master at 1080x1350 blows through it about
7.5x over, which is why the GIF is a **separate composition** with its own dimensions and
frame budget rather than a re-encode of the master:

| Output | Size | fps | Frames | Purpose |
|---|---|---|---|---|
| Master MP4 | 1080x1350 | 30 | ~188 | The feed video post |
| LinkedIn GIF | 552x690 | 15 | <=94 | Comments, DMs, cross-posting |

When the budget check fails it tells you the frame ceiling at your current dimensions, so the
fix is arithmetic rather than guesswork.

## Rendering

```bash
bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/animate.sh" <config.json> <basename> <outdir> [brand.json]
```

Two renderers, one timing contract, so the output is identical either way:

- **Playwright** (via `render.sh` with `motion: true`) — quick, no extra install.
- **Remotion** (`animate.sh`) — frame-accurate, renders frames in parallel, and gives you
  `npx remotion studio` to scrub the timeline while you tune. Reach for it when timing needs
  iteration, when several cards sequence into one video, or when audio is involved.

The contract is four data attributes the builders already emit with `--motion`:

| Attribute | Effect |
|---|---|
| `data-s` / `data-d` | fade and rise, start and duration in ms |
| `data-count` (+ `data-suffix`, `data-dec`) | count a number up to its value |
| `data-wipe` | width 0% to 100%, a reveal with no fade |

Because both renderers consume the same attributes, **a new card format gets a Remotion
animation for free**, with no React written. `remotion/src/Card.tsx` injects the built HTML and
drives those attributes off `useCurrentFrame()`.

One caveat that cost a real bug: `data-wipe` must also clear the `opacity: 0` that the motion
CSS puts on every `[data-s]` element. Returning early without it renders the bar permanently
invisible, which shipped silently in both renderers until a mid-frame extract caught it.

## Posting

Upload the **MP4** as a video post and **set the custom thumbnail to the PNG**. Frame 0 is the
empty pre-animation state, so a video with no custom cover previews as a blank card in the feed.

## Order of operations

1. `storyboard.py init` then edit it. Thesis first.
2. `motion-check.py budget` on the GIF spec, before rendering anything.
3. `animate.sh` to render master plus poster PNG.
4. `motion-check.py seam` on the master.
5. Taste Loop B, with the storyboard's motion rules folded into the artifact gates.
6. Ship: MP4 as the video post, PNG as its thumbnail, GIF for comments.

## Related

- [visual-pipeline](../visual-pipeline/SKILL.md) — the static half, brand, QA gate, claims
- `scripts/motion-check.py` — seam and budget, both with a two-sided self-test
- `remotion/src/Card.tsx` — the renderer bridge
