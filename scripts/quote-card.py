#!/usr/bin/env python3
"""
quote-card.py — LinkedIn "stat + quote" card (1080x1080), config-driven.

Single-frame quote card. Palette, font and footer all come from brand.json. Matches the
faux-OS window chrome used by dashboard-card/bar-card so the format reads as
part of the same visual family. Layout: window chrome -> eyebrow -> hero stat
+ label -> quote surface (decorative quotation mark + bordered card) -> source
-> brand footer.

Usage:
  python3 quote-card.py --config card.json --out /tmp/card.html
Then:
  node capture.js --html /tmp/card.html --slides 1 --outdir <dir> --scale 2

Config schema: see templates/quote-card.example.json
"""
import argparse, base64, html, json, pathlib, re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit


BRAND = None


def esc(s):
    s = html.escape(str(s), quote=False).replace("'", "’")
    return re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', s)


def b64(p):
    return base64.b64encode(pathlib.Path(p).read_bytes()).decode()


def build(cfg, theme=None):
    T = brandkit.theme(BRAND, theme or BRAND.get('rules', {}).get('defaultTheme', 'dark'))
    font_family, font_weights, font_import = brandkit.font(BRAND, cfg)
    F = brandkit.footer(BRAND, cfg)
    # The hero stat is optional. A quote can carry a card on its own, and forcing
    # a number into the slot invents emphasis the copy never asked for.
    stat_html = ""
    if cfg.get("stat"):
        stat_html = (f'<div class="stat-block"><div class="hero">{esc(cfg["stat"])}</div>'
                     f'<div class="label">{esc(cfg.get("stat_label", ""))}</div></div>')
    accent = cfg.get("accent_line")
    accent_html = f'<div class="accent-line">{esc(accent)}</div>' if accent else ""

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
/* WRAP RULE: text-wrap INHERITS, so declaring balance on the root gives every
   descendant even line lengths and no orphans - a 4-word chip breaks 2+2, not
   3+1 ("Clay to LinkedIn / Ads"). Real paragraphs override to `pretty` below,
   which prevents orphans without forcing even lines. Set here rather than on a
   list of classes so a new element cannot silently miss it. */
#slide-1{{text-wrap:balance;box-shadow:inset 0 0 0 1px {T['border']};width:1080px;height:1080px;background:{T['bg']};font-family:'{font_family}',sans-serif;
  color:{T['text']};padding:46px;display:flex;}}
.window{{flex:1;background:{T['window']};border:1px solid {T['win_border']};border-radius:30px;
  display:flex;flex-direction:column;overflow:hidden;}}
.chrome{{display:flex;align-items:center;gap:18px;padding:26px 40px;
  border-bottom:1px solid {T['win_border']};}}
.dots{{display:flex;gap:9px;}} .dots span{{width:13px;height:13px;border-radius:50%;background:{T['dot']};}}
.chrome-title{{font-size:15px;font-weight:700;letter-spacing:0.06em;color:{T['sub']};}}
.body{{flex:1;display:flex;flex-direction:column;padding:{cfg.get('body_pad_top',56)}px 64px 44px;}}
.content{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:{cfg.get('gap',36)}px;}}
.eyebrow{{font-size:{cfg.get('eyebrow_size',14)}px;font-weight:700;letter-spacing:0.16em;
  text-transform:uppercase;color:{T['accent']};}}
.stat-block{{display:flex;flex-direction:column;}}
.hero{{font-size:{cfg.get('stat_size',160)}px;font-weight:800;
  letter-spacing:-0.03em;line-height:0.9;color:{T['accent']};}}
.label{{margin-top:8px;font-size:{cfg.get('label_size',36)}px;font-weight:500;color:{T['sub']};}}
/* Optional supporting line under the quote: names the parts of a framework the
   quote refers to. Brand secondary text, so it reads as context rather than
   competing with the quote for the eye. */
.accent-line{{font-size:{cfg.get('accent_size',24)}px;font-weight:500;line-height:1.45;
  letter-spacing:0.01em;color:{T['sub']};max-width:{cfg.get('accent_width',660)}px;}}
.quote-card{{position:relative;background:{T['surface']};border:1px solid {T['surface_border']};
  border-radius:24px;padding:118px 44px 32px;overflow:hidden;}}
.quote-mark{{position:absolute;top:24px;left:40px;font-size:120px;font-weight:800;
  color:{T['structural']};opacity:0.28;line-height:1;}}
.quote{{position:relative;font-size:{cfg.get('quote_size',32)}px;font-weight:600;line-height:1.3;
  color:{T['text']};max-width:820px;}}
.source{{position:relative;margin-top:18px;font-size:{cfg.get('source_size',18)}px;
  font-weight:400;color:{T['sub']};}}
.g{{color:{T['accent']};}}
.foot{{padding-top:22px;border-top:1px solid {T['foot_border']};display:flex;align-items:center;
  justify-content:space-between;}}
{brandkit.footer_lock(T, F, 0.75)['css']}
</style></head><body><div id="slide-1"><div class="window">
  <div class="chrome"><div class="dots"><span></span><span></span><span></span></div>
  <div class="chrome-title">{esc(cfg.get('window_title','Insight'))}</div></div>
  <div class="body"><div class="content">
    <div class="eyebrow">{esc(cfg['eyebrow'])}</div>
    {stat_html}
    <div class="quote-card">
      <div class="quote-mark">&ldquo;</div>
      <div class="quote">{esc(cfg['quote'])}</div>
      <div class="source">{esc(cfg['source'])}</div>
    </div>
    {accent_html}
  </div>
  <div class="foot">{brandkit.footer_lock(T, F, 0.75)['html']}</div>
  </div>
</div></div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand", help="path to brand.json")
    ap.add_argument("--theme", choices=["light", "dark"])
    a = ap.parse_args()
    global BRAND
    BRAND = brandkit.load(a.brand)
    cfg = json.loads(pathlib.Path(a.config).read_text())
    pathlib.Path(a.out).write_text(build(cfg, a.theme))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
