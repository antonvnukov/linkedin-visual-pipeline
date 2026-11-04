#!/usr/bin/env python3
"""
format-variety.py — refuse to ship the same composition N times running.

WHY THIS EXISTS: over 2026-08-12..14, four of five shipped configs were
`card-flow`. Each choice was locally defensible and nobody was checking the
sequence, so three days of posts went out looking like one repeated template.
Anton spotted it; no gate did. The pipeline already gates palette, em dashes,
fonts, claims, loop seam and GIF budget. It gated every property of a single
card and nothing about the relationship between cards.

Composition is the thing that must vary. The SHELL must not: typeface, palette,
avatar and seed footer are the recognition asset, and a previous pass nearly
"fixed" repetition by proposing to strip them, which would have traded the brand
away to solve a scheduling problem.

  format-variety.py check  <format> [--limit 3]   exit 1 if it would make LIMIT in a row
  format-variety.py record <format>               append to the history
  format-variety.py show   [--n 10]               recent history
  format-variety.py --self-test

Override for a deliberate repeat: LV_ALLOW_REPEAT=1.
"""
import argparse, json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HISTORY = ROOT / ".format-history.jsonl"
KNOWN = ["card-bar", "card-dashboard", "card-flow", "card-before-after", "card-email", "card-quote", "card-infographic", "carousel"]
DEFAULT_LIMIT = 3


def _load(path=None):
    p = pathlib.Path(path) if path else HISTORY
    if not p.is_file():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def streak(entries, fmt):
    """How many times fmt appears consecutively at the END of history."""
    n = 0
    for e in reversed(entries):
        if e.get("format") == fmt:
            n += 1
        else:
            break
    return n


def check(fmt, limit=DEFAULT_LIMIT, path=None):
    entries = _load(path)
    run = streak(entries, fmt)
    would_be = run + 1
    if would_be < limit:
        return True, run, []
    # Suggest what has NOT been used recently, most-stale first.
    recent = [e.get("format") for e in entries[-8:]]
    unused = [f for f in KNOWN if f not in recent]
    stale = sorted({e.get("format") for e in entries} - {fmt},
                   key=lambda f: max((i for i, e in enumerate(entries) if e.get("format") == f), default=-1))
    return False, run, (unused + [s for s in stale if s not in unused])


def record(fmt, path=None, config=None):
    """Append a use. Re-rendering the SAME config is idempotent.

    This gate counts SHIPPED POSTS, not render invocations. Re-running render.sh
    on one config (a copy tweak, a gate fix, a failed first attempt) used to
    append a fresh row each time, so one card could manufacture its own
    three-in-a-row streak and block the next genuinely different card. A second
    DIFFERENT config of the same format still counts, which is the thing the
    gate actually exists to catch.
    """
    p = pathlib.Path(path) if path else HISTORY
    key = pathlib.Path(config).stem if config else None
    if key:
        entries = _load(path)
        if entries and entries[-1].get("format") == fmt and entries[-1].get("config") == key:
            return False
    row = {"format": fmt}
    if key:
        row["config"] = key
    with p.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return True


def _demo():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        h = pathlib.Path(td) / "h.jsonl"
        # Clean side: variety passes.
        for f in ["card-bar", "card-flow", "card-quote"]:
            record(f, h)
        ok, run, _ = check("card-flow", 3, h)
        assert ok, "a non-consecutive repeat must pass"
        assert run == 0, f"streak should be 0 after an intervening format, got {run}"

        # Dirty side: the real 2026-08 sequence must fail on the third.
        h2 = pathlib.Path(td) / "h2.jsonl"
        record("card-flow", h2)
        ok, run, _ = check("card-flow", 3, h2)
        assert ok, "two in a row is allowed"
        record("card-flow", h2)
        ok, run, alts = check("card-flow", 3, h2)
        assert not ok, "three in a row must fail"
        assert run == 2, f"expected streak 2, got {run}"
        assert alts, "a refusal must name alternatives, or it is just an obstacle"

        # A different format after a blocked streak clears it.
        record("card-quote", h2)

        # Re-rendering ONE config must not manufacture a streak, but a second
        # DIFFERENT config of the same format must still count.
        h3 = pathlib.Path(td) / "idem.jsonl"
        assert record("card-quote", h3, config="a.json") is True
        assert record("card-quote", h3, config="a.json") is False, "same config must not re-append"
        assert streak(_load(h3), "card-quote") == 1, "one config = one use"
        assert record("card-quote", h3, config="b.json") is True, "a different config counts"
        assert streak(_load(h3), "card-quote") == 2
        ok, _, _ = check("card-flow", 3, h2)
        assert ok, "one different card must clear the streak"
    print("format-variety OK (passes variety, blocks a 3-run, names alternatives, clears)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check"); c.add_argument("format"); c.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    r = sub.add_parser("record"); r.add_argument("format"); r.add_argument("--config", default=None)
    s = sub.add_parser("show"); s.add_argument("--n", type=int, default=10)
    a = ap.parse_args()

    if a.self_test or not a.cmd:
        _demo(); sys.exit(0)
    if a.cmd == "record":
        record(a.format, config=a.config); sys.exit(0)
    if a.cmd == "show":
        for e in _load()[-a.n:]:
            print(" ", e.get("format"))
        sys.exit(0)

    if os.environ.get("LV_ALLOW_REPEAT"):
        print(f"  format-variety: repeat allowed by LV_ALLOW_REPEAT ({a.format})")
        sys.exit(0)
    ok, run, alts = check(a.format, a.limit)
    if ok:
        return
    print(f"  FAIL [variety] '{a.format}' has shipped {run}x in a row; this would make {run + 1}.", file=sys.stderr)
    print(f"         Composition is what varies. The shell (font, palette, footer) never does.", file=sys.stderr)
    if alts:
        print(f"         Not used recently: {', '.join(alts[:4])}", file=sys.stderr)
    print(f"         Deliberate repeat: LV_ALLOW_REPEAT=1 bash scripts/render.sh ...", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
