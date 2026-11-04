#!/usr/bin/env python3
"""
brand-drift.py — assert every hand-mirrored palette copy still matches brand.json.

Anton chose to keep the values inline in the skills rather than pointer-only. This
gate is the condition that makes that choice safe: a copy is allowed, but it has
to self-report the moment it diverges.

CORRECTION 2026-09-28. The first version of this gate had its RETIRED list
INVERTED. brand.json was last edited on Aug 18 with the May-13 values
(#0F0F0F / #03D08C), missing Anton's D7 ruling (2026-07-17) and the System A
lock (2026-09-14). So the gate called the live palette "retired" and passed the
stale one, and 54 "findings" were in fact correct copies. Nothing checked the
RETIRED list against the live brand, which is why `inverted_retired()` now
fails the run the moment a retired value is also a live one.

Decisions encoded here (brand.json "decisions" block): System A (D1), white
light canvas (D3), one accent plus a red `negative` data signal (D2).

    python3 brand-drift.py              # check the mirrors
    python3 brand-drift.py --self-test  # prove it catches a seeded regression
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = pathlib.Path.home() / ".claude/skills"

# Skills that deliberately MIRROR the personal-brand palette. a separate client
# brand book is excluded on purpose: its colours are its own.
#
# These are DIRECTORIES, not single files. The first version of this gate listed
# three SKILL.md paths and reported "3 mirrors match" while a live retired palette
# sat in che-linkedin-post-engine/agents/visual-designer.md — the palette is
# quoted in a skill's agents/, references/ and examples/ files too, and the agent
# prompt is the copy the runtime actually reads. Scanning the SKILL.md alone
# audited the table of contents and called it the book.
MIRROR_SKILLS = [
    SKILLS / "che-linkedin-visual",
    SKILLS / "che-linkedin-carousel",
    SKILLS / "che-linkedin-post-engine",
]


def mirrors():
    """Every .md inside a mirroring skill, SKILL.md first."""
    out = []
    for d in MIRROR_SKILLS:
        if not d.exists():
            out.append(d / "SKILL.md")        # surfaces as ": missing"
            continue
        out.append(d / "SKILL.md")
        out += sorted(f for f in d.rglob("*.md") if f.name != "SKILL.md")
    return out

# Values the personal brand used to carry. Any reappearance is drift, not history.
RETIRED = {
    "#03D08C": "May-13 Figma dark accent; System A dark accent is themes.dark.accent",
    "#0F0F0F": "May-13 dark canvas; System A is themes.dark.canvas",
    "#F8FBFF": "blue-tinted light canvas; light canvas is white (D3 2026-09-28)",
    "#F5F5F5": "System A off-white light canvas; replaced by white (Anton D3 2026-09-28)",
    "#0C0C0C": "May-13 light ink; use themes.light.text",
    "#6B6B6B": "May-13 light muted; use themes.light.muted",
    "#A0A0A0": "May-13 muted; use themes.dark.muted / themes.light.faint",
    "#E5E5E5": "May-13 light border; use themes.light.border",
    "#554E48": "brown dark faint; use themes.dark.faint",
    "#2D2926": "warm brown-grey from a stale design-system screenshot; never rendered",
}
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
HEADING = re.compile(r"^#{1,6}\s")
BAN_WORDS = re.compile(r"never use|banned|retired|superseded|deprecated", re.I)
POINTER = re.compile(r"correct\s*=|use instead|\u2192|->", re.I)


def live(brand=None):
    b = json.loads((pathlib.Path(brand) if brand else ROOT / "brand.json").read_text())
    return b["themes"]["dark"], b["themes"]["light"]


def inverted_retired(brand=None):
    """Retired values that are ALSO live brand values. Non-empty = the gate is
    enforcing the wrong direction (the 2026-09 inversion), so it must fail."""
    D, L = live(brand)
    live_hex = {v.upper() for th in (D, L) for v in th.values()
                if isinstance(v, str) and v.startswith("#")}
    return sorted(live_hex & {h.upper() for h in RETIRED})


def check(files=None, brand=None):
    D, L = live(brand)
    problems = []
    for h in inverted_retired(brand):
        problems.append(f"brand-drift.py: RETIRED lists {h}, which is a LIVE brand.json value "
                        "(the list is inverted; fix RETIRED, not the skills)")
    for f in (files if files is not None else mirrors()):
        if not f.exists():
            problems.append(f"{f}: missing")
            continue
        text = f.read_text()
        live_hex = {v.upper() for th in (D, L) for v in th.values()
                    if isinstance(v, str) and v.startswith("#")}
        ban_section = False
        for ln, line in enumerate(text.splitlines(), 1):
            # A markdown heading opens or closes a ban section. Hex lines start
            # with "#" too, but a heading is "#" runs followed by a SPACE.
            if HEADING.match(line):
                ban_section = bool(BAN_WORDS.search(line))
                continue
            hexes = [x.upper() for x in HEX.findall(line)]
            banning = ban_section or bool(BAN_WORDS.search(line))
            if banning:
                # In a ban entry, the hexes being banned are the first one on a
                # "X, correct = Y" line, or every one on a comma list. A LIVE
                # value there is the banned-AND-required contradiction (found
                # twice: che-linkedin-post-engine SKILL.md 2026-09-17, its
                # visual-designer agent 2026-09-28).
                banned = hexes[:1] if POINTER.search(line) else hexes
                for h in banned:
                    if h in live_hex:
                        problems.append(f"{f}:{ln}: bans {h}, which is a LIVE brand value")
                continue
            for h in set(hexes) & set(RETIRED):
                problems.append(f"{f}:{ln}: retired {h} ({RETIRED[h]})")
        # Only the SKILL.md is required to STATE the live accent. A reference or
        # example file legitimately discusses one slide and names no accent; the
        # retired-value scan above is what guards those.
        if f.name == "SKILL.md" and D["accent"].upper() not in text.upper():
            problems.append(f"{f}: mirrors the palette but never states the live "
                            f"dark accent {D['accent']}")
    return (not problems), problems


def _self_test():
    import tempfile
    D, L = live()
    with tempfile.TemporaryDirectory() as t:
        good = pathlib.Path(t) / "good.md"
        good.write_text(f"Dark accent `{D['accent']}`, canvas `{D['canvas']}`.\n")
        ok, probs = check([good])
        assert ok, f"a current mirror must PASS, got {probs}"

        bad = pathlib.Path(t) / "bad.md"
        bad.write_text(f"Dark accent `{D['accent']}`.\nUse #03D08C for the dark accent.\n")
        ok, probs = check([bad])
        assert not ok and any("#03D08C" in p for p in probs), f"must catch drift, got {probs}"
        assert any(":2:" in p for p in probs), f"finding must carry file:line, got {probs}"

        banned = pathlib.Path(t) / "banned.md"
        banned.write_text(f"Accent `{D['accent']}`.\nNever use #03D08C, it is retired.\n")
        ok, probs = check([banned])
        assert ok, f"an explicit ban is the CORRECT mention, got {probs}"

        # The accent-must-be-stated rule applies to a skill's SKILL.md, so the
        # fixture has to BE one. When the gate widened to whole skill dirs this
        # fixture was a plain good.md-style name and the assertion broke; the
        # fixture was wrong, not the rule.
        sd = pathlib.Path(t) / "silent-skill"; sd.mkdir()
        silent = sd / "SKILL.md"
        silent.write_text("Space Grotesk, no colours stated.\n")
        ok, probs = check([silent])
        assert not ok, "a SKILL.md that states no accent at all must fail"

        # ...and the companion case the widening exists FOR: a retired hex in a
        # non-SKILL.md file inside a mirroring skill must still be caught, even
        # though that file is not required to state the accent.
        ref = sd / "agents"; ref.mkdir()
        agent = ref / "visual-designer.md"
        agent.write_text("Slide 1: bg #0F0F0F, accent #03D08C.\n")
        ok, probs = check([agent])
        assert not ok and any("#03D08C" in x for x in probs), \
            f"must catch a retired hex in a skill's agents/ file, got {probs}"
        assert not any("never states the live" in x for x in probs), \
            f"a non-SKILL.md file must NOT be required to state the accent, got {probs}"
        sec = pathlib.Path(t) / "sec" ; sec.mkdir()
        s = sec / "SKILL.md"
        s.write_text(f"Accent `{D['accent']}`.\n\n### BANNED Colors\n```\n#03D08C   - old accent; correct = {D['accent']}\n#0F0F0F, #554E48\n```\n")
        ok, probs = check([s])
        assert ok, f"a code-block ban list under a BANNED heading is correct, got {probs}"
        s.write_text(f"Accent `{D['accent']}`.\n\n### BANNED Colors\n```\n#2D2926, {D['accent']}, #FAF8F5\n```\n")
        ok, probs = check([s])
        assert not ok and any("LIVE brand value" in x for x in probs), f"must catch banning the live accent, got {probs}"
        # The 2026-09 inversion: a RETIRED value that is the LIVE brand value must
        # fail the run. Seed a brand whose dark accent is a retired hex.
        inv = json.loads((ROOT / "brand.json").read_text())
        inv["themes"]["dark"]["accent"] = "#03D08C"
        invf = pathlib.Path(t) / "inverted-brand.json"
        invf.write_text(json.dumps(inv))
        assert inverted_retired(invf) == ["#03D08C"], inverted_retired(invf)
        ok, probs = check([good], brand=invf)
        assert not ok and any("inverted" in x for x in probs), f"must catch an inverted RETIRED list, got {probs}"
        assert inverted_retired() == [], f"live brand.json collides with RETIRED: {inverted_retired()}"
    print("brand-drift OK")
    print("  catches: a retired hex (incl. in a skill's agents//references/), a SKILL.md\n           with no live accent, missing file:line")
    print("  catches: a RETIRED list that names a LIVE brand value (the inversion)")
    print("  catches: a ban list that bans a LIVE brand value (banned AND required)")
    print("  passes:  a current mirror, and a line that explicitly BANS the old value")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    ok, probs = check(brand=a.brand)
    if ok:
        print(f"  ok   [brand-drift] {len(mirrors())} mirrored files match brand.json")
        return
    print(f"brand-drift FAIL ({len(probs)}):", file=sys.stderr)
    for p in probs:
        print(f"  - {p}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
