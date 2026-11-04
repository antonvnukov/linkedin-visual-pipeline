#!/usr/bin/env python3
"""
dashboard-card.py — LinkedIn "reporting dashboard card" template (1080x1080).

A reusable single-frame visual for metric / scoreboard / "measure X not Y" posts.
Layout: faux-OS window chrome -> headline -> eyebrow'd metric tiles (icon-island or
big number) -> segment/engine strip with sparklines -> quote note -> brand footer.

Emits HTML for LIGHT or DARK theme on the LOCKED DESIGN.md palette (no drift).
Render to PNG with the sibling capture.js (single frame => ship the PNG, not the PDF).

Usage:
  python3 dashboard-card.py --config card.json --theme dark  --out /tmp/card-dark.html
  python3 dashboard-card.py --config card.json --theme light --out /tmp/card-light.html

Accent marker: wrap words in *asterisks* inside any headline/note to color them green.
Tile "value": "up" | "down" -> arrow in a tinted island; anything else -> big accent number.

Config schema: see templates/dashboard-card.example.json
"""
import argparse, base64, html, json, pathlib, re, sys
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit



BRAND = None


def esc(s):
    """Escape HTML, smarten apostrophes, then convert *accent* markers to green spans."""
    s = html.escape(str(s), quote=False).replace("'", "’")
    return re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', s)


def b64(path):
    return base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def arrow(direction, color, size=46):
    d = ("M12 20 V6 M6 12 L12 5 L18 12" if direction == "up"
         else "M12 4 V18 M6 12 L12 19 L18 12")
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg"><path d="{d}" stroke="{color}" '
            f'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def sparkline(values, color, fill):
    """Plot the segment's own trend. No data -> no chart (this repo forbids fabricated numbers)."""
    if not values:
        return ""
    W, H, PAD, BASE = 150, 46, 6, 44
    n = len(values)
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1                          # flat series -> a mid line, not a divide-by-zero
    def x(i): return PAD + (i * (W - 2 * PAD) / (n - 1) if n > 1 else (W - 2 * PAD) / 2)
    def y(v): return (BASE) - (v - lo) / span * (BASE - PAD)
    pts = [(round(x(i), 1), round(y(v), 1)) for i, v in enumerate(values)]
    poly = " ".join(f"{px},{py}" for px, py in pts)
    area = "M" + " L".join(f"{px},{py}" for px, py in pts) + f" L{pts[-1][0]},{BASE} L{pts[0][0]},{BASE} Z"
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<path d="{area}" fill="{fill}"/>'
            f'<polyline points="{poly}" stroke="{color}" '
            f'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def tile_html(t, T):
    val = str(t.get("value", "up")).lower()
    if val in ("up", "down"):
        badge = f'<div class="island">{arrow(val, T["accent"], 46)}</div>'
    else:
        badge = f'<div class="bignum">{esc(t.get("value", ""))}</div>'
    return (f'<div class="tile"><div class="tile-top"><div class="tile-label">'
            f'{esc(t["label"])}</div>{badge}</div>'
            f'<div class="tile-sub">{esc(t.get("sub",""))}</div></div>')


def seg_html(s, T):
    spark = sparkline(s.get("spark", []), T["accent"], T["spark_fill"])
    spark_html = f'<div class="engine-spark">{spark}</div>' if spark else ""
    return (f'<div class="engine"><div class="engine-head">'
            f'<span class="engine-name">{esc(s["name"])}</span>'
            f'<span class="engine-cap">{esc(s.get("cap","Citations"))}</span></div>'
            f'{spark_html}</div>')


def build(cfg, theme, motion=False):
    T = brandkit.theme(BRAND, theme)
    font_family, font_weights, font_import = brandkit.font(BRAND, cfg)
    F = brandkit.footer(BRAND, cfg)
    # Dissolve before motion_ms so the loop returns to frame 0 (see bar-card.py).
    out = int(cfg.get("motion_ms", 5500)) - 380 - 2 * -(-1000 // int(cfg.get("fps", 24)))
    am = (lambda s, d=520: f' data-s="{s}" data-d="{d}" data-out="{out}"') if motion else (lambda s, d=520: "")
    motion_css = "[data-s]{opacity:0;}" if motion else ""
    # Same opt-in key as before-after, flow and carousel: "treatment": "brutalist".
    # Portrait implies it (Anton 2026-10-18: a rounded dashboard reads as the old style).
    portrait = int(cfg.get("height", 1080)) > 1080
    brut = "brut" if cfg.get("treatment", "brutalist" if portrait else None) == "brutalist" else ""
    mono_family = brandkit.mono(BRAND)[0] or font_family
    brut_css = (f".brut .window,.brut .tile,.brut .engine,.brut .note,.brut .island,.brut .range{{border-radius:0;box-shadow:none;}}"
                f".brut .dots span{{border-radius:0;}}"
                f".brut .title,.brut .range,.brut .eyebrow{{font-family:'{mono_family}',monospace;}}"
                f".brut .title::before{{content:'// ';color:{T['accent']};}}"
                f".brut .headline h1{{letter-spacing:-.04em;}}") if brut else ""
    # "mobile": true lifts every text node to the phone-feed floor (nothing under
    # 30px on the 1080 canvas, headline 68px+) and flows tiles into a 2-column grid
    # with the number above its label. "height": 1350 makes it a 4:5 portrait (pair
    # it with a <config>.qa.json expectedHeight). Both opt-in; old configs unchanged.
    mobile_css = (f"#slide-1{{padding:30px;height:{int(cfg.get('height', 1080))}px;}}"
                  ".chrome{padding:18px 32px;}.title{font-size:30px;}.range{font-size:30px;padding:6px 20px;}"
                  ".body{padding:30px 36px 24px;}.content{gap:40px;}"
                  ".headline h1{font-size:84px;line-height:1.0;}.headline .sub{margin-top:18px;font-size:38px;}"
                  ".eyebrow{font-size:30px;letter-spacing:0.08em;}.tiles{flex-wrap:wrap;}"
                  ".tile{flex:1 1 calc(50% - 9px);min-height:0;gap:8px;padding:28px 28px;}"
                  ".tile-top{flex-direction:column-reverse;align-items:flex-start;gap:4px;}"
                  ".bignum{font-size:88px;line-height:1;}.tile-label{font-size:36px;}.tile-sub{font-size:30px;}"
                  ".note{padding:20px 24px;}.note .main{font-size:36px;}.note .cap{font-size:30px;}"
                  ".foot{padding-top:18px;}.lf-who img{width:60px;height:60px;}"
                  ".lf-name,.lf-site,.lf-seed{font-size:30px;}") if cfg.get("mobile") else ""
    runtime = ("<script>" + (pathlib.Path(__file__).resolve().parent / "motion-runtime.js").read_text() + "</script>") if motion else ""
    tiles = "".join(tile_html(t, T) for t in cfg["tiles"])
    segs = "".join(seg_html(s, T) for s in cfg.get("strip", []))
    strip_block = (f'<div class="strip-block"{am(1000)}><div class="eyebrow">'
                   f'{esc(cfg["strip_eyebrow"])}</div><div class="engines">{segs}</div></div>'
                   if cfg.get("strip") else "")

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
/* WRAP RULE: text-wrap INHERITS, so declaring balance on the root gives every
   descendant even line lengths and no orphans - a 4-word chip breaks 2+2, not
   3+1 ("Clay to LinkedIn / Ads"). Real paragraphs override to `pretty` below,
   which prevents orphans without forcing even lines. Set here rather than on a
   list of classes so a new element cannot silently miss it. */
#slide-1{{text-wrap:balance;box-shadow:inset 0 0 0 1px {T['border']};width:1080px;height:1080px;background:{T['canvas']};font-family:'{font_family}',sans-serif;
  color:{T['text']};padding:46px;display:flex;position:relative;}}
.window{{flex:1;background:{T['window']};border:1px solid {T['win_border']};border-radius:30px;
  box-shadow:{T['win_shadow']};display:flex;flex-direction:column;overflow:hidden;}}
.chrome{{display:flex;align-items:center;justify-content:space-between;padding:26px 40px;
  border-bottom:1px solid {T['chrome_border']};}}
.chrome-l{{display:flex;align-items:center;gap:18px;}}
.dots{{display:flex;gap:9px;}} .dots span{{width:13px;height:13px;border-radius:50%;background:{T['dot']};}}
.title{{font-size:23px;font-weight:800;letter-spacing:-0.01em;color:{T['title']};}}
.range{{font-size:15px;font-weight:600;color:{T['range_fg']};background:{T['range_bg']};
  border:1px solid {T['range_border']};border-radius:100px;padding:8px 18px;}}
.body{{flex:1;display:flex;flex-direction:column;padding:40px 40px 32px;}}
.content{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:42px;}}
.headline h1{{font-size:56px;font-weight:800;letter-spacing:-0.02em;line-height:1.0;color:{T['text']};}}
.headline .sub{{margin-top:14px;font-size:27px;font-weight:500;color:{T['sub']};}}
.g{{color:{T['accent']};}}
.eyebrow{{font-size:13px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;
  color:{T['accent']};margin-bottom:15px;}}
.tiles{{display:flex;gap:18px;}}
.tile{{flex:1;background:{T['tile_bg']};border:1px solid {T['tile_border']};border-radius:20px;
  padding:24px;display:flex;flex-direction:column;gap:16px;min-height:172px;box-shadow:{T['tile_shadow']};}}
.tile-top{{display:flex;align-items:center;justify-content:space-between;}}
.tile-label{{font-size:23px;font-weight:700;color:{T['text']};}}
.island{{width:64px;height:64px;border-radius:18px;background:{T['island_bg']};display:flex;
  align-items:center;justify-content:center;flex-shrink:0;}}
.bignum{{font-size:44px;font-weight:800;letter-spacing:-0.02em;color:{T['accent']};flex-shrink:0;}}
.tile-sub{{font-size:16px;font-weight:500;color:{T['sub']};line-height:1.34;margin-top:auto;}}
.engines{{display:flex;gap:18px;}}
.engine{{flex:1;background:{T['tile_bg']};border:1px solid {T['tile_border']};border-radius:18px;
  padding:20px 22px;display:flex;flex-direction:column;gap:10px;box-shadow:{T['tile_shadow']};}}
.engine-head{{display:flex;align-items:baseline;justify-content:space-between;}}
.engine-name{{font-size:20px;font-weight:700;color:{T['text']};}}
.engine-cap{{font-size:13px;font-weight:600;color:{T['sub']};}}
.engine-spark{{margin-top:2px;}}
.note{{background:{T['note_bg']};border:1px solid {T['note_border']};border-radius:16px;padding:20px 24px;}}
.note .main{{font-size:23px;font-weight:700;color:{T['text']};}}
.note .cap{{font-size:16px;font-weight:500;color:{T['sub']};margin-top:5px;}}
.foot{{padding-top:22px;border-top:1px solid {T['foot_border']};display:flex;align-items:center;
  justify-content:space-between;}}
{motion_css}
{mobile_css}
{brut_css}
{brandkit.footer_lock(T, F, 0.75)['css']}
</style></head><body><div id="slide-1" class="{brut}"><div class="window">
<div class="chrome"><div class="chrome-l"><div class="dots"><span></span><span></span><span></span></div>
<div class="title">{esc(cfg['window_title'])}</div></div>
<div class="range">{esc(cfg.get('range','Last 30 days'))}</div></div>
<div class="body"><div class="content">
<div class="headline"{am(100)}><h1>{esc(cfg['headline'])}</h1><div class="sub">{esc(cfg['subhead'])}</div></div>
<div class="tiles-block"{am(460)}><div class="eyebrow">{esc(cfg['tiles_eyebrow'])}</div>
<div class="tiles">{tiles}</div></div>
{strip_block}
<div class="note"{am(1500)}><div class="main">{esc(cfg['note'])}</div>
<div class="cap">{esc(cfg.get('note_cap',''))}</div></div>
</div>
<div class="foot">{brandkit.footer_lock(T, F, 0.75)['html']}</div>
</div></div></div>{runtime}</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--theme", choices=["light", "dark"], default="dark")
    ap.add_argument("--motion", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand", help="path to brand.json")
    a = ap.parse_args()
    global BRAND
    BRAND = brandkit.load(a.brand)
    cfg = json.loads(pathlib.Path(a.config).read_text())
    pathlib.Path(a.out).write_text(build(cfg, a.theme, a.motion))
    print(f"wrote {a.out} ({a.theme}{', motion' if a.motion else ''})")


def _selftest():
    # empty -> nothing; a rising series must map to strictly falling y (SVG y grows downward)
    assert sparkline([], "#000", "#eee") == ""
    svg = sparkline([1, 2, 3, 4], "#0a0", "#e0f0e0")
    import re as _re
    ys = [float(p.split(",")[1]) for p in _re.search(r'points="([^"]+)"', svg).group(1).split()]
    assert ys == sorted(ys, reverse=True), ys              # rising values -> descending y
    assert 6 <= min(ys) and max(ys) <= 44, ys              # inside the padded box
    flat = sparkline([5, 5, 5], "#0a0", "#eee")            # flat series must not divide by zero
    assert "polyline" in flat
    global BRAND
    BRAND = brandkit.load(None)
    base = {"window_title": "t", "headline": "h", "subhead": "s", "tiles_eyebrow": "e", "tiles": [], "note": "n"}
    assert 'class="brut"' in build(dict(base, height=1350), "light"), "portrait defaults to brutalist"
    assert 'class="brut"' not in build(base, "light"), "square stays rounded unless asked"
    assert 'class="brut"' not in build(dict(base, height=1350, treatment="soft"), "light"), "an explicit treatment wins"
    print("dashboard-card self-test ok (sparkline, brutalist default on portrait)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        _selftest()
    else:
        main()
