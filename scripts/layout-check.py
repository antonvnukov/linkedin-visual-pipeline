#!/usr/bin/env python3
"""
layout-check.py — does the content actually USE the canvas?

Every other gate in this repo judges what is ON the card: palette, dashes,
fonts, figures, overflow. None of them judges the space AROUND it, so a deck
whose content occupied 29% of a 1080x1350 frame passed every check and shipped
looking like a square block floating in a portrait canvas. The reader saw it
immediately; the pipeline could not see it at all.

Two measurements, both on the rendered PNGs, because this defect does not exist
in the DOM — it only appears once type has wrapped at a real size:

  fill    content height / available height (canvas minus footer). Too low and
          the slide reads as underfilled. No upper bound here: the overflow case
          is already covered by qa-visual's geometry checks.

  drift   spread of the FIRST content row across slides. A swipeable deck with a
          128px spread visibly jerks on every swipe even when each slide is fine
          alone. That is a whole-DECK property, so no single-card gate could
          ever have caught it.

    python3 layout-check.py <slides-dir> [--min-fill 45] [--max-drift 40]
    python3 layout-check.py --self-test
"""
import argparse
import pathlib
import sys

try:
    from PIL import Image
    import numpy as np
except ImportError:
    sys.exit("layout-check needs pillow + numpy (pip install pillow numpy)")

FOOTER_H = 88          # CSS px, portrait family
TOL = 20               # per-channel delta that counts as "not background"
# Content lives inside a 90px side padding. Anything outside that is FRAME, not
# content: corner registration marks sit at x=46 and x=1034 and are absolutely
# positioned at the live-area edges, so measuring full width let two ~100px
# decorative L-shapes define the first and last ink rows and report a fictional
# 94% fill on every slide of a deck. Measuring the content column only is what
# keeps this gate about content.
CONTENT_INSET = 80     # CSS px ignored on each side


def measure(png, scale=2, footer_h=FOOTER_H):
    """-> (top, bottom, fill_pct) in CSS px, or None for a blank frame."""
    a = np.asarray(Image.open(png).convert("RGB")).astype(int)
    bg = a[5, 5]
    diff = np.abs(a - bg).max(axis=2)
    w = a.shape[1]
    lo, hi = int(CONTENT_INSET * scale), int(w - CONTENT_INSET * scale)
    diff = diff[:, lo:hi]
    rows = np.where((diff > TOL).sum(axis=1) > 0)[0]
    if not len(rows):
        return None
    h = a.shape[0] / scale
    # Drop the footer band: it is pinned and identical on every slide, so
    # counting it would make an empty slide look 30% full.
    body = rows[rows / scale < h - footer_h - 4]
    if not len(body):
        return None
    top, bot = body[0] / scale, body[-1] / scale
    return top, bot, 100 * (bot - top) / (h - footer_h)


def check(slides_dir, min_fill=45.0, max_drift=40.0, scale=2, quiet=False):
    pngs = sorted(pathlib.Path(slides_dir).glob("slide-*.png"),
                  key=lambda p: int("".join(c for c in p.stem if c.isdigit()) or 0))
    if not pngs:
        return False, [f"no slide-*.png in {slides_dir}"]
    problems, tops = [], []
    for p in pngs:
        m = measure(p, scale)
        if m is None:
            problems.append(f"{p.name}: blank frame")
            continue
        top, _bot, fill = m
        tops.append(top)
        if fill < min_fill:
            problems.append(f"{p.name}: fill {fill:.0f}% < {min_fill:.0f}% "
                            "(content floats; raise the type scale or add a line)")
        if not quiet:
            print(f"  {p.name}: top {top:.0f}p  fill {fill:.0f}%")
    if len(tops) > 1:
        drift = max(tops) - min(tops)
        if not quiet:
            print(f"  top-edge drift across {len(tops)} slides: {drift:.0f}p")
        if drift > max_drift:
            problems.append(f"top-edge drift {drift:.0f}p > {max_drift:.0f}p "
                            "(content jumps on swipe; anchor the body, do not centre it)")
    return (not problems), problems


def _self_test():
    """Two-sided: must CATCH each seeded defect AND pass a clean control."""
    import tempfile
    W, H, S = 1080, 1350, 2

    def slide(path, top, height, bg=(15, 15, 15)):
        a = np.full((H * S, W * S, 3), bg, dtype=np.uint8)
        a[top * S:(top + height) * S, 100 * S:900 * S] = (255, 255, 255)
        a[(H - 60) * S:(H - 40) * S, 100 * S:300 * S] = (255, 255, 255)   # footer band
        Image.fromarray(a).save(path)

    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)

        good = d / "good"; good.mkdir()
        for i in (1, 2, 3):
            slide(good / f"slide-{i}.png", 124, 820)
        ok, probs = check(good, quiet=True)
        assert ok, f"clean control must PASS, got {probs}"

        thin = d / "thin"; thin.mkdir()          # the bug that actually shipped
        for i in (1, 2, 3):
            slide(thin / f"slide-{i}.png", 480, 370)
        ok, probs = check(thin, quiet=True)
        assert not ok and any("fill" in p for p in probs), f"must catch underfill, got {probs}"

        jump = d / "jump"; jump.mkdir()          # fine per-slide, jerks on swipe
        for i, t in enumerate((124, 250, 366), 1):
            slide(jump / f"slide-{i}.png", t, 800)
        ok, probs = check(jump, quiet=True)
        assert not ok and any("drift" in p for p in probs), f"must catch drift, got {probs}"

        blank = d / "blank"; blank.mkdir()       # must fail, not score 0% and pass
        Image.fromarray(np.full((H * S, W * S, 3), 15, dtype=np.uint8)).save(blank / "slide-1.png")
        ok, _ = check(blank, quiet=True)
        assert not ok, "a blank frame must fail"

    print("layout-check OK")
    print("  catches: underfill, top-edge drift, blank frame")
    print("  passes:  a well-filled, top-aligned deck")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slides_dir", nargs="?")
    ap.add_argument("--min-fill", type=float, default=45.0)
    ap.add_argument("--max-drift", type=float, default=40.0)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test or not a.slides_dir:
        return _self_test()
    ok, probs = check(a.slides_dir, a.min_fill, a.max_drift, a.scale)
    if ok:
        print("  ok   [layout]")
        return
    print(f"layout FAIL ({len(probs)} problem(s)):", file=sys.stderr)
    for p in probs:
        print(f"  - {p}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
