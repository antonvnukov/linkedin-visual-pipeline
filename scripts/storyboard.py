#!/usr/bin/env python3
"""
storyboard.py — the required design stage for motion.

    python3 storyboard.py init <config.json> [-o storyboard.md]
    python3 storyboard.py check <storyboard.md>

Motion fails in time, which a screenshot cannot show. Authoring the timing as a
document first is cheaper than discovering it over six render cycles. animate.sh
refuses to render without one, so this is a gate, not a suggestion.
"""
import argparse, json, pathlib, re, sys

TEMPLATE = """# {title} — motion storyboard

## Motion thesis

TODO: one sentence on what the MOVEMENT says that the still does not.
If you cannot finish this sentence, ship the still instead.

## Timing

- 0.00-0.60s: TODO opening state, readable on frame 0 (this is also the poster).
- 0.60-2.40s: TODO
- 2.40-4.40s: TODO
- 4.40-{dur}s: TODO resolve, then return to the exact opening state.

## Motion rules

- No decorative wipes, zoom packs, particles, gradient sweeps, or spring overshoot.
- Movement carries meaning; anything else reads as template.
- The layout stays spatially stable. Time resolves density, not rearrangement.
- Frame 0 and the closing hold are pixel-identical.

## Delivery targets

- Master: {w}x{h}, {fps} fps, {frames} frames, H.264 MP4.
- LinkedIn GIF: 552x690, 15 fps, at most 94 frames, under 5 MB, infinite loop.
- The GIF numbers keep it under LinkedIn's 36,152,320-pixel budget at 4:5.
"""

REQUIRED = ["## Motion thesis", "## Timing", "## Motion rules", "## Delivery targets"]


def check(text):
    problems = [f"missing section: {s}" for s in REQUIRED if s not in text]
    if "TODO" in text:
        n = text.count("TODO")
        problems.append(f"{n} TODO placeholder(s) remain — the storyboard is still a template")
    thesis = re.search(r"## Motion thesis\s*\n+(.+?)(?:\n\n|\n##)", text, re.S)
    if thesis and len(thesis.group(1).strip()) < 25:
        problems.append("motion thesis is too short to be a thesis")
    return (not problems), problems


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("init"); i.add_argument("config"); i.add_argument("-o", "--out")
    c = sub.add_parser("check"); c.add_argument("storyboard")
    a = ap.parse_args()

    if a.cmd == "init":
        p = pathlib.Path(a.config); cfg = json.loads(p.read_text())
        size = cfg.get("size", "square")
        w, h = (1080, 1350) if size == "portrait" else (1080, 1080)
        if isinstance(size, dict): w, h = int(size["w"]), int(size["h"])
        fps = int(cfg.get("fps", 30)); ms = int(cfg.get("motion_ms", 5500))
        out = pathlib.Path(a.out) if a.out else p.with_suffix(".storyboard.md")
        out.write_text(TEMPLATE.format(title=p.stem, w=w, h=h, fps=fps,
                                       frames=round(ms / 1000 * fps), dur=round(ms / 1000, 2)))
        print(f"wrote {out}")
        print("Fill in the thesis and timing. animate.sh will refuse while TODOs remain.")
    elif a.cmd == "check":
        ok, probs = check(pathlib.Path(a.storyboard).read_text())
        if ok:
            print("storyboard OK")
        else:
            print(f"storyboard FAIL ({len(probs)}):")
            for x in probs: print(f"  - {x}")
            sys.exit(1)
    else:
        # self-check: the template must NOT pass, a filled one must
        t = TEMPLATE.format(title="t", w=1080, h=1350, fps=30, frames=165, dur=5.5)
        ok, probs = check(t)
        assert not ok and any("TODO" in p for p in probs), "a fresh template must not pass"
        filled = t.replace("TODO: one sentence on what the MOVEMENT says that the still does not.\nIf you cannot finish this sentence, ship the still instead.",
                           "One system runs event after event, depositing reusable memory each time.")
        filled = re.sub(r"TODO[^\n]*", "the system idles, loaded and ready", filled)
        ok, probs = check(filled)
        assert ok, probs
        missing = filled.replace("## Motion rules", "## Rules")
        ok, probs = check(missing)
        assert not ok and any("missing section" in p for p in probs), probs
        print("storyboard OK (template rejected, filled accepted, missing section caught)")


if __name__ == "__main__":
    main()
