# Motion

One timing contract, two renderers. The builders emit it, both renderers consume it, so a
new card format gets an animation for free.

## The contract

`--motion` tags elements with data attributes. Nothing else is needed to animate a format.

| Attribute | Effect |
|---|---|
| `data-s` / `data-d` | Fade + rise. Start and duration in ms; `data-d` defaults to 600. |
| `data-count` (+ `data-suffix`, `data-dec`) | Counts a number from 0 to its value while fading in. |
| `data-wipe` | Width 0% to 100%. A reveal, not a fade. |

Easing is `easeOutExpo` everywhere, and every element is a pure function of `t`. Nothing is
incremental, because both renderers seek frames out of order.

> A `data-wipe` element must set `opacity: 1` as well as width. The motion CSS puts
> `opacity: 0` on every `[data-s]`, so a wipe that only sets width stays invisible forever.
> This shipped broken for months: every animated bar card silently rendered without its bar.
> If you add a new attribute that early-returns, clear the opacity too.

## Renderer 1 — Playwright (`render.sh`, `motion:true`)

Seeks `window.render(t)` once per frame, screenshots, hands the frames to ffmpeg for MP4 +
GIF. Zero extra install beyond Playwright and ffmpeg. Use it for a single card, shipped now.

## Renderer 2 — Remotion (`animate.sh`)

```bash
cd remotion && npm install     # once
bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/animate.sh" <config.json> <base> <outdir> [brand.json]
```

`remotion/src/Card.tsx` fetches the built HTML out of `remotion/public/`, injects its styles
and markup, and applies the same contract off `useCurrentFrame()`. Same pixels, rendered
frame-accurately and in parallel.

Reach for Remotion when you want to:

- **Scrub timing live.** `cd remotion && npx remotion studio` gives a real timeline. Tuning
  `data-s` values blind against a 90-second re-render is miserable by comparison.
- **Sequence several cards** into one video with `<Series>` or `<Sequence>`.
- **Add audio**: a voiceover or a music bed under the card.
- **Render in parallel**, which matters once a video runs past a few seconds.

The composition reads `width`, `height` and `durationMs` from props, so square and portrait
both work without a second composition.

### Gotcha: nvm

An nvm-managed shell exports `node`, `npm` and `npx` as lazy-loading shell *functions* that
recurse until the shell gives up in a non-interactive context. `animate.sh` resolves the
binary by absolute path for exactly this reason. Do the same in anything you add.

### Fonts

`Card.tsx` awaits `document.fonts.ready` inside `delayRender` before the first frame is
captured. Without it the render bakes a fallback face into the opening frames, and it is
subtle enough to miss until it is published.

## Posting

Upload the **MP4** as a video post, and **set the custom thumbnail to the PNG**. Frame 0 is
the empty pre-animation state, so a video without a custom cover shows a blank still in the
feed. The GIF is for comments, DMs and X, not for the feed post.
