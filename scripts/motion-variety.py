#!/usr/bin/env python3
"""
motion-variety.py — never ship the same animation twice running; try something new regularly.

WHY: every Jev motion card through 2026-09-27 shipped one recipe (light, ease 0.2,0.8,0.2,1,
rise 16, build-then-dissolve) and Anton saw it: "the thing is not to use the same animation
always but try to be creative from time to time with new options" (2026-09-28).
format-variety.py already guards the COMPOSITION sequence; this guards the MOTION sequence.

Two rules, run by render.sh on every motion render:
  1. BLOCK  a motion signature identical to the last shipped motion card.
  2. WARN   when the last NOVELTY_EVERY cards all reused options already seen before:
            time to try something new (an unused value, or a primitive from BACKLOG).

  motion-variety.py check   <config.json>      rule 1 (exit 1) + rule 2 (stderr WARN)
  motion-variety.py record  <config.json>      append after a successful render
  motion-variety.py suggest                    what has never been used + what to build next
  motion-variety.py --self-test

Override a deliberate repeat: LV_ALLOW_REPEAT=1. Test renders: LV_NO_RECORD=1.
"""
import argparse, json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HISTORY = ROOT / ".motion-history.jsonl"
NOVELTY_EVERY = 3

# The motion options a config can set. Defaults = what a config gets when it says nothing.
AXES = {
    "layout":        "spine",
    "theme":         "light",
    "ease":          "house",
    "rise":          16,
    "motion_style":  "cascade",
    "motion_return": "dissolve",
    "motion_live":   False,
    "motion_morph":  False,
}

# Known option values per axis, so `suggest` can name what has never shipped.
MENU = {
    "layout": ["spine", "cycle", "decisions", "sort", "mega", "flow"],
    "theme": ["light", "dark"],
    "ease": ["house", "0.2,0.8,0.2,1", "0.45,0,0.2,1", "0.9,0,0.1,1"],
    "motion_style": ["cascade", "headers_first"],
    "motion_return": ["dissolve", "reverse"],
    "motion_live": [False, True],
    "motion_morph": [False, True],
}

# New primitives not built yet, from docs/motion-review-2026-09-28.md. When rule 2 fires
# and the menu is exhausted, build ONE of these instead of re-using a recipe.
BACKLOG = [
    "chart morph: bars thin into a line through their own tops (needs a real weekly series)",
    "masked type: the headline revealed through a moving mask, not a fade",
    "camera push: slow scale-in on the payoff block during the hold",
    "spring stack: cards land with per-element spring damping instead of one stagger",
    "particle reveal: seeded dots gather into the hero number (needs a sourced milestone)",
    "text-to-layout: the title's key word flies to its section header",
]


def signature(cfg):
    sig = {}
    for k, default in AXES.items():
        v = cfg.get(k, default)
        if k == "layout" and "layout" not in cfg:
            v = cfg.get("format", default)
        sig[k] = v
    return sig


def _load(path=None):
    p = pathlib.Path(path) if path else HISTORY
    if not p.is_file():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def novel_axes(sig, before):
    """MOTION axes whose value this card uses for the first time ever.

    Layout is excluded on purpose: five Jev cards each introduced a new layout and still
    all moved the same way, which is exactly what Anton saw.
    """
    return [k for k, v in sig.items() if k != "layout" and all(e["sig"].get(k) != v for e in before)]


def check(cfg, path=None):
    """(ok, problems, warnings)."""
    hist = _load(path)
    sig = signature(cfg)
    problems, warnings = [], []
    if hist and hist[-1]["sig"] == sig:
        problems.append(f"same motion as the last shipped card ({hist[-1].get('config')}): "
                        f"change at least one of {', '.join(AXES)}")
    recent = hist[-(NOVELTY_EVERY - 1):] if NOVELTY_EVERY > 1 else []
    stale_run = len(recent) == NOVELTY_EVERY - 1 and all(not e.get("novel") for e in recent)
    if stale_run and not novel_axes(sig, hist):
        warnings.append(f"{NOVELTY_EVERY} motion cards in a row with nothing new. Try: "
                        + "; ".join(suggest(path)[:3]))
    return not problems, problems, warnings


def record(cfg, config_name, path=None):
    p = pathlib.Path(path) if path else HISTORY
    hist = _load(path)
    sig = signature(cfg)
    if hist and hist[-1].get("config") == config_name and hist[-1]["sig"] == sig:
        return False                                  # re-render of the same card
    row = {"config": config_name, "sig": sig, "novel": novel_axes(sig, hist)}
    with p.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return True


def suggest(path=None):
    hist = _load(path)
    used = {k: {json.dumps(e["sig"].get(k)) for e in hist} for k in AXES}
    out = [f"never used: {k}={v}" for k, vals in MENU.items() for v in vals
           if json.dumps(v) not in used[k]]
    return out + [f"build new: {b}" for b in BACKLOG]


def _demo():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        h = pathlib.Path(td) / "h.jsonl"
        a = {"layout": "sort"}
        assert check(a, h)[0], "empty history passes"
        record(a, "a", h)
        ok, probs, _ = check(a, h)
        assert not ok and "same motion" in probs[0], "identical motion to the last card must fail"
        b = dict(a, theme="dark")
        assert check(b, h)[0], "one changed axis passes"
        assert record(b, "b", h) and not record(b, "b", h), "re-render of one card records once"
        c = dict(a, ease="0.9,0,0.1,1")
        record(c, "c", h)                              # novel ease
        # Two cards that reuse only known values, then a third: WARN.
        record(dict(a, theme="dark", ease="0.9,0,0.1,1"), "d", h)
        record(a, "e", h)
        _, _, warns = check(b, h)
        assert warns and "nothing new" in warns[0], f"a novelty drought must warn: {warns}"
        _, _, warns = check(dict(a, layout="decisions"), h)
        assert warns, "a new LAYOUT alone is not new motion"
        _, _, warns = check(dict(a, motion_morph=True, layout="decisions"), h)
        assert not warns, "a card with a first-ever option clears the drought"
        s = suggest(h)
        assert any("motion_morph=True" in x for x in s) and any(x.startswith("build new") for x in s)
    print("motion-variety OK (blocks identical motion, allows one changed axis, warns on a novelty drought, suggests)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for n in ("check", "record"):
        sub.add_parser(n).add_argument("config")
    sub.add_parser("suggest")
    a = ap.parse_args()
    if a.self_test or not a.cmd:
        _demo(); return
    if a.cmd == "suggest":
        print("\n".join(suggest())); return
    cfg = json.loads(pathlib.Path(a.config).read_text())
    name = pathlib.Path(a.config).stem
    if a.cmd == "record":
        record(cfg, name); return
    ok, probs, warns = check(cfg)
    for w in warns:
        print(f"  WARN [motion-variety] {w}", file=sys.stderr)
    if ok:
        return
    if os.environ.get("LV_ALLOW_REPEAT"):
        print("  motion-variety: repeat allowed by LV_ALLOW_REPEAT", file=sys.stderr)
        return
    for p in probs:
        print(f"  FAIL [motion-variety] {p}", file=sys.stderr)
    print("         Ideas: python3 scripts/motion-variety.py suggest", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
