#!/usr/bin/env python3
"""
font-leak.py — the brand must be the ONLY source of type.

Scans every rendered .html under a directory, collects the first family named in
each `font-family:` declaration, and fails if any is not one of the brand's
families (brandkit font + mono).

Replaces a CI one-liner that counted Google Fonts `family=` URL params. Once the
fonts were committed and embedded as @font-face (brandkit._cached_faces), no
render carries a `family=` param at all, so that line returned 0 against an
expected 1 in EVERY environment. It never ran in CI (an earlier example failed
first), so nobody saw it could not pass (2026-09-22).

Usage:
  python3 scripts/font-leak.py <render-dir> [--brand brand.json]
  python3 scripts/font-leak.py --self-test
"""
import argparse, pathlib, re, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit

DECL = re.compile(r"font-family:\s*['\"]?([A-Za-z][A-Za-z0-9 \-]*?)['\"]?\s*[,;}]")


def families_in(root):
    found = {}
    for f in sorted(pathlib.Path(root).rglob("*.html")):
        for m in DECL.finditer(f.read_text(errors="ignore")):
            found.setdefault(m.group(1).strip(), f)
    return found


def allowed(brand_path):
    B = brandkit.load(brand_path)
    fam = brandkit.font(B, {})[0]
    mono = brandkit.mono(B)[0]
    # generic CSS fallbacks are not a leak: they only apply if the brand face fails
    return {fam, mono} - {None, ""} | {"sans-serif", "serif", "monospace", "system-ui"}


def check(root, brand_path):
    ok = allowed(brand_path)
    found = families_in(root)
    if not found:
        return False, [f"no font-family declarations found under {root}: nothing was checked"]
    bad = [f"{name!r} in {path}" for name, path in found.items() if name not in ok]
    return not bad, bad


def self_test():
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        fam = brandkit.font(brandkit.load(None), {})[0]
        (d / "a.html").write_text(f"<style>@font-face{{font-family:'{fam}';}} p{{font-family:'{fam}',sans-serif;}}</style>")
        ok, probs = check(d, None)
        assert ok, f"clean render must pass: {probs}"
        (d / "b.html").write_text("<style>p{font-family:Helvetica,sans-serif;}</style>")
        ok, probs = check(d, None)
        assert not ok and "Helvetica" in probs[0], f"seeded leak must fail: {probs}"
        empty = d / "empty"; empty.mkdir()
        ok, probs = check(empty, None)
        assert not ok, "an empty render dir must not pass as clean"
    print("PASS font-leak self-test (clean passes, seeded Helvetica leak caught, empty dir refused)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?")
    ap.add_argument("--brand")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.root:
        ap.error("render dir required (or --self-test)")
    ok, probs = check(a.root, a.brand)
    if ok:
        print(f"font-leak OK: only brand faces in {a.root}")
        return
    print("FAIL [font-leak]\n  - " + "\n  - ".join(probs), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
