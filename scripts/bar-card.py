#!/usr/bin/env python3
"""
bar-card.py — LinkedIn "stat + stacked bar" card (1080x1080), config-driven.

A single-frame data card: window chrome -> big hero stat -> headline + source ->
one 2-segment stacked bar (part-to-whole) -> centered takeaway -> brand footer.
LIGHT or DARK theme on the locked palette. --motion tags elements for the shared
motion-runtime.js (hero counts up, bar wipes in, text staggers) for frame capture.

Usage:
  python3 bar-card.py --config card.json --theme light --out /tmp/card.html
  python3 bar-card.py --config card.json --theme dark --motion --out /tmp/card-motion.html

Accent: wrap words in *asterisks* in note/headline. Config: templates/bar-card.example.json
"""
import argparse, base64, html, json, pathlib, re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit

SCRIPTS = pathlib.Path(__file__).resolve().parent


BRAND = None


def esc(s):
    s = html.escape(str(s), quote=False).replace("'", "’")
    return re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', s)


def b64(p):
    return base64.b64encode(pathlib.Path(p).read_bytes()).decode()


def build(cfg, theme, motion):
    T = brandkit.theme(BRAND, theme)
    font_family, font_weights, font_import = brandkit.font(BRAND, cfg)
    F = brandkit.footer(BRAND, cfg)
    green_pct = cfg.get("green_pct", 62.1)
    gray_pct = cfg.get("gray_pct", 37.9)

    # motion hooks
    # Dissolve before motion_ms so the loop returns to frame 0 (render.sh gates the
    # seam losslessly; this card had no fade-out and jumped on every loop until 2026-09-28).
    out = int(cfg.get("motion_ms", 5500)) - 380 - 2 * -(-1000 // int(cfg.get("fps", 24)))

    def anim(s, d, extra=""):
        return f' data-s="{s}" data-d="{d}" data-out="{out}"{extra}' if motion else ""
    stat_count = cfg.get("stat_count")
    big_attr = (anim(100, 1300, f' data-count="{stat_count}" data-suffix="%" data-dec="1"')
                if (motion and stat_count is not None) else anim(100, 1300))
    runtime = ""
    motion_css = ""
    if motion:
        motion_css = "[data-s]{opacity:0;}"
        runtime = "<script>" + (SCRIPTS / "motion-runtime.js").read_text() + "</script>"

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
/* WRAP RULE: text-wrap INHERITS, so declaring balance on the root gives every
   descendant even line lengths and no orphans - a 4-word chip breaks 2+2, not
   3+1 ("Clay to LinkedIn / Ads"). Real paragraphs override to `pretty` below,
   which prevents orphans without forcing even lines. Set here rather than on a
   list of classes so a new element cannot silently miss it. */
#slide-1{{text-wrap:balance;box-shadow:inset 0 0 0 1px {T['border']};width:1080px;height:1080px;background:{T['canvas']};font-family:'{font_family}',sans-serif;
  color:{T['text']};padding:46px;display:flex;}}
.window{{flex:1;background:{T['window']};border:1px solid {T['win_border']};border-radius:30px;
  box-shadow:{T['win_shadow']};display:flex;flex-direction:column;overflow:hidden;}}
.chrome{{display:flex;align-items:center;justify-content:space-between;padding:26px 40px;
  border-bottom:1px solid {T['chrome_border']};}}
.chrome-l{{display:flex;align-items:center;gap:18px;}}
.dots{{display:flex;gap:9px;}} .dots span{{width:13px;height:13px;border-radius:50%;background:{T['dot']};}}
.title{{font-size:23px;font-weight:800;letter-spacing:-0.01em;color:{T['title']};}}
.pill{{font-size:15px;font-weight:600;color:{T['pill_fg']};background:{T['pill_bg']};
  border:1px solid {T['pill_border']};border-radius:100px;padding:8px 18px;}}
.body{{flex:1;display:flex;flex-direction:column;padding:40px 40px 32px;}}
.content{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:60px;}}
.chart{{display:flex;flex-direction:column;gap:52px;}}
.big{{font-size:132px;font-weight:800;letter-spacing:-0.03em;line-height:0.9;color:{T['accent']};}}
.head{{margin-top:14px;font-size:36px;font-weight:700;letter-spacing:-0.02em;line-height:1.08;max-width:820px;}}
.src{{margin-top:14px;font-size:17px;font-weight:500;color:{T['sub']};}}
.bars{{display:flex;flex-direction:column;align-items:flex-start;}}
.stacked{{display:flex;height:64px;border-radius:16px;overflow:hidden;width:100%;}}
.seg{{display:flex;align-items:center;height:100%;white-space:nowrap;}}
.seg-green{{flex:0 0 {green_pct}%;background:{T['green_bg']};padding:0 26px;}}
.seg-gray{{flex:0 0 {gray_pct}%;background:{T['gray_bg']};padding:0 22px;justify-content:space-between;}}
.seg .nm{{font-size:18px;font-weight:700;letter-spacing:-0.01em;}}
.seg-green .nm{{color:{T['green_fg']};}}
.seg-gray .nm{{color:{T['gray_fg']};}} .seg-gray .pct{{font-size:19px;font-weight:800;color:{T['gray_fg']};}}
.note{{background:{T['note_bg']};border:1px solid {T['note_border']};border-radius:16px;
  padding:20px 24px;display:flex;align-items:center;justify-content:center;}}
.note .main{{font-size:22px;font-weight:700;text-align:center;color:{T['text']};}}
.note .main .g{{color:{T['accent']};}}
.g{{color:{T['accent']};}}
.foot{{padding-top:22px;border-top:1px solid {T['foot_border']};display:flex;align-items:center;justify-content:space-between;}}
{motion_css}
{brandkit.footer_lock(T, F, 0.75)['css']}
</style></head><body><div id="slide-1"><div class="window">
<div class="chrome"><div class="chrome-l"><div class="dots"><span></span><span></span><span></span></div>
<div class="title">{esc(cfg['window_title'])}</div></div><div class="pill">{esc(cfg.get('pill','Last 30 days'))}</div></div>
<div class="body"><div class="content">
  <div class="chart">
  <div class="focal">
    <div class="big"{big_attr}>{esc(cfg['stat'])}</div>
    <div class="head"{anim(350,500)}>{esc(cfg['headline'])}</div>
    <div class="src"{anim(560,500)}>{esc(cfg['source'])}</div>
  </div>
  <div class="bars"><div class="stacked"{anim(900,1150,' data-wipe')}>
    <div class="seg seg-green"><span class="nm">{esc(cfg['green_label'])}</span></div>
    <div class="seg seg-gray"><span class="nm">{esc(cfg['gray_label'])}</span><span class="pct">{gray_pct}%</span></div>
  </div></div>
  </div>
  <div class="note"{anim(2150,520)}><div class="main">{esc(cfg['note'])}</div></div>
</div>
<div class="foot">{brandkit.footer_lock(T, F, 0.75)['html']}</div>
</div></div></div>{runtime}</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--theme", choices=["light", "dark"], default="light")
    ap.add_argument("--motion", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand", help="path to brand.json")
    a = ap.parse_args()
    global BRAND
    BRAND = brandkit.load(a.brand)
    cfg = json.loads(pathlib.Path(a.config).read_text())
    pathlib.Path(a.out).write_text(build(cfg, a.theme, a.motion))
    print(f"wrote {a.out} ({a.theme}{', motion' if a.motion else ''})")


if __name__ == "__main__":
    main()
