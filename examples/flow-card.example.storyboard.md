# The stack that predicts timing — motion storyboard

## Motion thesis

The still shows four boxes; the motion shows a *filter*. Each layer only lights once
the one before it has resolved, so the viewer watches the funnel narrow rather than
reading a diagram of it. The card then dissolves and rebuilds, which says the thing
the post is actually arguing: this is an order you run every time, not a stack you own.

Motion personality: **Corporate** (che-motion-design). Decelerate on entrance, zero
overshoot, no bounce. Signature ease `power2.out`, which sits inside 0.3% of the
Material Design 3 standard curve at the midpoint.

## Timing

| Window | What happens |
|---|---|
| 0.00-0.56s | Eyebrow then title rise in. Chrome and footer are present from frame 0, so the brand never pops. |
| 0.42-0.76s | **01 Intent Signals** lands. The first layer is the only thing lit. |
| 0.70-0.94s | Connector to 02 draws. Secondary layer, shorter than the cards it joins. |
| 0.88-1.22s | **02 Validate Fit** lands. Read: fit is checked only now. |
| 1.16-1.40s | Connector down to 03. |
| 1.34-1.68s | **03 Enrich Contacts** lands. The narrowest, most expensive step, last. |
| 1.62-1.86s | Connector back to the payoff. |
| 1.80-2.42s | **04 One Per Layer** resolves on the accent tint. Longest beat of the piece: this is the argument. |
| 2.50-3.02s | Caption resolves. |
| 3.02-4.40s | Hold on the complete system. The only still anyone screenshots. |
| 4.40-4.78s | Everything dissolves together, accelerating out. |
| 4.78-5.20s | Empty hold, identical to frame 0, so the loop seam is clean. |

## Motion rules

- No decorative wipes, zoom packs, particles, gradient sweeps or spring overshoot.
- One property pair only: opacity plus an 18px rise. Nothing scales, nothing rotates.
- Layers light strictly in order. Never two nodes entering at once, or the gating
  claim the piece exists to make is contradicted by its own choreography.
- Connectors are secondary: shorter and quieter than the nodes they join.
- The dissolve is synchronised across every element. A staggered exit would read as
  a second story rather than a reset.
- Frame 0 and the closing hold must be pixel-identical.

## Delivery targets

- Master: 1080x1080, 30 fps, 156 frames, H.264 MP4.
- LinkedIn GIF: 540x540, 15 fps, at most 78 frames, under 5MB, infinite loop.
- Square keeps the GIF far inside LinkedIn's 36,152,320-pixel budget, so the loop
  survives without a re-encode.
