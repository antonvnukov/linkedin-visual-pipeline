#!/usr/bin/env python3
"""
fetch-fonts.py — cache a brand's webfont locally so rendering is deterministic.

Why this exists. The builders used to pull the family with an `@import` from
Google Fonts. That puts a network fetch, and a SECOND async hop for the
@font-face rules the import brings in, inside the render path. Remotion captures
frames across several browser tabs, and on a cold tab the early frames were
rasterised in the fallback face. The glyphs look near identical to Space Grotesk
at chrome size, but the line-box metrics differ, so the whole window-chrome row
shifted about a pixel partway through the video and the header appeared to jump
on every loop. It reproduced on roughly two runs in three, which reads as flaky
encoder noise until you diff the frames.

Cached files turn the font into a build input instead of a runtime race.

  python3 fetch-fonts.py                 # family and weights from brand.json
  python3 fetch-fonts.py --family "Inter" --weights 400,700

Writes assets/fonts/<Family-slug>-<weight>.woff2. brandkit.font() picks them up
automatically and emits base64 @font-face rules; with no cache it falls back to
the old @import, so this is additive.
"""
import argparse, pathlib, re, sys, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"
# Google serves woff2 only to browsers that advertise support.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
# The latin subset carries ASCII. Cards are latin-only; pulling every subset
# would quadruple the base64 for glyphs no card renders.
LATIN_MARKER = "U+0000-00FF"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def slug(family):
    return re.sub(r"[^A-Za-z0-9]+", "-", family).strip("-")


def fetch(family, weights):
    q = family.replace(" ", "+")
    css = get(f"https://fonts.googleapis.com/css2?family={q}:wght@{';'.join(weights)}&display=swap").decode()
    blocks = re.findall(r"@font-face\s*\{[^}]*\}", css)
    if not blocks:
        raise SystemExit(f"no @font-face returned for {family}; is the family name right?")
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for b in blocks:
        w = re.search(r"font-weight:\s*(\d+)", b)
        u = re.search(r"url\((https[^)]+\.woff2)\)", b)
        rng = re.search(r"unicode-range:([^;]+);", b)
        if not (w and u and rng and LATIN_MARKER in rng.group(1)):
            continue
        if w.group(1) not in weights:
            continue
        out = FONT_DIR / f"{slug(family)}-{w.group(1)}.woff2"
        out.write_bytes(get(u.group(1)))
        written.append(f"{out.name} ({out.stat().st_size // 1024}KB)")
    if not written:
        raise SystemExit(f"matched no latin faces for {family} at weights {weights}")
    for line in written:
        print("  cached", line)
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family")
    ap.add_argument("--weights", help="comma separated, e.g. 400,500,600,700")
    ap.add_argument("--brand")
    a = ap.parse_args()
    brand = brandkit.load(a.brand)
    family = a.family or brand.get("font", {}).get("family", "Space Grotesk")
    weights = (a.weights.split(",") if a.weights
               else brand.get("font", {}).get("weights", "400;700").replace(";", ",").split(","))
    weights = [w.strip() for w in weights if w.strip()]
    print(f"caching {family} {weights} -> {FONT_DIR}")
    fetch(family, weights)
    print("done. Builders will now embed the font instead of importing it.")


if __name__ == "__main__":
    main()
