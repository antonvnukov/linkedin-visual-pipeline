#!/usr/bin/env python3
"""
before-after-card.py — LinkedIn "before vs after" split (1080x1080), config-driven.

A SECOND SILHOUETTE. Every other format in this kit (bar, dashboard, flow, quote)
is the same faux-OS window: chrome dots, pill, eyebrow, content, footer. Four of
them in a row read as one repeated template in a feed. This one deliberately drops
the window and goes full-bleed: a centred eyebrow rail, two columns split by a
glowing rule, and a footer with a hairline top border.

What does NOT change is the brand: Space Grotesk, the locked palette, the avatar
and seed footer. Recognition comes from those. Fatigue comes from repeating the
same COMPOSITION, so composition is the thing allowed to vary.

Left column is the old way: a slightly crooked pile of struck-through cards.
Right column is the new way: a clean vertical pipeline of dotted nodes ending on
an emphasised final node. The split compares EFFORT, not quantity, so the two
sides do not need equal row counts.

Ported 2026-08-14 from brand-guide/visual-system/templates/
linkedin-square-before-after-outreach.html, which had shipped but was never
carried into the plugin.

Usage:
  python3 before-after-card.py --config card.json --theme dark --out /tmp/card.html

Config: examples/before-after-card.example.json

Opt-in PORTRAIT profile (2026-10-05): "height": 1350. Without the key the canvas stays
1080x1080 and the HTML is byte-identical to before. See PORTRAIT_H and the portrait block
in build(); `--self-test` is two-sided (key absent vs 1350).
"""
import argparse, html, json, pathlib, re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit

SCRIPTS = pathlib.Path(__file__).resolve().parent
BRAND = None

# Each row is nudged a different way so the pile reads as handled, not designed.
TILTS = ["rotate(-1.8deg)", "translateX(13px) rotate(1.4deg)", "translateX(-3px) rotate(-.9deg)",
         "translateX(10px) rotate(1.7deg)", "translateX(2px) rotate(-1.3deg)"]
PORTRAIT_H = 1350
ROW_MS, ROW_STEP, NODE_MS, NODE_STEP, BEAT = 380, 90, 900, 220, 340


def esc(s):
    s = html.escape(str(s), quote=False).replace("'", "’")
    return re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', s)


def build(cfg, theme, motion):
    # Feed-portrait profile: exactly "height": 1350. Any other value fails loud.
    H = int(cfg.get("height", 1080))
    if H not in (1080, PORTRAIT_H):
        raise SystemExit(f"before-after: height {H} unsupported (1080 or {PORTRAIT_H})")
    portrait = H == PORTRAIT_H
    # Same opt-in key as the carousel and card-flow: "treatment": "brutalist".
    # Portrait implies it (square-corner site style) unless the config names a treatment.
    treatment = cfg.get("treatment", "brutalist" if portrait else None)
    brut = "brut" if treatment == "brutalist" else ""
    # Portrait also implies the phone-size text option unless the config sets "mobile".
    mobile = cfg.get("mobile", portrait)
    T = brandkit.theme(BRAND, theme)
    font_family, _, font_import = brandkit.font(BRAND, cfg)
    mono_family, _ = brandkit.mono(BRAND)
    mono_family = mono_family or font_family
    F = brandkit.footer(BRAND, cfg)
    # Footer is LOCKED to layout A (Anton 2026-10-11): photo + name + site left, tagline right.
    # "footer_tag": "" used to centre the identity and drop the tagline; it shipped the wrong
    # footer on 2026-10-17, so an empty value now means the brand tagline. Text still replaces it.
    ft = cfg.get("footer_tag") or None
    foot_cls = "foot"
    solo_css = ""
    before, after = cfg["before"], cfg["after"]
    # Opt-in keys added by the three-critic loop of 2026-10-04 (defaults unchanged):
    #   before.hero     a muted headline on the left, so both columns open with one
    #   "pack": "top"   both lists start right under their header instead of floating centred
    #   "final": false  every pipeline node identical (no hollow last node, no heavier last card)
    left_head = (f'<p class="hero hero-a">{esc(before["hero"])}</p>' if before.get("hero")
                 else f'<p class="sub">{esc(before["subhead"])}</p>')
    pack_css = (".stack,.pipe{justify-content:flex-start;padding-top:40px;}"
                if cfg.get("pack") == "top" else "")
    #   "node_min": N   pipeline card height in px, so three nodes can match a taller left pile;
    #                   the connector is trimmed to run node centre to node centre
    nm = cfg.get("node_min")
    node_css = (f".ncard.ncard{{min-height:{int(nm)}px;}}"
                f".pipe .inner::before{{top:{int(nm)//2}px;bottom:{int(nm)//2}px;}}") if nm else ""
    #   "row_min": N    left pile row height in px (pairs with node_min to close the gap above the captions)
    rm = cfg.get("row_min")
    node_css += f".old.old{{min-height:{int(rm)}px;}}" if rm else ""
    final_css = ("" if cfg.get("final", True) else
                 f".pnode:last-child .dot{{border:0;background:{T['accent']};outline:0;}}"
                 f".pnode:last-child .ncard{{border:1px solid {T['accent']};}}")
    gm = cfg.get("gap_label")
    gap_marker = (f'<div class="gapmark"><span class="gm-a">&larr;</span>'
                  f'<span class="gm-t">{esc(gm)}</span>'
                  f'<span class="gm-a">&rarr;</span></div>') if gm else ""

    # Dissolve before motion_ms so the loop returns to frame 0. render.sh gates the seam
    # losslessly; without this fade every motion render of this format fails that gate.
    out = int(cfg.get("motion_ms", 5500)) - 380 - 2 * -(-1000 // int(cfg.get("fps", 24)))

    def anim(s, d):
        return f' data-s="{s}" data-d="{d}" data-out="{out}"' if motion else ""

    runtime = "<script>" + (SCRIPTS / "motion-runtime.js").read_text() + "</script>" if motion else ""
    # "mobile": true lifts every text node to the phone-feed floor (nothing under
    # 30px on the 1080 canvas). Opt-in so existing configs render unchanged.
    mobile_css = (".rail{flex-basis:84px;}.rail p{font-size:30px;}.pill{font-size:30px;height:52px;padding:0 24px;}"
                  ".sub{font-size:34px;max-width:none;}.old,.ncard{font-size:32px;min-height:96px;}"
                  ".tag{font-size:30px;}.cap{font-size:30px;}.gm-t{font-size:30px;}.gm-a{font-size:30px;}"
                  ".foot{flex-basis:100px;}"
                  ""
                  # the brutalist rules below are more specific and pinned .sub/.cap at 21/20px,
                  # under the phone floor; doubled class = same floor in both postures (2026-10-04)
                  ".brut .sub.sub{font-size:30px;}.brut .cap.cap{font-size:34px;line-height:1.25;letter-spacing:-.01em;}"
                  ".brut .old.old{font-size:35px;}") if mobile else ""
    motion_css = "[data-s]{opacity:0;}" if motion else ""

    # Portrait: the extra 270px goes to the columns, never to a dead band. The header rows
    # are shared through subgrid so both stacks start on one line, rows and nodes stretch
    # to fill the stack, and the connector runs node centre to node centre by calc().
    portrait_css, closing = "", ""
    if portrait:
        n, g = len(after["steps"]), 16
        hs = cfg.get("hero_size", 76)
        portrait_css = (
            f"#slide-1{{height:{H}px;}}"
            ".split{grid-template-rows:auto 1fr auto;row-gap:0;}"
            ".col{grid-row:1/4;grid-template-rows:subgrid;}"
            ".stack,.pipe{justify-content:stretch;padding:22px 0 0;}"
            ".inner{flex:1;}.row{flex:1;}.old.old{height:100%;}"
            ".pnode{flex:1;align-items:stretch;}.dot{align-self:center;}.ncard.ncard{height:auto;}"
            f".pipe .inner::before{{top:calc((100% - {(n - 1) * g}px)/{2 * n});bottom:calc((100% - {(n - 1) * g}px)/{2 * n});}}"
            f".hero{{font-size:{hs}px;}}"
            ".rail p{letter-spacing:.05em;}"  # .14em on 30px type trips impeccable [wide-tracking]
            ".hero.hero-a{line-height:1.12;}"  # 2-line left hero beside a 3-line right one: close the header gap
            ".tag{font-size:26px;}.cap{padding-top:18px;}"
            ".closing{flex:0 0 auto;padding:22px 52px 24px;font-size:36px;line-height:1.3;font-weight:700;"
            f"letter-spacing:-.015em;color:{T['text']};border-top:2px solid {T['sub']};}}"
        )
        if cfg.get("closing"):
            closing = f'<p class="closing">{esc(cfg["closing"])}</p>'
        # closing is portrait only: fail loud, never drop it on a square card
    elif cfg.get("closing"):
        raise SystemExit('before-after: "closing" needs "height": 1350')

    rows = "".join(
        f'<div class="row"><div class="old"{anim(ROW_MS + i * ROW_STEP, BEAT)} '
        f'style="transform:{TILTS[i % len(TILTS)]}">{esc(x)}</div></div>'
        for i, x in enumerate(before["steps"])
    )
    nodes = "".join(
        f'<div class="pnode"{anim(NODE_MS + i * NODE_STEP, BEAT)}><span class="dot"></span>'
        f'<div class="ncard"><span>{esc(x if isinstance(x, str) else x["label"])}</span>'
        + (f'<span class="tag">{esc(x["tag"])}</span>' if isinstance(x, dict) and x.get("tag") else "")
        + "</div></div>"
        for i, x in enumerate(after["steps"])
    )

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
/* WRAP RULE: text-wrap INHERITS, so declaring balance on the root gives every
   descendant even line lengths and no orphans - a 4-word chip breaks 2+2, not
   3+1 ("Clay to LinkedIn / Ads"). Real paragraphs override to `pretty` below,
   which prevents orphans without forcing even lines. Set here rather than on a
   list of classes so a new element cannot silently miss it. */
#slide-1{{text-wrap:balance;width:1080px;height:{H}px;background:{T['canvas']};color:{T['text']};
  font-family:'{font_family}',sans-serif;display:flex;flex-direction:column;overflow:hidden;
  font-synthesis:none;-webkit-font-smoothing:antialiased;}}
.rail{{flex:0 0 62px;display:grid;place-items:center;padding:22px 0;border-bottom:1px solid {brandkit.tint(T['accent'], .38)};}}
.rail p{{color:{T['accent']};font-size:15px;line-height:1;letter-spacing:.14em;font-weight:700;text-align:center;}}
.split{{flex:1;min-height:0;position:relative;display:grid;grid-template-columns:1fr 1fr;
  /* 72px, not 54px: the centre gap marker needs guaranteed clearance on BOTH
     sides regardless of column content length. At 54px it occluded the first
     word of the adjacent card. Widened by the taste loop's fixer in the run
     that converged at 9.27. */
  gap:72px;padding:0 52px 18px;}}
.rule{{position:absolute;z-index:5;left:calc(50% - 1px);top:0;bottom:18px;width:2px;
  background:{T['accent']};}}
.col{{min-width:0;padding:26px 0 0;display:grid;grid-template-rows:auto 1fr auto;position:relative;}}
.pill{{width:max-content;height:38px;padding:0 20px;display:inline-grid;place-items:center;
  border-radius:999px;font-size:18px;line-height:1;letter-spacing:.08em;font-weight:700;}}
.col-a .pill{{color:{T['canvas']};background:{T['sub']};}}
.col-b .pill{{color:{T['on_accent']};background:{T['accent']};}}
.sub{{max-width:380px;margin-top:20px;color:{T['sub']};font-size:24px;line-height:1.24;font-weight:600;}}
.hero{{margin-top:16px;font-size:{cfg.get('hero_size', 60)}px;line-height:.92;letter-spacing:-.035em;
  font-weight:700;color:{T['text']};}}
.hero .g{{color:{T['accent']};}}
.stack,.pipe{{min-height:0;display:flex;flex-direction:column;justify-content:center;padding:14px 0;}}
/* The connector is drawn on an inner wrapper that shrink-wraps the nodes. Drawn on
   the centring container instead, it ran the full column height and trailed off
   past the last node into empty space. */
.inner{{position:relative;display:flex;flex-direction:column;gap:16px;}}
.row{{display:flex;align-items:center;}}
.old{{width:94%;min-height:86px;padding:16px 22px;display:flex;align-items:center;
  color:{T['sub']};background:{T['surface']};border:1px solid {T['surface_border']};border-radius:12px;
  font-size:26px;line-height:1.12;font-weight:600;text-decoration-line:line-through;
  text-decoration-color:{T['muted']};text-decoration-thickness:2px;text-decoration-skip-ink:none;}}
.pipe .inner::before{{content:"";position:absolute;z-index:0;left:15px;top:43px;bottom:43px;width:2px;
  background:{T['accent']};opacity:.55;}}
.pnode{{display:grid;grid-template-columns:32px 1fr;gap:14px;align-items:center;z-index:1;}}
.dot{{width:13px;height:13px;justify-self:center;border-radius:50%;background:{T['accent']};}}
.ncard{{min-height:86px;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;
  gap:12px;background:{T['island_bg']};border:1px solid {T['accent']};border-radius:12px;
  color:{T['text']};font-size:25px;line-height:1.12;font-weight:600;}}
.pnode:last-child .dot{{border:2px solid {T['accent']};background:{T['canvas']};
  outline:7px solid {brandkit.tint(T['accent'], .18)};}}
.pnode:last-child .ncard{{border:2px solid {T['accent']};}}
.tag{{color:{T['accent']};font-size:19px;line-height:1;font-weight:700;white-space:nowrap;}}
.cap{{align-self:end;padding-bottom:14px;font-size:23px;line-height:1.2;font-weight:600;}}
/* Space Grotesk ships no italic face and font-synthesis is off, so italic would
   render upright. Weight and colour carry the emphasis instead. */
.col-a .cap{{color:{T['sub']};font-weight:500;}}
.col-b .cap{{color:{T['accent']};}}
.foot{{flex:0 0 78px;padding:15px 52px;display:grid;grid-template-columns:1fr auto;align-items:center;
  border-top:1px solid {T['accent']};background:{T['canvas']};}}
.g{{color:{T['accent']};}}
{motion_css}
{mobile_css}
{pack_css}{final_css}{node_css}{portrait_css}{solo_css}
.hero-a{{color:{T['sub']};}}

/* ---- BRUTALIST treatment (before/after): "treatment":"brutalist" ----
   Matches the dark cyber-brutalism reference: hard rectangles, mono telemetry,
   accent slash markers, no glow. Same palette and face as the default posture. */
.brut .rail p{{font-family:'{mono_family}',monospace;letter-spacing:.05em;}}
.brut .rail p::before{{content:"// ";color:{T['accent']};}}
.brut .rail{{border-bottom-width:2px;}}
.brut .pill{{border-radius:0;font-family:'{mono_family}',monospace;letter-spacing:.04em;}}
.brut .col-a .pill{{background:transparent;color:{T['sub']};border:1px solid {T['sub']};}}
.brut .col-b .pill{{background:transparent;color:{T['accent']};border:1px solid {T['accent']};}}
.brut .sub{{font-family:'{mono_family}',monospace;font-size:21px;line-height:1.35;}}
/* -.04em, not -.05em: both sit inside industrial-brutalist-ui's -.03 to -.06
   macro range, but -.05 trips impeccable's extreme-negative-tracking. This is
   the value where the skill and the detector agree. */
.brut .hero{{letter-spacing:-.04em;}}
.brut .old{{border-radius:0;transform:none !important;width:100%;
  text-decoration-thickness:3px;}}
.brut .ncard{{border-radius:0;}}
.brut .dot{{border-radius:0;}}
.brut .tag{{font-family:'{mono_family}',monospace;font-weight:400;}}
.brut .cap{{font-family:'{mono_family}',monospace;font-size:20px;line-height:1.4;}}
.brut .old{{border-color:{T['sub']};text-decoration-thickness:2px;text-decoration-color:{T['sub']};}}
.brut .rail p{{color:{T['sub']};}}
.brut .rail{{border-bottom-color:{T['accent']};}}
.brut .rule{{bottom:0;}}
.brut .cap{{font-weight:700;text-wrap:balance;}}
.brut .foot{{border-top-width:2px;border-top-color:{T['accent']};}}
.brut .seed{{font-family:'{mono_family}',monospace;}}
.gapmark{{position:absolute;z-index:6;left:50%;top:50%;
  transform:translate(-50%,-50%) rotate(-90deg);
  display:flex;align-items:center;gap:12px;padding:10px 16px;white-space:nowrap;
  background:{T['canvas']};border:2px solid {T['accent']};}}
.gm-t{{font-size:19px;font-weight:700;letter-spacing:.14em;color:{T['accent']};}}
.gm-a{{font-size:20px;font-weight:700;color:{T['accent']};line-height:1;}}
.brut .gapmark{{border-radius:0;}}
.brut .gm-t{{font-family:'{mono_family}',monospace;}}
{brandkit.footer_lock(T, F, 1.0)['css']}.foot.foot{{flex-basis:104px;padding-top:0;padding-bottom:0;}}
</style></head><body><div id="slide-1" class="{brut}">
<div class="rail"><p>{esc(cfg['eyebrow'])}</p></div>
<main class="split">
  <div class="rule"></div>{gap_marker}
  <section class="col col-a">
    <div><span class="pill">{esc(before['pill'])}</span>
      {left_head}</div>
    <div class="stack"><div class="inner">{rows}</div></div>
    <p class="cap">{esc(before.get('caption', ''))}</p>
  </section>
  <section class="col col-b">
    <div><span class="pill">{esc(after['pill'])}</span>
      <p class="hero">{esc(after['hero'])}</p></div>
    <div class="pipe"><div class="inner">{nodes}</div></div>
    <p class="cap">{esc(after.get('caption', ''))}</p>
  </section>
</main>
{closing}<div class="{foot_cls}">{brandkit.footer_lock(T, F, 1.0, tag=ft)['html']}</div>
</div>{runtime}</body></html>"""


def self_test():
    """Two-sided: height absent keeps the square card; height 1350 switches the profile."""
    global BRAND
    BRAND = brandkit.load(None)
    base = {"format": "card-before-after", "eyebrow": "E", "before": {"pill": "A", "subhead": "s", "steps": ["x", "y"], "caption": "c"},
            "after": {"pill": "B", "hero": "h", "steps": ["p", "q", "r"], "caption": "d"}}
    sq = build(base, "dark", False)
    assert "height:1080px" in sq and 'id="slide-1" class=""' in sq and 'class="foot"' in sq, "square default changed"
    assert "subgrid" not in sq and "foot.solo" not in sq and 'class="lf-seed"' in sq, "portrait/footer CSS leaked into the square card"
    po = build(dict(base, height=PORTRAIT_H, footer_tag="", closing="z"), "dark", False)
    assert "height:1350px" in po and 'class="brut"' in po and "subgrid" in po, "1350 did not switch the profile"
    assert ".rail p{font-size:30px;}" in po, "portrait must default to the phone-size text"
    assert 'class="lf-seed"' in po and "foot solo" not in po, "empty footer_tag must keep the locked layout-A footer"
    assert 'class="closing">z<' in po, "closing line missing at 1350"
    assert 'class=""' in build(dict(base, height=PORTRAIT_H, treatment="default"), "dark", False), "explicit treatment must win"
    assert ".rail p{font-size:30px;}" not in build(dict(base, height=PORTRAIT_H, mobile=False), "dark", False), "explicit mobile=False must win"
    assert '<div class="lf-seed">T</div>' in build(dict(base, footer_tag="T"), "dark", False), "footer_tag text must replace the tagline"
    for bad in (dict(base, height=1200), dict(base, closing="z")):
        try:
            build(bad, "dark", False)
        except SystemExit:
            continue
        raise AssertionError("an unsupported height / square closing must fail loud")
    print("PASS before-after-card self-test (square default, 1350 profile, footer_tag, closing, fail-loud)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--theme", choices=["light", "dark"], default="dark")
    ap.add_argument("--motion", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--brand", help="path to brand.json")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not (a.config and a.out):
        ap.error("--config and --out are required (or --self-test)")
    global BRAND
    BRAND = brandkit.load(a.brand)
    cfg = json.loads(pathlib.Path(a.config).read_text())
    pathlib.Path(a.out).write_text(build(cfg, a.theme, a.motion))
    print(f"wrote {a.out} ({a.theme}{', motion' if a.motion else ''})")


if __name__ == "__main__":
    main()
