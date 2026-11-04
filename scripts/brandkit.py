#!/usr/bin/env python3
"""
brandkit.py — the one place the pipeline learns what a brand looks like.

Every builder imports this instead of hardcoding hexes, fonts or a footer.
Swap brand.json and every format re-skins. Resolution order for the brand file:

  1. --brand / LV_BRAND env var
  2. ./brand.json in the current working directory
  3. <plugin>/brand.json
  4. <plugin>/brand.example.json   (so a fresh clone renders something)

Run directly for a self-check:  python3 brandkit.py
"""
import html
import base64
import json
import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _candidates(explicit=None):
    if explicit:
        yield pathlib.Path(explicit).expanduser()
    if os.environ.get("LV_BRAND"):
        yield pathlib.Path(os.environ["LV_BRAND"]).expanduser()
    yield pathlib.Path.cwd() / "brand.json"
    yield ROOT / "brand.json"
    yield ROOT / "brand.example.json"


def load(explicit=None):
    """Return (brand_dict, path_it_came_from)."""
    for p in _candidates(explicit):
        if p.is_file():
            brand = json.loads(p.read_text())
            brand.setdefault("_path", str(p))
            brand.setdefault("_dir", str(p.parent))
            return brand
    raise SystemExit("brandkit: no brand.json found. Copy brand.example.json to brand.json.")


# ---------------------------------------------------------------- colour utils

def _rgb(hex_or_rgba):
    """(r,g,b) from #RGB / #RRGGBB. Returns None for rgba()/named values."""
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", hex_or_rgba.strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tint(color, alpha):
    """Same hue at `alpha` opacity. Falls back to the input if it isn't a hex."""
    rgb = _rgb(color)
    if rgb is None:
        return color
    return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha})"


def is_dark(color):
    rgb = _rgb(color)
    if rgb is None:                      # rgba() overlays only appear on dark surfaces here
        return True
    r, g, b = rgb
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


# ---------------------------------------------------------------- theme tokens

def theme(brand, name):
    """Expand the 8 brand tokens into every key the card builders reference."""
    t = brand["themes"][name]
    accent, canvas = t["accent"], t["canvas"]
    dark = is_dark(canvas)
    return {
        # raw passthrough
        "canvas": canvas, "text": t["text"], "sub": t["muted"], "accent": accent,
        "window": t["surface"], "win_border": t["border"], "chrome_border": t["border"],
        "dot": t["faint"] if dark else "#C0C0C0",
        "title": t["text"],
        # pills
        "pill_fg": t["muted"], "pill_bg": "transparent" if dark else canvas,
        "pill_border": t["border"],
        # stacked-bar segments
        "green_bg": accent, "green_fg": t["onAccent"],
        "gray_bg": t["faint"], "gray_fg": t["text"] if dark else t["text"],
        # accent-tinted note surface
        "note_bg": tint(accent, 0.08 if dark else 0.05),
        "note_border": tint(accent, 0.22 if dark else 0.20),
        # depth + footer
        "win_shadow": "none" if dark else
                      f"0 2px 4px {tint(t['text'], 0.02)}, 0 20px 48px {tint(t['text'], 0.06)}",
        "foot_border": t["border"],
        "avatar_ring": tint(t["text"], 0.12) if not dark else tint(t["muted"], 0.7),
        # dashboard tiles, range pill, accent islands, sparkline fill
        "range_fg": t["muted"], "range_bg": "transparent" if dark else canvas,
        "range_border": tint(t["text"], 0.14) if dark else t["border"],
        "tile_bg": tint(t["text"], 0.04) if dark else t["surface"],
        "tile_border": tint(t["text"], 0.08) if dark else t["border"],
        "tile_shadow": "none" if dark else
                       f"0 1px 2px {tint(t['text'], 0.02)}, 0 10px 24px {tint(t['text'], 0.04)}",
        "island_bg": tint(accent, 0.12 if dark else 0.08),
        "spark_fill": tint(accent, 0.12 if dark else 0.08),
        # aliases so every builder speaks one vocabulary
        "bg": canvas,
        "border": t["border"],
        "on_accent": t["onAccent"],
        "chip": tint(t["text"], 0.05) if dark else t["surface"],
        "hairline": tint(t["text"], 0.10) if dark else t["border"],
        "muted": t["faint"],
        # A theme's fallback must come from ITS OWN palette. Falling back to the
        # light accent gave every dark card a hex the dark palette forbids — the
        # cross-route colour borrow this whole project exists to prevent.
        "structural": t.get("accentDeep", accent),
        "surface": tint(t["text"], 0.04) if dark else t["surface"],
        "surface_border": tint(t["text"], 0.08) if dark else t["border"],
    }


def _cached_faces(family, weights):
    """Base64 @font-face rules from assets/fonts, or '' when nothing is cached.

    Embedding beats importing because it removes the network, and the second
    async hop for the imported @font-face rules, from the render path. With the
    @import, Remotion rasterised early frames on a cold tab in the fallback face;
    the glyphs look almost identical at chrome size but the line-box metrics do
    not, so the whole window-chrome row shifted a pixel partway through the video
    and the header looked like it jumped on every loop. Populate the cache with
    scripts/fetch-fonts.py.
    """
    import base64
    font_dir = pathlib.Path(__file__).resolve().parent.parent / "assets" / "fonts"
    if not font_dir.is_dir():
        return ""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", family).strip("-")
    rules = []
    for w in [x for x in weights.split(";") if x.strip()]:
        p = font_dir / f"{slug}-{w.strip()}.woff2"
        if not p.is_file():
            return ""                     # partial cache is worse than none: mixed sources
        b64 = base64.b64encode(p.read_bytes()).decode()
        rules.append(
            f"@font-face{{font-family:'{family}';font-style:normal;font-weight:{w.strip()};"
            f"font-display:block;src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )
    return "".join(rules)


def mono(brand):
    """(family, weights) for the brand's monospace face, or ('', '') if it has none.

    A second face is a brand decision, not a per-card one. Declaring it here keeps
    the QA font check able to assert it: that check demands every text node render
    in a DECLARED family, so a card that reaches for an undeclared mono silently
    fails rather than silently drifting.
    """
    f = (brand.get("font") or {})
    return f.get("mono", ""), f.get("monoWeights", "400;700")


def font(brand, cfg=None):
    """(family, weights, <style> font block). cfg may override for a one-off.

    Third element is either embedded @font-face rules (preferred, deterministic)
    or the legacy @import line when no local cache exists. When the brand declares
    a mono face, its rules are appended, so any builder can use it without each
    one re-solving font loading.
    """
    cfg = cfg or {}
    f = brand.get("font", {})
    family = cfg.get("font", f.get("family", "Space Grotesk"))
    weights = cfg.get("font_weights", f.get("weights", "400;500;600;700"))
    if f.get("source") == "local":
        imp = ""                          # caller embeds @font-face from brand.font.files
    else:
        imp = _cached_faces(family, weights) or (
            "@import url('https://fonts.googleapis.com/css2?family="
            f"{family.replace(' ', '+')}:wght@{weights}&display=swap');")
        mfam, mweights = mono(brand)
        if mfam:
            imp += _cached_faces(mfam, mweights) or (
                "@import url('https://fonts.googleapis.com/css2?family="
                f"{mfam.replace(' ', '+')}:wght@{mweights}&display=swap');")
    return family, weights, imp


# ---------------------------------------------------------------- footer

def avatar_data_uri(brand):
    """Base64 data URI for the footer photo, or '' when the brand has none."""
    rel = (brand.get("footer") or {}).get("avatar")
    if not rel:
        return ""
    p = pathlib.Path(rel)
    if not p.is_absolute():
        p = pathlib.Path(brand["_dir"]) / rel
    if not p.is_file():
        return ""
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def footer(brand, cfg=None):
    """Merged footer content: config overrides brand, brand overrides nothing."""
    cfg = cfg or {}
    f = brand.get("footer") or {}
    tag = f.get("tagline") or {}
    avatar = avatar_data_uri(brand)
    return {
        # A brand with no photo must emit NO <img> at all. An empty src renders
        # the browser's broken-image glyph, which looks like a bug on the card.
        "avatar_img": f'<img src="{avatar}" alt="">' if avatar else "",
        "name": cfg.get("footer_name", f.get("name", brand.get("name", ""))),
        "role": cfg.get("footer_role", f.get("role", "")),
        "avatar": avatar,
        "seed_accent": cfg.get("seed_accent", tag.get("accent", "")),
        "seed_rest": cfg.get("seed_rest", tag.get("rest", "")),
        # "lead" is plain text before the accent word: "GTM = Go To " + accent "Money".
        "seed_lead": cfg.get("seed_lead", tag.get("lead", "")),
        "site": cfg.get("footer_site", f.get("site", "")),
    }


def seed_html(F):
    """The tagline, composed in one place: lead + accent word + rest."""
    e = html.escape
    parts = [e(F.get("seed_lead", "")), f'<span class="g">{e(F["seed_accent"])}</span>' if F.get("seed_accent") else "",
             e(F.get("seed_rest", ""))]
    lead, acc, rest = parts
    return (lead + acc + (" " + rest if rest and not rest.startswith((" ", ",", ".")) else rest)).strip()


def footer_lock(T, F, scale=1.0, tag=None, right=None):
    """THE card footer. LOCKED 2026-10-11 (Anton picked layout A): photo with no ring,
    name with the site under it on the left, the tagline alone on the right.

    Every builder renders its footer through this function, so the layout is changed
    here and nowhere else (brandkit --self-test fails a builder that draws its own).
    The builder keeps only its container (a flex or grid row with space-between).

      scale  1.0 on a 1080-wide portrait card; smaller cards pass 0.7 to 0.8
      tag    None = brand tagline, "" = no right side, text = that text in its place
      right  raw HTML for the right side (infographic source line)
    Returns {"css", "html", "who"}; "who" is the left block alone.
    """
    e = html.escape
    px = lambda n: f"{round(n * scale, 1):g}px"
    css = (f".lf-who{{display:flex;align-items:center;gap:{px(16)};min-width:0;}}"
           f".lf-who img{{width:{px(68)};height:{px(68)};border-radius:50%;object-fit:cover;border:0;flex-shrink:0;}}"
           f".lf-name{{font-size:{px(28)};font-weight:700;letter-spacing:-.01em;line-height:1.15;color:{T['text']};white-space:nowrap;}}"
           f".lf-site{{font-size:{px(20)};font-weight:500;line-height:1.2;margin-top:{px(2)};color:{T['sub']};white-space:nowrap;}}"
           f".lf-seed{{font-size:{px(26)};font-weight:700;letter-spacing:-.01em;white-space:nowrap;color:{T['text']};}}"
           f".lf-seed .g{{color:{T['accent']};}}")
    site = f'<div class="lf-site">{e(F["site"])}</div>' if F.get("site") else ""
    who = (f'<div class="lf-who">{F["avatar_img"]}<div><div class="lf-name">{e(F["name"])}</div>{site}</div></div>')
    if right is not None:
        r = right
    elif tag is None:
        s = seed_html(F)
        r = f'<div class="lf-seed">{s}</div>' if s else ""
    else:
        r = f'<div class="lf-seed">{e(tag)}</div>' if tag else ""
    return {"css": css, "html": who + r, "who": who}


def footer_lock_violations(src):
    """Why a builder's source does not use the locked footer (empty list = it does)."""
    out = []
    if "footer_lock(" not in src and "brandkit.seed_html(" not in src:
        out.append("does not call brandkit.footer_lock (or seed_html, for the carousel's own footer)")
    for stale in ("F['seed_accent']", 'F["seed_accent"]', "foot-seed", "foot-role", 'class="who"', "pseed-accent"):
        if stale in src:
            out.append(f"still draws its own footer ({stale})")
    return out


# ---------------------------------------------------------------- gate support

def _composite(fg_rgba, backdrop):
    """Flatten rgba(r,g,b,a) over an opaque backdrop hex -> set of #RRGGBB.

    Returns both rounding modes: browsers do not agree on how to round a channel
    that lands on .5, and being one bit out in one channel would fail the palette
    check on a colour the brand itself generated.
    """
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", fg_rgba.replace(" ", ""))
    bg = _rgb(backdrop)
    if not m or bg is None:
        return set()
    r, g, b, a = int(m[1]), int(m[2]), int(m[3]), float(m[4])
    exact = [a * c + (1 - a) * bc for c, bc in zip((r, g, b), bg)]
    return {
        "#%02X%02X%02X" % tuple(round(v) for v in exact),
        "#%02X%02X%02X" % tuple(int(v) for v in exact),
    }


def palette(brand, theme_name):
    """Every literal hex a render of this theme is allowed to contain.

    Accent tints are declared as rgba(), but a screenshot contains the FLATTENED
    colour, so a literal-hex allowlist alone misses them. A live review found the
    note panel (#F2F8F6, 5.4% of the canvas) passing a palette check that never
    covered it. Composite each tint over both plausible backdrops and include the
    results, so the check constrains what is actually rendered.
    """
    t = brand["themes"][theme_name]
    hexes = {v for v in t.values() if isinstance(v, str) and v.startswith("#")}
    hexes.update(brand.get("rules", {}).get("extraPaletteHex", []))
    hexes.add("#FFFFFF")                  # always legal: pure white text/segments
    hexes.add("#C0C0C0" if not is_dark(t["canvas"]) else t["faint"])

    # Only tokens that paint a FLAT surface. Shadows are blurred gradients and
    # rings are hairlines, so compositing those would add a dozen colours the
    # render never contains as a flat fill and quietly widen the allowlist.
    FLAT = ("note_bg", "note_border", "island_bg", "spark_fill",
            "tile_bg", "tile_border", "chip", "surface", "surface_border")
    backdrops = [t["canvas"]] + [v for v in (t.get("surface"), "#FFFFFF") if _rgb(v or "")]
    T = theme(brand, theme_name)
    for key in FLAT:
        v = T.get(key)
        if isinstance(v, str) and v.startswith("rgba"):
            for bd in backdrops:
                hexes.update(_composite(v, bd))
    return sorted(h.upper() for h in hexes)


def _demo():
    b = load()
    assert b["themes"]["light"] and b["themes"]["dark"], "both themes required"
    assert tint("#047857", 0.2) == "rgba(4,120,87,0.2)", tint("#047857", 0.2)
    assert tint("rgba(1,2,3,0.4)", 0.2) == "rgba(1,2,3,0.4)", "non-hex passes through"
    assert is_dark("#0F0F0F") and not is_dark("#F8FBFF")
    # every token any builder dereferences must resolve for BOTH themes,
    # otherwise a format silently KeyErrors only on the theme nobody tested
    required = ("canvas", "text", "sub", "accent", "note_bg", "note_border", "win_shadow",
                "avatar_ring", "window", "win_border", "chrome_border", "dot", "title",
                "pill_fg", "pill_bg", "pill_border", "green_bg", "green_fg", "gray_bg",
                "gray_fg", "foot_border", "range_fg", "range_bg", "range_border", "tile_bg",
                "tile_border", "tile_shadow", "island_bg", "spark_fill", "bg", "muted",
                "structural", "surface", "surface_border", "border", "on_accent", "chip",
                "hairline")
    # Every hex a theme's tokens resolve to must be legal in THAT theme's palette.
    # `structural` used to fall back across themes, so every dark quote card
    # rendered a light-theme hex and failed its own gate. CI caught it; nothing
    # in this file did.
    for name in ("light", "dark"):
        legal = set(palette(b, name))
        for key, v in theme(b, name).items():
            if isinstance(v, str) and v.startswith("#"):
                assert v.upper() in legal, f"{name}.{key} = {v} is not in the {name} palette"

    for name in ("light", "dark"):
        T = theme(b, name)
        for key in required:
            assert T.get(key), f"{name}.{key} missing or empty"
        assert palette(b, name), f"{name} palette empty"
    fam, w, imp = font(b)
    assert fam and w, "font unresolved"
    assert font(b, {"font": "Inter"})[0] == "Inter", "cfg override ignored"
    assert footer(b)["name"], "footer name unresolved"
    no_photo = dict(b, footer=dict(b.get("footer", {}), avatar=None))
    assert footer(no_photo)["avatar_img"] == "", "photoless brand must emit no <img>"
    # locked footer: shape, and a two-sided check that every builder goes through it
    T0 = theme(b, "light")
    F0 = dict(footer(b), name="N", site="s.io", seed_lead="GTM = Go To ", seed_accent="Money", seed_rest="")
    lf = footer_lock(T0, F0)
    assert 'class="lf-name">N<' in lf["html"] and 'class="lf-site">s.io<' in lf["html"], "name and site must be in the left block"
    assert 'GTM = Go To <span class="g">Money</span>' in lf["html"], "tagline = lead + accent word"
    assert "lf-seed" not in footer_lock(T0, F0, tag="")["html"], 'tag="" must drop the right side'
    assert ">T<" in footer_lock(T0, F0, tag="T")["html"], "tag text must replace the tagline"
    assert "lf-site" not in footer_lock(T0, dict(F0, site=""))["html"], "no site = no empty line"
    assert "border:0" in lf["css"] and ":" not in lf["css"].split("font-size:")[1].split(";")[0], "css value shape"
    assert footer_lock_violations("x = 1"), "a builder without the lock must be caught"
    assert footer_lock_violations("footer_lock(T, F) F['seed_accent']"), "a builder that also draws its own must be caught"
    assert footer_lock_violations("brandkit.footer_lock(T, F)") == [], "a clean builder must pass"
    builders = sorted(pathlib.Path(__file__).resolve().parent.glob("*-card.py"))
    assert builders, "no builders found: the footer lock checked nothing"
    bad = [f"{p.name}: {v}" for p in builders for v in footer_lock_violations(p.read_text())]
    assert not bad, "footer lock: " + "; ".join(bad)
    print(f"  footer lock: {len(builders)} builders use brandkit.footer_lock")
    print(f"brandkit OK  <- {b['_path']}")
    print(f"  font    : {fam} @ {w}")
    print(f"  light   : {palette(b, 'light')}")
    print(f"  dark    : {palette(b, 'dark')}")
    print(f"  footer  : {footer(b)['name']!r} / avatar={'yes' if footer(b)['avatar'] else 'none'}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="brand resolver + self-check")
    ap.add_argument("--brand", help="path to brand.json")
    ap.add_argument("--palette", choices=["light", "dark"], help="print this theme's legal hexes")
    ap.add_argument("--get", help="dotted key to print, e.g. font.family or rules.banDashes")
    a = ap.parse_args()
    if a.palette:
        print(" ".join(palette(load(a.brand), a.palette)))
    elif a.get:
        v = load(a.brand)
        for k in a.get.split("."):
            v = (v or {}).get(k)
        print("" if v is None else v)
    else:
        _demo()
