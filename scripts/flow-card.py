#!/usr/bin/env python3
"""
flow-card.py — LinkedIn "ordered sequence" card (1080x1080), config-driven.

A single-frame flow diagram: window chrome -> eyebrow + title -> a 2x2 grid of
four connected steps read clockwise (01 -> 02 -> 03 -> 04) -> takeaway -> footer.
The last node is the payoff and renders on the accent tint.

Use this format when the content's meaning IS the order. A metric grid
(card-dashboard) or a part-to-whole bar (card-bar) cannot say "first this, then
that", and bending sequential content into one of them loses the argument.

Usage:
  python3 flow-card.py --config card.json --theme dark --out /tmp/card.html
  python3 flow-card.py --config card.json --theme dark --motion --out /tmp/card-motion.html

Accent: wrap words in *asterisks* in title/caption/insight.
Config: examples/flow-card.example.json
"""
import argparse, html, json, pathlib, re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit

SCRIPTS = pathlib.Path(__file__).resolve().parent

BRAND = None

# Motion timing lives in one place so the storyboard and the render cannot drift
# apart. Durations follow the Corporate archetype in che-motion-design: card
# enter 200-350ms, dramatic reveal 600-1200ms for the payoff, connectors shorter
# still because they are the secondary layer, not the thing being read.
FIRST_NODE_MS = 420
BEAT_MS = 460            # node-to-node spacing
NODE_D = 340             # card enter
ARROW_D = 240            # connector, secondary layer
ARROW_LAG = 280          # connector lands after its source node has landed
PAYOFF_D = 620           # dramatic reveal on the accent node
CAPTION_MS = 2500
CAPTION_D = 520
# Everything dissolves together, then the card holds empty long enough to read as
# a deliberate reset rather than a cut. Frame 0 and the final frame match.
DISSOLVE_MS = 4400
DISSOLVE_D = 380


def esc(s):
    s = html.escape(str(s), quote=False).replace("'", "’")
    return re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', s)


def build(cfg, theme, motion):
    # Same opt-in key the portrait carousel uses: "treatment": "brutalist".
    brut = "brut" if cfg.get("treatment") == "brutalist" else ""
    T = brandkit.theme(BRAND, theme)
    font_family, font_weights, font_import = brandkit.font(BRAND, cfg)
    mono_family, _ = brandkit.mono(BRAND)
    mono_family = mono_family or font_family
    F = brandkit.footer(BRAND, cfg)

    nodes = cfg["nodes"]
    if len(nodes) != 4:
        raise SystemExit(f"card-flow renders exactly 4 nodes, config has {len(nodes)}")

    def anim(s, d, extra=""):
        if not motion:
            return ""
        return (f' data-s="{s}" data-d="{d}"'
                f' data-out="{DISSOLVE_MS}" data-outd="{DISSOLVE_D}"{extra}')

    runtime = ""
    motion_css = ""
    # "mobile": true lifts every text node to the phone-feed floor (a 1080 canvas
    # shows at ~400px, so nothing under 30px, headline 68px+). Opt-in so existing
    # configs render unchanged. Same key as email-card / before-after-card.
    mobile_css = ("#slide-1{padding:30px;}.chrome{padding:18px 32px;}.title{font-size:30px;}"
                  ".pill{font-size:30px;padding:6px 20px;}.body{padding:24px 32px 22px;gap:20px;}"
                  ".eyebrow{font-size:30px;letter-spacing:0.08em;}.head{font-size:68px;line-height:1.0;}"
                  ".grid{gap:20px 26px;}.node{padding:20px 24px;}.num{font-size:30px;right:20px;top:18px;}"
                  ".kicker{font-size:30px;margin:0 0 6px;}.label{font-size:40px;padding-right:44px;}"
                  ".insight{font-size:30px;margin-top:10px;}.arrow{font-size:40px;}"
                  ".note{padding:14px 22px;}.note .main{font-size:32px;}.foot{padding-top:16px;}"
                  ".lf-who img{width:60px;height:60px;}.lf-name,.lf-site,.lf-seed{font-size:30px;}"
                  # the brutalist rule pinned .num at 26px and 90% opacity, under the phone floor (2026-10-04)
                  ".brut .num.num{font-size:32px;opacity:1;}"
                  # three-critic loop 2026-10-04: one node may carry the proof figure ("big": true);
                  # step numerals go grey so green marks the payoff only; larger arrows; readable descriptors;
                  # the caption strip loses its tint so the accent node is the only filled block
                  ".node.big .label{font-size:60px;letter-spacing:-.04em;}.insight.insight{font-size:33px;}"
                  f".brut .num.num{{color:{T['sub']};}}.arrow.arrow{{font-size:54px;}}"
                  f".brut .note{{background:{T['surface']};border-color:{T['accent']};}}"
                  ) if cfg.get("mobile") else ""
    if motion:
        motion_css = "[data-s]{opacity:0;}"
        runtime = "<script>" + (SCRIPTS / "motion-runtime.js").read_text() + "</script>"

    # Grid reads clockwise: 01 top-left, 02 top-right, 03 bottom-right, 04
    # bottom-left. Connectors sit in the gaps between them.
    order = ["n1", "n2", "n4", "n3"]          # DOM order is grid order (row-major)
    cells = {}
    for i, n in enumerate(nodes):
        start = FIRST_NODE_MS + i * BEAT_MS
        accent = " is-accent" if n.get("accent") else ""
        cells[f"n{i + 1}"] = (
            f'<article class="node{accent}{" big" if n.get("big") else ""}"{anim(start, PAYOFF_D if accent else NODE_D)}>'
            f'<span class="num">{i + 1:02d}</span>'
            f'<div><p class="kicker">{esc(n["sub"])}</p>'
            f'<p class="label">{esc(n["label"])}</p></div>'
            f'<p class="insight">{esc(n["insight"])}</p>'
            f"</article>"
        )
    grid_cells = "".join(cells[k] for k in order)

    arrows = "".join(
        f'<div class="arrow {cls}"{anim(FIRST_NODE_MS + i * BEAT_MS + ARROW_LAG, ARROW_D)}>{glyph}</div>'
        for i, (cls, glyph) in enumerate([("a1", "&#8594;"), ("a2", "&#8595;"), ("a3", "&#8592;")])
    )

    caption = cfg.get("caption", "")
    caption_html = (
        f'<div class="note"{anim(CAPTION_MS, CAPTION_D)}>'
        f'<div class="main">{esc(caption)}</div></div>'
        if caption else ""
    )

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
/* WRAP RULE: text-wrap INHERITS, so declaring balance on the root gives every
   descendant even line lengths and no orphans - a 4-word chip breaks 2+2, not
   3+1 ("Clay to LinkedIn / Ads"). Real paragraphs override to `pretty` below,
   which prevents orphans without forcing even lines. Set here rather than on a
   list of classes so a new element cannot silently miss it. */
#slide-1{{text-wrap:balance;width:1080px;height:1080px;background:{T['canvas']};font-family:'{font_family}',sans-serif;
  color:{T['text']};padding:46px;display:flex;}}
.window{{flex:1;background:{T['window']};border:1px solid {T['win_border']};border-radius:30px;
  box-shadow:{T['win_shadow']};display:flex;flex-direction:column;overflow:hidden;}}
.chrome{{display:flex;align-items:center;justify-content:space-between;padding:26px 40px;
  border-bottom:1px solid {T['chrome_border']};}}
.chrome-l{{display:flex;align-items:center;gap:18px;}}
.dots{{display:flex;gap:9px;}} .dots span{{width:13px;height:13px;border-radius:50%;background:{T['dot']};}}
.title{{font-size:23px;font-weight:700;letter-spacing:-0.01em;color:{T['title']};}}
.pill{{font-size:15px;font-weight:600;color:{T['pill_fg']};background:{T['pill_bg']};
  border:1px solid {T['pill_border']};border-radius:100px;padding:8px 18px;}}
.body{{flex:1;display:flex;flex-direction:column;padding:34px 40px 30px;gap:26px;}}
.eyebrow{{font-size:17px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:{T['sub']};}}
.head{{margin-top:12px;font-size:46px;font-weight:700;letter-spacing:-0.025em;line-height:1.04;max-width:900px;}}
.grid{{position:relative;flex:1;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;
  gap:22px 30px;}}
.node{{position:relative;min-width:0;padding:26px 28px 24px;border:1px solid {T['surface_border']};
  border-radius:22px;background:{T['surface']};display:flex;flex-direction:column;justify-content:center;}}
.node.is-accent{{background:{T['island_bg']};border-color:{T['note_border']};}}
.node.is-accent .label{{color:{T['accent']};}}
.num{{position:absolute;right:24px;top:20px;font-size:34px;font-weight:700;line-height:1;color:{T['muted']};}}
.kicker{{margin:0 0 12px;font-size:18px;font-weight:600;letter-spacing:0.01em;color:{T['sub']};}}
.label{{margin:0;font-size:31px;font-weight:700;letter-spacing:-0.02em;line-height:1.05;}}
.insight{{margin:16px 0 0;font-size:19px;font-weight:500;line-height:1.3;color:{T['sub']};}}
.arrow{{position:absolute;z-index:2;font-size:32px;font-weight:700;line-height:1;color:{T['accent']};}}
.arrow.a1{{left:50%;top:25%;transform:translate(-50%,-50%);}}
.arrow.a2{{left:75%;top:50%;transform:translate(-50%,-50%);}}
.arrow.a3{{left:50%;top:75%;transform:translate(-50%,-50%);}}
.note{{background:{T['note_bg']};border:1px solid {T['note_border']};border-radius:16px;
  padding:18px 24px;display:flex;align-items:center;justify-content:center;}}
.note .main{{font-size:21px;font-weight:500;text-align:center;color:{T['text']};}}
/* Emphasis carries weight as well as colour, so it survives a desaturated or
   colour-blind read instead of relying on the accent hue alone. Both weights are
   real cached faces: asking for 800 would synthesize a faux bold and fail the QA
   font-loaded check, which only passes weights the brand actually ships. */
.note .main .g{{font-weight:700;}}
.g{{color:{T['accent']};}}
.foot{{padding-top:20px;border-top:1px solid {T['foot_border']};display:flex;align-items:center;
  justify-content:space-between;}}
{motion_css}
{mobile_css}

/* ---- BRUTALIST treatment (flow): "treatment":"brutalist" ----
   From the dark cyber-brutalism reference: hard rectangles, mono telemetry,
   slash section codes in the accent, a crosshair at the grid intersection.
   Same palette and face as the default posture; introduces no new colour. */
.brut .window{{border-radius:0;box-shadow:none;border-width:2px;}}
.brut .dots{{display:none;}}
.brut .chrome{{border-bottom-width:2px;}}
.brut .title,.brut .pill{{font-family:'{mono_family}',monospace;letter-spacing:.04em;}}
.brut .pill{{border-radius:0;border:1px solid {T['accent']};background:transparent;color:{T['accent']};}}
.brut .eyebrow{{font-family:'{mono_family}',monospace;letter-spacing:.08em;
  padding-bottom:16px;border-bottom:1px solid {T['surface_border']};}}
.brut .eyebrow::before{{content:"// ";color:{T['accent']};}}
.brut .head{{letter-spacing:-.045em;}}
.brut .node{{border-radius:0;}}
.brut .num{{font-family:'{mono_family}',monospace;color:{T['accent']};font-size:26px;
  letter-spacing:-.04em;opacity:.9;}}
.brut .num::before{{content:"/";opacity:.6;}}
.brut .kicker{{font-family:'{mono_family}',monospace;letter-spacing:.02em;font-weight:400;}}
.brut .label{{letter-spacing:-.035em;}}
.brut .grid::after{{content:"";position:absolute;z-index:3;left:50%;top:50%;
  width:26px;height:26px;transform:translate(-50%,-50%);opacity:.55;
  background:linear-gradient({T['accent']},{T['accent']}) center/2px 100% no-repeat,
             linear-gradient({T['accent']},{T['accent']}) center/100% 2px no-repeat;}}
.brut .note{{border-radius:0;}}
.brut .foot{{border-top-width:2px;border-top-color:{T['accent']};}}
.brut .lf-seed,.brut .lf-site{{font-family:'{mono_family}',monospace;}}
{brandkit.footer_lock(T, F, 0.75)['css']}
</style></head><body><div id="slide-1" class="{brut}"><div class="window">
<div class="chrome"><div class="chrome-l"><div class="dots"><span></span><span></span><span></span></div>
<div class="title">{esc(cfg['window_title'])}</div></div><div class="pill">{esc(cfg.get('pill', 'Sequence'))}</div></div>
<div class="body">
  <div>
    <p class="eyebrow"{anim(0, 460)}>{esc(cfg['eyebrow'])}</p>
    <h1 class="head"{anim(120, 500)}>{esc(cfg['title'])}</h1>
  </div>
  <div class="grid">{grid_cells}{arrows}</div>
  {caption_html}
  <div class="foot">{brandkit.footer_lock(T, F, 0.75)['html']}</div>
</div>
</div></div>{runtime}</body></html>"""


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
