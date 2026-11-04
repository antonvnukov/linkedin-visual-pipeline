#!/usr/bin/env python3
"""
design-brief.py — emit ONE portable file that another session can actually use.

The problem this solves: the design system currently lives in eight places and
several were wrong (2026-09-28: brand.json itself held the stale May-13 values for
six weeks, see brand-drift.py's CORRECTION note); `_visual-gen/CONTEXT.md` has a section headed "Design system
(locked)" where every value is stale; a design-system screenshot named CURRENT
carried a dark base the pipeline has never rendered. Meanwhile brand.json, the
only file the renderer actually reads, is gitignored and therefore travels
nowhere.

So this DERIVES the brief from brand.json instead of restating it. Every hex in
the output is read from the brand, never typed here - `--self-test` asserts
exactly that, so a hand-edited colour cannot survive a regeneration.

    python3 design-brief.py                 # write DESIGN-BRIEF.md
    python3 design-brief.py --self-test     # prove no hex is hand-typed

Use the output in whichever session you have:
  Claude Code   point at the file, skills load from ~/.claude/skills anyway
  claude.ai     upload it as Project Knowledge
  blind agent   paste it into the task body (no filesystem, no MCP, no memory)
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


def brand(path=None):
    return json.loads((pathlib.Path(path) if path else ROOT / "brand.json").read_text())


def strip_repo_refs(md):
    """Drop the section that names paths a blind agent cannot resolve."""
    i = md.find("## Live implementation")
    if i == -1:
        return md
    # Drop the implementation section AND the provenance footer: both name a
    # repository and a generator script the receiving agent cannot resolve, and
    # a path it cannot verify is what makes it stop rather than act.
    return md[:i] + ("*You do not have access to the repository this came from, and you do "
                     "not need it. Everything required is above. Apply it to what you are "
                     "building, and ask if something is missing.*\n")


def render(b, today=None):
    d, l = b["themes"]["dark"], b["themes"]["light"]
    f = b["font"]
    day = today or datetime.date.today().isoformat()
    rows = "\n".join(
        f"| `{k}` | `{l[k]}` | `{d[k]}` |"
        for k in ("canvas", "surface", "border", "text", "muted", "faint", "accent", "onAccent", "negative")
        if k in l and k in d
    )
    dec = b.get("decisions", {})
    decisions = ("## Decisions (Anton's rulings, dated)\n\n" + "\n".join(f"- **{k}:** {v}" for k, v in dec.items()) + "\n\n") if dec else ""
    return f"""# Design brief — {b['name']}

**READ THIS, APPLY IT, DO NOT EDIT IT.** It is a read-only reference, not a task.
Take the values below and apply them to whatever you are building. Nothing here
asks you to change this file or any file in the repository it came from.

**Scope: every visual surface for {b['name']}** - LinkedIn cards, dashboards,
internal tools, landing pages. It is not scoped to one repository. If you are
building an interface and you are not sure which colours or type to use, this is
the answer.

**If you were told to "update accordingly" and given only this file, that
instruction is incomplete.** Ask what should change. This file is the input, not
the target.

## Type

- Display and body: **{f['family']}**, weights {f['weights'].replace(';', ', ')}
- Mono: **{f.get('mono', 'none')}**, weights {f.get('monoWeights', '').replace(';', ', ')}

Mono is for labels, codes and readouts. Never for a formatted quantity: a
monospace face gives the thousands comma its own character cell, so `30,000`
renders as `30 , 000` and reads like a typo.

## Colour

| token | light | dark |
|---|---|---|
{rows}

Default theme: **{b['rules']['defaultTheme']}**.

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
6. **Two faces, locked.** {f['family']} and {f.get('mono', 'its mono')}. No third face
   on cards, not even for body text.

{decisions}## The brutalist treatment

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

*Provenance: generated from `brand.json` on {day} by `scripts/design-brief.py` in
the `linkedin-visuals` repository. The generator asserts every colour above is
read from the brand file, so this cannot drift from what actually renders. To
change a value, change `brand.json` and regenerate; editing this copy would be
overwritten and would not reach the renderer.*
"""


def _self_test():
    b = brand()
    out = render(b, today="2026-01-01")
    allowed = {v.upper() for t in b["themes"].values() for v in t.values() if HEX.fullmatch(v)}
    found = {h.upper() for h in HEX.findall(out)}
    stray = found - allowed
    assert not stray, f"hand-typed hex not present in brand.json: {sorted(stray)}"
    assert allowed & found, "brief emitted no brand colours at all"

    # seed a hand-typed colour and confirm the check catches it
    poisoned = out + "\n<!-- #BADBAD -->\n"
    seeded = {h.upper() for h in HEX.findall(poisoned)} - allowed
    assert seeded == {"#BADBAD"}, f"seeded hex must be caught, got {seeded}"

    assert "gradient" in out.lower(), "the no-gradient constraint must survive"

    paste = strip_repo_refs(out)
    assert "## Live implementation" not in paste, "paste mode must drop repo paths"
    assert "linkedin-visuals" not in paste, "paste mode must not name a repo the agent cannot see"
    assert allowed & {h.upper() for h in HEX.findall(paste)}, \
        "paste mode still has to carry the colours"
    assert "DO NOT EDIT IT" in paste, "paste mode keeps the apply-do-not-edit framing"
    print("design-brief OK")
    print(f"  passes:  {len(found)} colours, all read from brand.json")
    print("  catches: a hex that is not in the brand file")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand")
    ap.add_argument("-o", "--out", default=str(ROOT / "DESIGN-BRIEF.md"))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--paste", action="store_true",
                    help="print content for a blind agent task body (no repo paths)")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    md = render(brand(a.brand))
    if a.paste:
        print(strip_repo_refs(md))
        return
    pathlib.Path(a.out).write_text(md)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
