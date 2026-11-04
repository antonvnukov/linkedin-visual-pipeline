# Design brief — Anton Vnukov

**READ THIS, APPLY IT, DO NOT EDIT IT.** It is a read-only reference, not a task.
Take the values below and apply them to whatever you are building. Nothing here
asks you to change this file or any file in the repository it came from.

**Scope: every visual surface for Anton Vnukov** - LinkedIn cards, dashboards,
internal tools, landing pages. It is not scoped to one repository. If you are
building an interface and you are not sure which colours or type to use, this is
the answer.

**If you were told to "update accordingly" and given only this file, that
instruction is incomplete.** Ask what should change. This file is the input, not
the target.

## Type

- Display and body: **Space Grotesk**, weights 400, 500, 600, 700
- Mono: **Space Mono**, weights 400, 700

Mono is for labels, codes and readouts. Never for a formatted quantity: a
monospace face gives the thousands comma its own character cell, so `30,000`
renders as `30 , 000` and reads like a typo.

## Colour

| token | light | dark |
|---|---|---|
| `canvas` | `#FFFFFF` | `#18181B` |
| `surface` | `#FFFFFF` | `#27272A` |
| `border` | `#E4E4E7` | `rgba(255,255,255,0.09)` |
| `text` | `#18181B` | `#FFFFFF` |
| `muted` | `#71717A` | `#A1A1AA` |
| `faint` | `#A1A1AA` | `#52525B` |
| `accent` | `#047857` | `#00AD74` |
| `onAccent` | `#FFFFFF` | `#18181B` |
| `negative` | `#B91C1C` | `#F87171` |

Default theme: **dark**.

## Hard constraints

1. **No gradients.** The palette gate matches literal hexes against the list
   above, so a gradient's intermediate values fail it. A website design system
   may call gradients a signature element; fixed-canvas cards do not use them.
2. **No em or en dashes** in copy. Commas, periods and hyphens only.
3. **One accent.** Never two accents in one composition. `negative` is NOT a
   second accent: it marks loss, "before" and wrong-way values only, never
   decoration.
4. **`text-wrap: balance` on the card root.** It inherits, so one declaration
   covers every descendant. Without it a four-word chip orphans its last word.
5. **Every rendered figure needs a claim** in a `<config>.claims.json` ledger.
   A generated draft does not satisfy it; a human states where each number came from.
6. **Two faces, locked.** Space Grotesk and Space Mono. No third face
   on cards, not even for body text.

## Decisions (Anton's rulings, dated)

- **palette:** System A (Anton D1 2026-09-27; D7 2026-07-17 origin). Matches live gotomoney.io dark tokens.
- **lightCanvas:** White, not System A's off-white (Anton D3 2026-09-28: white reads cleaner and more brutalist).
- **accents:** ONE brand accent per composition. `negative` is a data signal for loss/before/wrong values only, never decoration (Anton D2 2026-09-28).
- **fonts:** Locked: Space Grotesk + Space Mono. No third face on cards (Anton D2 2026-09-28).

## The brutalist treatment

Opt in per config with `"treatment": "brutalist"` on a portrait carousel. Same
face, same palette, opposite posture: zero border radius, labels in mono inside
`[ brackets ]`, chips boxed in hairlines, corner registration marks, display
tracking at `-.05em`, hard white ground.

The vocabulary comes from the `industrial-brutalist-ui` skill. Read that skill
before extending this. Two deviations are deliberate:

- It mandates a red accent. The accent is a SLOT, and for these projects the
  slot holds the green pair above. Its real rule, one accent used sparingly, holds.
- It wants generous tracking on mono labels. Keep it. The `impeccable` detector
  calls that `wide-tracking`, which is the detector reading a short label as
  body copy.

## Live implementation

Repository `linkedin-visuals`. Builders in `scripts/`, format reference in
`skills/visual-pipeline/formats.md`, gates in `scripts/gate.sh` (palette, dashes,
wrap, font, impeccable) plus `claims.py`, `layout-check.py`, `format-variety.py`.
Each gate carries a two-sided `--self-test`.

---

*Provenance: generated from `brand.json` on 2026-09-28 by `scripts/design-brief.py` in
the `linkedin-visuals` repository. The generator asserts every colour above is
read from the brand file, so this cannot drift from what actually renders. To
change a value, change `brand.json` and regenerate; editing this copy would be
overwritten and would not reach the renderer.*
