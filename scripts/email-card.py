#!/usr/bin/env python3
"""
email-card.py — LinkedIn "template card" (1080x1080), config-driven.

THIRD SILHOUETTE. The window family (bar / dashboard / flow / quote) is faux-OS
chrome; card-before-after is a full-bleed split. This one is a single centred
card on a quiet field: a label column and a monospace body, set with enough
leading that the lines read one at a time.

Use it when the content IS a template, a skeleton, or a snippet the reader could
copy. The monospace column is the point: it signals "this is the artefact", not
prose about the artefact, and the leading does the staccato work that a
paragraph cannot.

The mono face comes from brand.font.mono (a brand decision, so the QA font check
can still assert every text node renders in a DECLARED family). It is NOT a
per-card override, because an undeclared font is exactly the drift that check
exists to catch.

Usage:
  python3 email-card.py --config card.json --theme dark --out /tmp/card.html

Config: examples/email-skeleton.example.json
"""
import argparse, html, json, pathlib, re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit

SCRIPTS = pathlib.Path(__file__).resolve().parent
BRAND = None
ROW_MS, ROW_STEP, BEAT = 420, 130, 360


def esc(s):
    s = html.escape(str(s), quote=False).replace("'", "’")
    return re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', s)


def build(cfg, theme, motion):
    T = brandkit.theme(BRAND, theme)
    font_family, _, font_import = brandkit.font(BRAND, cfg)
    mono_family, _ = brandkit.mono(BRAND)
    if not mono_family:
        raise SystemExit("card-email needs brand.font.mono; run scripts/fetch-fonts.py --family '<Mono>'")
    F = brandkit.footer(BRAND, cfg)
    rows = cfg["rows"]

    # Dissolve before motion_ms so the loop returns to frame 0. render.sh gates the seam
    # losslessly; without this fade every motion render of this format fails that gate.
    out = int(cfg.get("motion_ms", 5500)) - 380 - 2 * -(-1000 // int(cfg.get("fps", 24)))

    def anim(s, d):
        return f' data-s="{s}" data-d="{d}" data-out="{out}"' if motion else ""

    runtime = "<script>" + (SCRIPTS / "motion-runtime.js").read_text() + "</script>" if motion else ""
    motion_css = "[data-s]{opacity:0;}" if motion else ""

    body = "".join(
        f'<div class="ln"{anim(ROW_MS + i * ROW_STEP, BEAT)}>'
        f'<span class="tag">{esc(r["tag"])}</span>'
        f'<span class="txt">{esc(r["text"])}</span></div>'
        for i, r in enumerate(rows)
    )
    kicker = f'<p class="kick">{esc(cfg["kicker"])}</p>' if cfg.get("kicker") else ""
    # "mobile": true lifts every text node to the phone-feed floor (a 1080 canvas
    # shows at ~400px, so nothing under 30px, headline 68px+). Opt-in so existing
    # configs render unchanged.
    mobile_css = (".eyebrow{font-size:30px;}.head{font-size:72px;}.kick{font-size:34px;}"
                  ".tag{font-size:30px;}"
                  ".foot{flex-basis:112px;}") if cfg.get("mobile") else ""

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
/* WRAP RULE: text-wrap INHERITS, so declaring balance on the root gives every
   descendant even line lengths and no orphans - a 4-word chip breaks 2+2, not
   3+1 ("Clay to LinkedIn / Ads"). Real paragraphs override to `pretty` below,
   which prevents orphans without forcing even lines. Set here rather than on a
   list of classes so a new element cannot silently miss it. */
#slide-1{{text-wrap:balance;box-shadow:inset 0 0 0 1px {T['border']};width:1080px;height:1080px;background:{T['canvas']};color:{T['text']};
  font-family:'{font_family}',sans-serif;display:flex;flex-direction:column;
  padding:58px 62px 0;overflow:hidden;-webkit-font-smoothing:antialiased;}}
.eyebrow{{font-size:16px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:{T['sub']};}}
.head{{margin-top:14px;font-size:52px;font-weight:700;letter-spacing:-.025em;line-height:1.04;}}
.kick{{margin-top:18px;font-size:21px;font-weight:500;color:{T['sub']};}}
/* The card shrink-wraps its rows and the STAGE centres it. Letting the card
   itself flex:1 stretched it to the full column and parked ~300px of dead space
   above and below the six lines. */
.stage{{flex:1;min-height:0;display:flex;align-items:center;}}
.card{{width:100%;background:{T['surface']};
  border:1px solid {T['surface_border']};border-radius:22px;padding:30px 36px;
  display:flex;flex-direction:column;gap:{cfg.get('row_gap', 10)}px;}}
.ln{{display:grid;grid-template-columns:{cfg.get('tag_col', 132)}px 1fr;gap:22px;align-items:baseline;
  padding:{cfg.get('row_pad', 17)}px 0;}}
.ln + .ln{{border-top:1px solid {brandkit.tint(T['text'], .06)};}}
/* Labels are the scan layer: same mono as the body so the block reads as one
   artefact, accent-coloured so the eye can jump Subject to Line 5 without
   reading the prose. */
.tag{{font-family:'{mono_family}',monospace;font-size:19px;font-weight:700;letter-spacing:.04em;
  color:{T['accent']};white-space:nowrap;}}
.txt{{font-family:'{mono_family}',monospace;font-size:{cfg.get('body_size', 23)}px;font-weight:400;
  line-height:1.35;color:{T['text']};}}
.g{{color:{T['accent']};}}
.foot{{flex:0 0 92px;display:flex;align-items:center;justify-content:space-between;
  border-top:1px solid {T['foot_border']};margin-top:24px;}}
{motion_css}
{mobile_css}
{brandkit.footer_lock(T, F, 0.8)['css']}
</style></head><body><div id="slide-1">
  <p class="eyebrow">{esc(cfg['eyebrow'])}</p>
  <h1 class="head">{esc(cfg['title'])}</h1>
  {kicker}
  <div class="stage"><div class="card">{body}</div></div>
  <div class="foot">{brandkit.footer_lock(T, F, 0.8)['html']}</div>
</div>{runtime}</body></html>"""


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


if __name__ == "__main__":
    main()
