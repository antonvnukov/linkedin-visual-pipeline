#!/usr/bin/env python3
"""
claims.py — the honesty ledger for a visual.

A card that shows a number is making a claim. This file is where that claim gets
an id, a classification, a source, and a cap on how many times it may appear
prominently. The cap matters: the same statistic rendered twice reads as two
independent findings, which is a quiet way to overstate evidence.

Enforcement is arithmetic, not intention. qa-visual.cjs merges these caps into
its text-occurrence counts, so a violated cap fails the gate.

    python3 claims.py init <config.json> [-o out.claims.json]   # pre-filled draft
    python3 claims.py check <config.json> <claims.json>          # coverage check
    python3 claims.py figures <config.json>                      # list figures (for scripts)
    python3 claims.py                                            # self-check

`init` produces a DRAFT. Every claim lands as `unverified` with an empty source,
and `check` fails while any remain, so the ledger cannot be satisfied by
generating it. A human has to say where each number came from.
"""
import argparse
import json
import pathlib
import re
import sys

# A "figure" is anything that reads as evidence: percentages, multipliers,
# money, counts with a unit, and bare numbers of 2+ digits.
FIGURE = re.compile(
    r"""(?<![\w.])(
        \d[\d,]*(?:\.\d+)?\s?%           |   # 62.1%  42 %
        [$€£]\s?\d[\d,]*(?:\.\d+)?[KMB]? |   # $42,121  $1.2M
        \d[\d,]*(?:\.\d+)?\s?[×x]        |   # 3.2x
        \d[\d,]*(?:\.\d+)?\s?(?:K|M|B)\b |   # 1M  17K
        \d{1,3}(?:,\d{3})+(?:\.\d+)?      |   # 1,200  4,672 (a 1-digit lead must not
                                              #   leave "200" as the figure: 2026-09-22)
        \d{2,}[\d,]*(?:\.\d+)?               # 17871  188
    )""",
    re.VERBOSE,
)

CLASSIFICATIONS = ("primary", "secondary", "user-reported", "estimate", "unverified")

# Fields that are labels/structure rather than evidence. A number here is not a claim.
NON_CLAIM_KEYS = {
    "format", "theme", "motion", "motion_ms", "fps", "size", "font", "font_weights",
    "green_pct", "gray_pct",  # bar geometry, derived from the stat itself
    "range",                  # a time-window label ("Last 30 days"), not a finding
}


def walk_strings(obj, key=None):
    if isinstance(obj, str):
        # A `$`-prefixed key is config metadata by JSON convention ($schema,
        # $comment). It is never rendered, so a number inside it is not a claim.
        if key not in NON_CLAIM_KEYS and not (key or "").startswith("$"):
            yield key, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v, key)


# Fields that exist SOLELY to render a headline figure. Whatever lands here is a
# claim by construction, so the 2-digit floor that keeps prose readable does not
# apply: a quote card whose hero stat is "5" at 160px is making an evidentiary
# claim the size of the card, and FIGURE alone would let it through unledgered.
HERO_FIGURE_KEYS = {"stat", "bignum"}


def figures_in(config):
    """Every distinct figure the config will render, with the fields it came from."""
    found = {}
    for key, text in walk_strings(config):
        for m in FIGURE.finditer(text):
            found.setdefault(m.group(1).strip(), set()).add(key or "?")
        # A hero field carrying any digit at all counts, however short.
        if key in HERO_FIGURE_KEYS and text.strip() and any(c.isdigit() for c in text):
            found.setdefault(text.strip(), set()).add(key)
    return {k: sorted(v) for k, v in sorted(found.items())}


def init(config, artifact):
    figs = figures_in(config)
    return {
        "artifact": artifact,
        "visibleSources": False,
        "publicationBoundary": "TODO: one sentence on how this data may and may not be framed.",
        "sources": {},
        "claims": [
            {
                "id": re.sub(r"[^a-z0-9]+", "-", f.lower()).strip("-") or "claim",
                "classification": "unverified",
                "display": [f],
                "source": "",
                "allowedProminentOccurrences": {f: 1},
                "note": f"Appears in: {', '.join(fields)}. Replace classification and source.",
            }
            for f, fields in figs.items()
        ],
    }


def check(config, ledger):
    """Return (ok, problems). Every rendered figure must be covered and verified."""
    problems = []
    figs = figures_in(config)
    covered = {d for c in ledger.get("claims", []) for d in c.get("display", [])}

    for f, fields in figs.items():
        if f not in covered:
            problems.append(f"uncovered figure {f!r} (rendered from: {', '.join(fields)})")

    for c in ledger.get("claims", []):
        cid = c.get("id", "?")
        cls = c.get("classification")
        if cls not in CLASSIFICATIONS:
            problems.append(f"claim {cid!r}: classification {cls!r} not one of {CLASSIFICATIONS}")
        if cls == "unverified":
            problems.append(f"claim {cid!r}: still 'unverified' — a draft ledger does not satisfy the gate")
        src = c.get("source", "")
        if cls in ("primary", "secondary") and not src:
            problems.append(f"claim {cid!r}: {cls} claim needs a source key")
        if src and src not in (ledger.get("sources") or {}):
            problems.append(f"claim {cid!r}: source {src!r} is not defined in sources{{}}")
        for value, cap in (c.get("allowedProminentOccurrences") or {}).items():
            if not isinstance(cap, int) or cap < 1:
                problems.append(f"claim {cid!r}: occurrence cap for {value!r} must be a positive integer")

    if "TODO" in (ledger.get("publicationBoundary") or ""):
        problems.append("publicationBoundary is still the TODO placeholder")

    return (not problems), problems


def _demo():
    cfg = {
        "format": "card-bar",
        "stat": "62.1%",
        "headline": "of LLM citations come from blog pages",
        "note": "Across 1.2M answers and $42,121 of spend",
        "green_pct": 62.1,
    }
    figs = figures_in(cfg)
    assert "62.1%" in figs, figs
    assert "1.2M" in figs, figs
    assert "$42,121" in figs, figs
    assert not any(f == "62.1" for f in figs), "green_pct is layout geometry, not a claim"

    # A sentence-ending period is punctuation, not a decimal point.
    dot = figures_in({"body": "LinkedIn domain authority: 99. Company blogs don't get near that."})
    assert set(dot) == {"99"}, dot
    # A time window is a label, not a finding.
    assert figures_in({"range": "Last 30 days"}) == {}, "range must be a non-claim key"

    # A one-digit HERO stat is still a claim: it is the biggest thing on the card.
    assert "5" in figures_in({"stat": "5", "stat_label": "write-back paths"}), \
        "a single-digit hero stat must be caught"
    assert figures_in({"headline": "5 paths"}) == {}, \
        "a lone digit in PROSE must still be ignored, or every list number becomes a claim"
    assert figures_in({"stat": "up"}) == {}, "a non-numeric hero (arrow/word) is not a figure"
    # Config metadata is not rendered copy.
    assert figures_in({"$comment": "1280x640 canvas"}) == {}, "$-keys are metadata"
    # A thousands separator after a ONE-digit lead is one figure. The old regex read
    # "1,200 req/min" as the figure "200", so the ledger demanded a number the card
    # never shows (2026-09-22, card-infographic readout).
    assert set(figures_in({"readout": "1,200 req/min"})) == {"1,200"}, "1,200 must parse as one figure"
    assert set(figures_in({"x": "4,672 companies"})) == {"4,672"}, "4,672 must parse as one figure"
    assert "1280" in figures_in({"headline": "1280 users"}), "a real field still counts"

    draft = init(cfg, "demo")
    assert len(draft["claims"]) == len(figs)
    ok, probs = check(cfg, draft)
    assert not ok and any("unverified" in p for p in probs), "a generated draft must NOT pass"

    good = json.loads(json.dumps(draft))
    good["publicationBoundary"] = "Vendor-reported, not a controlled study."
    good["sources"] = {"vendor": "https://example.com/report"}
    for c in good["claims"]:
        c["classification"] = "secondary"
        c["source"] = "vendor"
    ok, probs = check(cfg, good)
    assert ok, probs

    missing = json.loads(json.dumps(good))
    missing["claims"] = [c for c in missing["claims"] if "62.1%" not in c["display"]]
    ok, probs = check(cfg, missing)
    assert not ok and any("uncovered figure" in p for p in probs), probs

    bad_src = json.loads(json.dumps(good))
    bad_src["claims"][0]["source"] = "nope"
    ok, probs = check(cfg, bad_src)
    assert not ok and any("not defined in sources" in p for p in probs), probs

    print("claims OK")
    print(f"  figures detected: {', '.join(figs)}")
    print("  draft ledger correctly fails until a human verifies each claim")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("init"); i.add_argument("config"); i.add_argument("-o", "--out")
    c = sub.add_parser("check"); c.add_argument("config"); c.add_argument("claims")
    f = sub.add_parser("figures"); f.add_argument("config")
    a = ap.parse_args()

    if a.cmd == "init":
        cfg_path = pathlib.Path(a.config)
        cfg = json.loads(cfg_path.read_text())
        led = init(cfg, cfg_path.stem)
        out = pathlib.Path(a.out) if a.out else cfg_path.with_suffix(".claims.json")
        out.write_text(json.dumps(led, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {out} ({len(led['claims'])} claim(s), all 'unverified')")
        print("Now: set each classification, add sources, write publicationBoundary.")
    elif a.cmd == "figures":
        # Machine-readable probe for render.sh: one figure per line, exit 0.
        # Non-empty output + no ledger file is how the render refuses to ship.
        for fig, fields in figures_in(json.loads(pathlib.Path(a.config).read_text())).items():
            print(f"{fig}  (from: {', '.join(fields)})")
    elif a.cmd == "check":
        cfg = json.loads(pathlib.Path(a.config).read_text())
        led = json.loads(pathlib.Path(a.claims).read_text())
        ok, probs = check(cfg, led)
        if ok:
            print(f"claims OK ({len(led.get('claims', []))} claim(s) covered and verified)")
        else:
            print(f"claims FAIL ({len(probs)} problem(s)):")
            for p in probs:
                print(f"  - {p}")
            sys.exit(1)
    else:
        _demo()


if __name__ == "__main__":
    main()
