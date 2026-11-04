#!/usr/bin/env python3
"""
gates.py — assemble the numbered gates a critic is graded against.

    python3 gates.py assemble --format card-bar [--motion] [--artifact extra.md] \\
                              [--evidence dir] [--round 1] [-o critic-brief-r1.md]
    python3 gates.py                                   # self-check

Three layers, and only one of them costs anything:

  1. base      gates/base.md        static, every artifact          free
  2. format    gates/<format>.md    static, one set per format      free
  3. artifact  3-6 gates for THIS piece, generated per run          one `author` call

That split is the whole reason the full protocol is affordable. Hand-writing a
12-gate brief per artifact is the right bar and the wrong ergonomics; nobody
does it twice. Two thirds of the brief is a file read.

The output is a blind critic brief: it names the frozen artifact, its checksum,
the evidence bundle, the numbered gates, and the verdict rules.
"""
import argparse
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GATES = ROOT / "gates"

VERDICT_RULES = """## Verdict

- Verify the checksum above before reviewing anything. If it does not match, stop and say so.
- Score out of 10.
- PASS only at 9.0 or higher AND with no high-severity issue.
- Report every gate as PASS or FAIL, by number.
- Separate required fixes from optional polish.
"""

BLIND_PREAMBLE = """Review this frozen candidate independently. Do not inspect source code, prior
candidate folders, previous verdicts, builder history, or chat history. Judge only the artifact
and the evidence listed below.
"""


def sha256(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def read_layer(name):
    p = GATES / f"{name}.md"
    if not p.is_file():
        return []
    # A gate may wrap over several lines. Taking only the first line silently
    # drops the actionable half (the "0.36x" arithmetic, the concrete threshold).
    out = []
    for line in p.read_text().splitlines():
        stripped = line.strip()
        if stripped and stripped[0].isdigit() and "." in stripped[:4]:
            out.append(stripped.split(".", 1)[1].strip())
        elif stripped and out and not stripped.startswith("#"):
            out[-1] += " " + stripped
    return out


def assemble(fmt, motion=False, artifact_gates=None, candidate=None, evidence=None, rnd=1, title=None):
    gates = read_layer("base") + read_layer(fmt)
    if motion:
        gates += read_layer("motion")
    gates += list(artifact_gates or [])

    lines = [f"# Independent review: {title or fmt} (round {rnd})", "", BLIND_PREAMBLE]

    if candidate:
        lines += ["## Frozen artifact", ""]
        for c in ([candidate] if isinstance(candidate, str) else candidate):
            lines.append(f"- `{c}`")
            lines.append(f"  - expected SHA-256: `{sha256(c)}`")
        lines.append("")

    if evidence:
        lines += ["## Evidence", ""] + [f"- `{e}`" for e in evidence] + [""]

    lines += ["## Gates", ""]
    lines += [f"{i}. {g}" for i, g in enumerate(gates, 1)]
    lines += ["", VERDICT_RULES]
    return "\n".join(lines), gates


def _demo():
    base = read_layer("base")
    assert len(base) >= 8, f"base gates missing: {len(base)}"
    bar = read_layer("card-bar")
    assert bar, "format gates missing"

    import tempfile, os
    with tempfile.NamedTemporaryFile("wb", suffix=".png", delete=False) as fh:
        fh.write(b"not-a-real-png-but-hashable")
        cand = fh.name

    brief, gates = assemble("card-bar", motion=False, artifact_gates=["The 62.1% figure matches the green segment exactly."],
                            candidate=cand, evidence=["qa-report.json", "feed-preview.png"], rnd=1, title="demo")
    assert len(gates) == len(base) + len(bar) + 1
    assert "expected SHA-256" in brief and sha256(cand) in brief
    assert "Do not inspect source code" in brief
    assert "PASS only at 9.0" in brief
    # gates are numbered contiguously from 1
    nums = [int(l.split(".")[0]) for l in brief.splitlines() if l[:1].isdigit() and ". " in l[:5]]
    assert nums == list(range(1, len(gates) + 1)), nums[:5]

    mbrief, mgates = assemble("card-bar", motion=True, candidate=cand)
    assert len(mgates) > len(gates) - 1 and "loop does not jump" in mbrief
    os.unlink(cand)

    print("gates OK")
    print(f"  base={len(base)}  card-bar={len(bar)}  +motion={len(read_layer('motion'))}")
    print(f"  a card-bar brief with 1 artifact gate = {len(gates)} numbered gates, "
          f"{len(base) + len(bar)} of them free")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("assemble")
    a.add_argument("--format", required=True)
    a.add_argument("--motion", action="store_true")
    a.add_argument("--artifact", help="markdown file of extra gates, one per numbered line")
    a.add_argument("--candidate", action="append", default=[])
    a.add_argument("--evidence", action="append", default=[])
    a.add_argument("--round", type=int, default=1)
    a.add_argument("--title")
    a.add_argument("-o", "--out")
    ns = ap.parse_args()

    if ns.cmd != "assemble":
        return _demo()

    extra = []
    if ns.artifact:
        for line in pathlib.Path(ns.artifact).read_text().splitlines():
            line = line.strip()
            if line and line[0].isdigit() and "." in line[:4]:
                extra.append(line.split(".", 1)[1].strip())
            elif line.startswith("- "):
                extra.append(line[2:].strip())

    brief, gates = assemble(ns.format, ns.motion, extra, ns.candidate or None,
                            ns.evidence or None, ns.round, ns.title)
    if ns.out:
        pathlib.Path(ns.out).write_text(brief + "\n")
        print(f"wrote {ns.out} ({len(gates)} gates: "
              f"{len(gates) - len(extra)} static, {len(extra)} artifact-specific)")
    else:
        sys.stdout.write(brief + "\n")


if __name__ == "__main__":
    main()
