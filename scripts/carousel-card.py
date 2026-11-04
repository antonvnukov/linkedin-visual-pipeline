#!/usr/bin/env python3
"""
carousel-card.py — config-driven LinkedIn CAROUSEL (N slides -> PDF).

Two families, chosen automatically from the config:

1. SQUARE family (default) — 1080x1080, always the DARK theme from brand.json.
   Slide types: title | statement | list | split | versus | close.
   Chrome: NN/NN pager + "Swipe ->". Unchanged legacy behaviour.

2. PORTRAIT family — triggered by "size":"portrait" OR a "wordmark" key.
   1080x1350, PER-SLIDE "theme":"light"|"dark", Space Grotesk by default,
   name wordmark footer (88px, no employer branding), no pager.
   Slide types: hook | statement | bignum | quote | cta (+ statement/list reuse).
   Both per-slide themes read their tokens from brand.json — no palette lives here.

Config knobs (all optional; both families default to Space Grotesk):
  "font": "<family>"           one-off override; default: brand.font.family
  "font_weights": "400;500;600;700"  weights for the @import
  "size": "square" | "portrait" | {"w":1080,"h":1350}
  "wordmark": "<name>"         per-slide name footer (default: brand.footer.name)
  "footer_seed": "<tagline>"   default: brand.footer.tagline
  "show_slide_count": true      adds NN / NN after the seed line
  per-slide "theme": "light" | "dark"   (portrait family only; default dark)

Accent words via *asterisks*. Icons (square family): gears | fire | sprinkler.

Usage: python3 carousel-card.py --config carousel.json --out /tmp/c.html
Then:  node capture.js --html /tmp/c.html --slides <N> --outdir <dir> --scale 2
"""
import argparse, base64, html, json, pathlib, re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit

BRAND = None
L = D = None          # light / dark token maps, filled by _bind()
ACCENT = None         # dark accent, used by the inline SVG icons


def _bind(brand):
    global BRAND, L, D, ACCENT
    BRAND = brand
    L, D = brandkit.theme(brand, "light"), brandkit.theme(brand, "dark")
    ACCENT = D["accent"]

def esc(s):
    s = html.escape(str(s), quote=False).replace("'", "’")
    return re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', s)

def font_bits(cfg):
    """Family + @import, both from brand.json (cfg is a deliberate one-off override)."""
    fam, _weights, imp = brandkit.font(BRAND, cfg)
    return fam, imp

def canvas_bits(cfg):
    """Config-driven canvas -> (W, H). Default = legacy square 1080x1080."""
    size = cfg.get("size", "square")
    if isinstance(size, dict):
        return int(size["w"]), int(size["h"])
    if size == "portrait":
        return 1080, 1350
    return 1080, 1080

def icon(name, size=64):
    s = f'width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'
    if name == "gears":
        return (f'<svg {s}><circle cx="12" cy="12" r="3"/>'
                '<path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>')
    if name == "fire":
        return (f'<svg {s}><path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 11-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 002.5 2.5z"/></svg>')
    if name == "sprinkler":
        return (f'<svg {s}><path d="M6 21h12"/><path d="M12 21v-4"/>'
                '<path d="M12 17C11 12 8 9.5 4.5 8"/><path d="M12 17C13 12 16 9.5 19.5 8"/>'
                '<path d="M12 17C12 12.5 12 9 12 5.5"/></svg>')
    return ""

def kicker(txt):
    return f'<div class="kicker">{esc(txt)}</div>' if txt else ""

def counter(i, n):
    return f'<div class="count">{i:02d} <span class="cslash">/</span> {n:02d}</div>'

ARROW = "&rarr;"

# ---------------------------------------------------------------------------
# SQUARE family (legacy — unchanged output)
# ---------------------------------------------------------------------------
def render_slide(sl, i, n):
    t = sl.get("type", "statement")
    cnt = counter(i, n)
    if t == "title":
        return (f'<div class="s title">{kicker(sl.get("kicker",""))}'
                f'<h1 class="big">{esc(sl["headline"])}</h1>'
                f'<div class="subhead">{esc(sl.get("subhead",""))}</div>'
                f'<div class="swipe">Swipe {ARROW}</div>{cnt}</div>')
    if t == "statement":
        return (f'<div class="s statement">{kicker(sl.get("kicker",""))}'
                f'<h2>{esc(sl["headline"])}</h2>'
                f'<p>{esc(sl.get("body",""))}</p>{cnt}</div>')
    if t == "list":
        items = "".join(f'<div class="li"><span class="dot"></span><span>{esc(x)}</span></div>' for x in sl.get("items", []))
        ic = f'<div class="topicon">{icon(sl["icon"],76)}</div>' if sl.get("icon") else ""
        return (f'<div class="s list">{ic}{kicker(sl.get("kicker",""))}'
                f'<h2>{esc(sl["headline"])}</h2><div class="items">{items}</div>{cnt}</div>')
    if t == "split":
        return (f'<div class="s split">{kicker(sl.get("kicker",""))}<h2>{esc(sl["headline"])}</h2>'
                f'<div class="cols"><div class="col bad"><div class="col-b">{esc(sl.get("left",""))}</div></div>'
                f'<div class="col good"><div class="col-b">{esc(sl.get("right",""))}</div></div></div>{cnt}</div>')
    if t == "versus":
        li = f'<div class="vicon">{icon(sl["left_icon"],84)}</div>' if sl.get("left_icon") else ""
        ri = f'<div class="vicon">{icon(sl["right_icon"],84)}</div>' if sl.get("right_icon") else ""
        hd = f'<h2>{esc(sl["headline"])}</h2>' if sl.get("headline") else ""
        return (f'<div class="s versus">{hd}<div class="cols">'
                f'<div class="col"><div class="vt">{esc(sl.get("left_title",""))}</div>{li}<div class="col-b">{esc(sl.get("left",""))}</div></div>'
                f'<div class="col"><div class="vt g">{esc(sl.get("right_title",""))}</div>{ri}<div class="col-b">{esc(sl.get("right",""))}</div></div>'
                f'</div>{cnt}</div>')
    if t == "close":
        ft = f'<div class="footer">{esc(sl.get("footer",""))}</div>' if sl.get("footer") else ""
        return (f'<div class="s close"><h1 class="big">{esc(sl["headline"])}</h1>'
                f'<p>{esc(sl.get("body",""))}</p>{ft}{cnt}</div>')
    return f'<div class="s">{cnt}</div>'

def build_square(cfg):
    fam, imp = font_bits(cfg)
    W, H = canvas_bits(cfg)
    slides = cfg["slides"]
    n = len(slides)
    body = "".join(f'<div class="slide" id="slide-{i+1}">{render_slide(sl, i+1, n)}</div>'
                   for i, sl in enumerate(slides))
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{imp}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:{D['canvas']};}}
.slide{{width:{W}px;height:{H}px;background:{D['canvas']};text-wrap:balance;font-family:'{fam}',sans-serif;color:{D['text']};
  position:relative;overflow:hidden;}}
.s{{position:absolute;inset:0;padding:96px;display:flex;flex-direction:column;}}
.g{{color:{ACCENT};}}
.kicker{{font-size:20px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:{ACCENT};margin-bottom:28px;}}
h1.big{{font-size:82px;font-weight:800;letter-spacing:-0.03em;line-height:1.02;max-width:900px;}}
h2{{font-size:64px;font-weight:800;letter-spacing:-0.02em;line-height:1.05;max-width:880px;}}
.subhead{{margin-top:26px;font-size:32px;font-weight:500;color:{D['sub']};}}
p{{margin-top:28px;font-size:34px;font-weight:500;color:{D['sub']};line-height:1.35;max-width:820px;}}
.count{{position:absolute;right:96px;bottom:80px;font-size:20px;font-weight:700;letter-spacing:0.08em;color:rgba(255,255,255,0.34);}}
.count .cslash{{color:rgba(255,255,255,0.16);}}
.swipe{{position:absolute;left:96px;bottom:80px;font-size:22px;font-weight:600;color:{ACCENT};}}
.footer{{margin-top:auto;font-size:22px;font-weight:600;color:{D['sub']};}}
.footer{{}}
/* title + statement + close: vertically centered */
.title,.statement,.close{{justify-content:center;}}
.close .footer{{margin-top:48px;color:{D['text']};}}
/* list */
.list{{justify-content:center;}}
.topicon{{margin-bottom:34px;}}
.items{{margin-top:44px;display:flex;flex-direction:column;gap:24px;}}
.li{{display:flex;align-items:center;gap:22px;font-size:44px;font-weight:700;}}
.li .dot{{width:16px;height:16px;border-radius:50%;background:{ACCENT};flex-shrink:0;}}
/* split + versus columns */
.split,.versus{{justify-content:center;}}
.split h2,.versus h2{{margin-bottom:56px;}}
.cols{{display:flex;gap:28px;}}
.col{{flex:1;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.09);border-radius:24px;
  padding:44px 38px;display:flex;flex-direction:column;gap:20px;min-height:280px;}}
.col-b{{font-size:34px;font-weight:600;line-height:1.3;color:{D['text']};}}
.split .col.bad .col-b{{color:{D['sub']};}}
.split .col.good{{border-color:rgba(3,208,140,0.5);}}
.split .col.good .col-b{{color:{ACCENT};}}
.versus .col{{min-height:400px;justify-content:center;align-items:flex-start;gap:28px;}}
.vt{{font-size:24px;font-weight:800;letter-spacing:0.02em;text-transform:uppercase;color:{D['sub']};}}
.vt.g{{color:{ACCENT};}}
.vicon{{margin:6px 0;}}

</style></head><body>{body}</body></html>"""

# ---------------------------------------------------------------------------
# PORTRAIT family (light/dark per slide, config font, name wordmark)
# ---------------------------------------------------------------------------
_FOOT = {}   # brandkit.footer() of the current build, set in build()


def wordmark_foot(name, avatar_uri="", seed="", i=0, n=0, show_count=False):
    if not name:
        return ""
    # Locked footer (brandkit.footer_lock, layout A): name with the site under it, tagline right.
    site = f'<span class="psite">{esc(_FOOT.get("site", ""))}</span>' if _FOOT.get("site") else ""
    who = f'<span class="pwho"><span>{esc(name)}</span>{site}</span>'
    if avatar_uri:
        mark = f'<span class="pavatar"><img src="{avatar_uri}" alt=""/></span>{who}'
    else:
        mark = f'<span class="pdot"></span>{who}'
    right = ""
    if seed:
        # the brand tagline is composed by brandkit; a config "footer_seed" is plain text
        seed_markup = brandkit.seed_html(_FOOT) if seed == _FOOT.get("_default_seed") else esc(seed)
        right += f'<div class="pseed">{seed_markup}</div>'
    if show_count and i and n:
        right += f'<div class="pcount">{i:02d} / {n:02d}</div>'
    right = f'<div class="pfoot-right">{right}</div>' if right else ""
    return f'<div class="pfoot"><div class="pmark">{mark}</div>{right}</div>'

def flow_row(items):
    if not items:
        return ""
    nodes = '<span class="parrow">&darr;</span>'.join(f'<span class="pnode">{esc(x)}</span>' for x in items)
    return f'<div class="pflow">{nodes}</div>'

def chips_row(items):
    if not items:
        return ""
    pills = "".join(f'<span class="pchip">{esc(x)}</span>' for x in items)
    return f'<div class="pchips">{pills}</div>'

def dot_field(filled, total=60, ):
    """A grid of `total` dots with the first `filled` inked.

    Deliberately NOT a magnitude chart. The post it was built for contrasts 30
    searches/mo against 30,000, a 1000x ratio no grid can draw honestly; drawing
    it not-to-scale would be a lying chart. Both panes therefore get an EQUAL
    grid and the dots show INTENT DENSITY (how many of those searchers are ready
    to buy), which is the argument being made. The volumes stay as labels.
    """
    return "".join(f'<span class="dmdot{" on" if i < filled else ""}"></span>'
                   for i in range(total))

def versus_cols(sl):
    """Two labelled lanes for an old-way / new-way contrast.

    A contrast is not a flow and not a list: `flow` asserts sequence and `list`
    asserts one set. Reach for this only when the point is that the LEFT column
    is what the reader currently measures and the RIGHT is what they don't.
    The left lane renders muted on purpose — it is the column being retired.
    """
    def col(d, accent):
        items = "".join(f'<div class="pvli">{esc(x)}</div>' for x in d.get("items", []))
        return (f'<div class="pvcol{" acc" if accent else ""}">'
                f'<div class="pvt">{esc(d.get("title", ""))}</div>{items}</div>')
    return (f'<div class="pversus">{col(sl.get("left") or {}, False)}'
            f'{col(sl.get("right") or {}, True)}</div>')

def portrait_content(sl, name, avatar_uri="", footer_seed="", i=0, n=0, show_count=False, brut=False):
    t = sl.get("type", "statement")
    corners = '<span class="pcorner l"></span><span class="pcorner r"></span>' if brut else ""
    foot = wordmark_foot(name, avatar_uri, footer_seed, i, n, show_count)
    eye = f'<div class="peyebrow">{esc(sl["kicker"])}</div>' if sl.get("kicker") else ""
    if t == "hook":
        inner = (f'{eye}<h1 class="phook">{esc(sl["headline"])}</h1>'
                 f'<div class="psub">{esc(sl.get("subhead",""))}</div>')
    elif t == "bignum":
        big = f'<div class="pbignum">{esc(sl.get("bignum",""))}</div>'
        inner = (f'{eye}<h2 class="ph2 narrow">{esc(sl["headline"])}</h2>'
                 f'<div class="pcopy narrow">{esc(sl.get("body",""))}</div>')
        return f'{big}<div class="pbody">{inner}</div>{foot}'
    elif t == "quote":
        inner = (f'<div class="paccent-line"></div>'
                 f'<div class="pquote">{esc(sl.get("quote",""))}</div>'
                 f'<div class="psub">{esc(sl.get("subhead",""))}</div>'
                 f'{flow_row(sl.get("flow", []))}')
    elif t == "cta":
        v = sl.get("verdict") or {}
        verdict = (f'<div class="pverdict">'
                   f'<div class="pvwin">{esc(v.get("win", ""))}</div>'
                   f'<div class="pvop">{esc(v.get("op", "&gt;"))}</div>'
                   f'<div class="pvlose">{esc(v.get("lose", ""))}</div></div>') if v else ""
        btn = f'<div class="pcta-btn">{esc(sl.get("button",""))}</div>' if sl.get("button") else ""
        src = (f'<div class="psource">{esc(sl.get("source",""))}</div>'
               if sl.get("source") and sl.get("show_source_on_slide") else "")
        inner = (f'<h2 class="ph2">{esc(sl["headline"])}</h2>'
                 f'<div class="pcopy white">{esc(sl.get("body",""))}</div>{verdict}{btn}{src}')
    elif t == "list":
        items = "".join(f'<div class="pli"><span class="pdot2"></span><span>{esc(x)}</span></div>' for x in sl.get("items", []))
        inner = f'{eye}<h2 class="ph2">{esc(sl["headline"])}</h2><div class="pitems">{items}</div>'
    elif t == "dotmatrix":
        def pane(d):
            return (f'<div class="dmpane">'
                    f'<div class="dmgrid">{dot_field(int(d.get("filled", 0)), int(d.get("total", 60)))}</div>'
                    f'<div class="dmnum">{esc(d.get("value", ""))}</div>'
                    f'<div class="dmcap">{esc(d.get("caption", ""))}</div></div>')
        inner = (f'{eye}<h2 class="ph2 vs">{esc(sl["headline"])}</h2>'
                 f'<div class="dmwrap">{pane(sl.get("left") or {})}{pane(sl.get("right") or {})}</div>')
    elif t == "versus":
        inner = (f'{eye}<h2 class="ph2 vs">{esc(sl["headline"])}</h2>'
                 f'{versus_cols(sl)}')
    else:  # statement (default)
        inner = (f'{eye}<h2 class="ph2">{esc(sl["headline"])}</h2>'
                 f'<div class="pcopy">{esc(sl.get("body",""))}</div>'
                 f'{chips_row(sl.get("chips", []))}')
    return f'<div class="pbody">{inner}{corners}</div>{foot}'

def build_portrait(cfg):
    fam, imp = font_bits(cfg)
    mono_fam, _ = brandkit.mono(BRAND)
    mono_fam = mono_fam or fam
    W, H = canvas_bits(cfg)
    FT = brandkit.footer(BRAND, cfg)
    FT["_default_seed"] = brandkit.seed_html(FT)
    _FOOT.clear(); _FOOT.update(FT)
    name = cfg.get("wordmark", FT["name"])
    # The avatar + tagline footer is the LOCKED recognition layer (see formats.md).
    # This family used to show it only when a config named an `avatar` path, so
    # every carousel shipped with the fallback dot while the card formats showed
    # Anton's face. Fall back to the brand's own avatar, which brandkit already
    # resolved to a data URI, and keep the config key as a deliberate override.
    avatar_uri = FT["avatar"]
    av = cfg.get("avatar")
    if av:
        p = pathlib.Path(av).expanduser()
        if p.exists():
            avatar_uri = "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()
    slides = cfg["slides"]
    footer_seed = cfg.get("footer_seed", FT["_default_seed"])
    show_count = bool(cfg.get("show_slide_count", False))
    brut_cls = " brut" if cfg.get("treatment") == "brutalist" else ""
    body = "".join(
        f'<div class="slide {sl.get("theme","dark")}{brut_cls}" id="slide-{i+1}">{portrait_content(sl, name, avatar_uri, footer_seed, i+1, len(slides), show_count, bool(brut_cls))}</div>'
        for i, sl in enumerate(slides))
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{imp}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:{L['border']};}}
.slide{{width:{W}px;height:{H}px;font-family:'{fam}',sans-serif;text-wrap:balance;position:relative;overflow:hidden;
  display:flex;flex-direction:column;-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;}}
.slide.dark{{--bg:{D['canvas']};--tx:{D['text']};--mut:{D['sub']};--eye:{D['accent']};--acc:{D['accent']};--bd:{D['hairline']};--dot:{D['accent']};--chip:{D['chip']};background:{D['canvas']};}}
.slide.light{{--bg:{L['canvas']};--tx:{L['text']};--mut:{D['sub']};--eye:{L['accent']};--acc:{L['accent']};--bd:{L['border']};--dot:{L['accent']};--chip:{D['text']};background:{L['canvas']};}}
.pbody{{flex:1;display:flex;flex-direction:column;justify-content:flex-start;padding:118px 90px 0 90px;position:relative;z-index:2;}}
.g{{color:var(--acc);}}
.peyebrow{{font-size:21px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:var(--eye);margin-bottom:52px;}}
.phook{{font-size:120px;font-weight:700;line-height:1.04;letter-spacing:-0.03em;color:var(--tx);text-wrap:balance;max-width:940px;}}
.ph2{{font-size:92px;font-weight:700;line-height:1.08;letter-spacing:-0.02em;color:var(--tx);text-wrap:balance;}}
.ph2.narrow{{max-width:760px;}}
.psub{{font-size:42px;font-weight:500;color:var(--mut);margin-top:48px;line-height:1.4;max-width:880px;text-wrap:pretty;}}
.pcopy{{font-size:37px;font-weight:500;line-height:1.5;color:var(--tx);margin-top:48px;max-width:880px;text-wrap:pretty;}}
.pcopy.narrow{{max-width:720px;}}
.pcopy.white{{font-size:38px;line-height:1.5;color:var(--tx);}}
/* oversized number call-out */
.pbignum{{position:absolute;right:60px;bottom:150px;font-size:460px;font-weight:700;line-height:0.8;
  color:var(--acc);letter-spacing:-0.04em;opacity:0.92;z-index:1;}}
/* transition quote */
.paccent-line{{width:120px;height:2px;background:var(--acc);margin-bottom:56px;}}
.pquote{{font-size:64px;font-weight:700;line-height:1.24;letter-spacing:-0.01em;color:var(--tx);max-width:880px;text-wrap:balance;}}
.quote .psub,.pquote + .psub{{max-width:760px;font-size:26px;margin-top:40px;line-height:1.45;}}
/* cta */
.pcta-btn{{display:inline-flex;align-self:flex-start;align-items:center;gap:8px;background:{L['accent']};color:{D['text']};
  font-size:26px;font-weight:700;letter-spacing:0.01em;padding:24px 42px;border-radius:12px;margin-top:64px;}}
.psource{{font-size:18px;font-weight:500;color:var(--mut);margin-top:44px;}}
/* portrait list */
.pitems{{margin-top:40px;display:flex;flex-direction:column;gap:22px;}}
.pli{{display:flex;align-items:center;gap:20px;font-size:42px;text-wrap:balance;font-weight:600;color:var(--tx);}}
.pli .pdot2{{width:14px;height:14px;border-radius:50%;background:var(--acc);flex-shrink:0;}}
/* platform chips (part-to-whole call-out, replaces a bare bignum) */
.pchips{{display:flex;gap:16px;margin-top:60px;}}
.pchip{{flex:1;text-align:center;font-size:31px;font-weight:600;color:var(--tx);background:var(--chip);text-wrap:balance;
  border:1.5px solid var(--acc);border-radius:999px;padding:22px 14px;line-height:1;}}
/* dot-matrix panes. EQUAL grids on both sides on purpose: see dot_field().
   Inked dots read as intent density, the volumes are labels, and no dot stands
   for a fixed quantity - so nothing here can be misread as a scaled chart. */
.dmwrap{{display:grid;grid-template-columns:1fr 1fr;gap:64px;margin-top:56px;}}
.dmgrid{{display:grid;grid-template-columns:repeat(10,1fr);gap:10px;margin-bottom:34px;}}
.dmdot{{width:100%;aspect-ratio:1;border-radius:50%;border:1.5px solid var(--bd);}}
.dmdot.on{{background:var(--acc);border-color:var(--acc);}}
/* Grotesk, not mono. A monospace face gives the thousands comma a full
   character cell, so "30,000" rendered as "30 , 000" and read like a typo.
   The references use mono for CODES and readouts (SCN_01, DB.40), never for
   formatted quantities, so this is closer to them, not further. */
.dmnum{{font-size:50px;font-weight:700;letter-spacing:-.03em;
  color:var(--tx);line-height:1;}}
.dmcap{{margin-top:14px;font-size:25px;font-weight:600;line-height:1.25;color:var(--mut);text-wrap:balance;}}
/* versus lanes: old-way (muted) | new-way (accent), split by a hairline.
   Deliberately NOT a table: no cell borders, no header row background. The
   contrast carries in colour weight, so it stays readable at feed size. */
.pversus{{display:grid;grid-template-columns:1fr 1fr;margin-top:56px;}}
.pvcol{{padding-right:44px;}}
.pvcol.acc{{padding:0 0 0 44px;border-left:1px solid var(--bd);}}
.pvt{{font-size:24px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
  color:var(--mut);margin-bottom:34px;}}
.pvcol.acc .pvt{{color:var(--acc);}}
.pvli{{font-size:35px;font-weight:600;line-height:1.3;padding:23px 0;color:var(--mut);text-wrap:balance;}}
.pvcol.acc .pvli{{color:var(--tx);}}
.pvli + .pvli{{border-top:1px solid var(--bd);}}
.ph2.vs{{font-size:76px;}}
/* transition flow: vertical sequence (nodes white, down-arrows accent) */
.pflow{{display:flex;flex-direction:column;align-items:flex-start;gap:12px;margin-top:48px;}}
.pnode{{font-size:37px;font-weight:600;color:var(--tx);line-height:1.15;text-wrap:balance;}}
.parrow{{font-size:22px;font-weight:700;color:var(--acc);line-height:1;padding-left:6px;}}
/* The post's thesis is an INEQUALITY, so it is set as one rather than as a
   footnote under the CTA. Stacked because a portrait canvas cannot hold both
   sides on one line at a readable size; the operator is the pivot the eye
   lands on, and only the winning side carries the accent. */
.pverdict{{margin-top:52px;display:flex;flex-direction:column;align-items:flex-start;gap:6px;}}
.pvwin,.pvlose{{font-size:38px;font-weight:700;line-height:1.15;letter-spacing:-.02em;}}
.pvwin{{color:var(--acc);}}
.pvlose{{color:var(--mut);}}
.pvop{{font-size:46px;font-weight:700;line-height:1;color:var(--acc);padding-left:2px;}}
/* wordmark footer */
.pfoot{{height:88px;flex-shrink:0;display:flex;align-items:center;padding:15px 90px;border-top:1px solid var(--bd);}}
.pmark{{display:flex;align-items:center;gap:14px;font-weight:700;font-size:22px;letter-spacing:0.01em;color:var(--tx);}}
.pmark .pdot{{width:12px;height:12px;border-radius:3px;background:var(--dot);}}
.pmark .pavatar{{width:62px;height:62px;border-radius:50%;overflow:hidden;flex-shrink:0;}}
.pwho{{display:flex;flex-direction:column;line-height:1.15;}}
.psite{{font-size:17px;font-weight:500;letter-spacing:0;color:var(--mut);margin-top:2px;}}
.pmark .pavatar img{{width:100%;height:100%;object-fit:cover;display:block;}}
.pfoot-right{{margin-left:auto;display:flex;align-items:center;gap:24px;}}
.pseed{{font-size:21px;font-weight:700;color:var(--tx);white-space:nowrap;}}
.pseed .g{{color:var(--acc);}}
.pcount{{border-left:1px solid var(--bd);padding-left:24px;font-size:20px;font-weight:700;letter-spacing:0.04em;color:var(--mut);white-space:nowrap;}}

/* ---------------- BRUTALIST treatment: "treatment":"brutalist" ----------------
   Same face, same palette, opposite posture. The default portrait look is soft
   minimal (rounded chips, round dots, wide air). This strips the radius to zero,
   moves every LABEL to the mono face with a "/" section marker, boxes the chips
   and list rows in hairlines, and tightens the display tracking. Nothing here
   introduces a colour: the palette gate still sees only brand tokens. */
.brut .peyebrow{{font-family:'{mono_fam}',monospace;letter-spacing:.08em;margin-bottom:26px;}}
/* [BRACKETED LABELS] - ref20's [DELIVERY SYSTEMS] */
.brut .peyebrow::before{{content:"[ ";opacity:.5;}}
.brut .peyebrow::after{{content:" ]";opacity:.5;}}
.brut .pbody > .peyebrow{{padding-bottom:22px;border-bottom:1px solid var(--bd);}}
.brut .phook,.brut .ph2{{letter-spacing:-.045em;}}
.brut .psub,.brut .pcopy{{max-width:900px;}}
.brut .pchip{{border-radius:0;border:1.5px solid var(--bd);background:transparent;
  font-family:'{mono_fam}',monospace;font-size:25px;font-weight:400;padding:20px 14px;
  text-align:left;}}
.brut .pchips{{gap:0;}}
.brut .pchip + .pchip{{border-left:none;}}
.brut .dmdot{{border-radius:0;}}
.brut .dmgrid{{gap:7px;}}
/* NOT mono, for the same reason the base rule is not: a monospace comma gets
   a full cell and "30,000" reads as "30 , 000". The treatment overrode the
   base fix and reintroduced the defect. */
.brut .dmnum{{letter-spacing:-.04em;font-size:48px;}}
.brut .pli .pdot2{{border-radius:0;width:12px;height:12px;}}
.brut .pitems{{border-top:1px solid var(--bd);}}
.brut .pli{{padding:22px 0;border-bottom:1px solid var(--bd);}}
.brut .pvli{{border-radius:0;}}
.brut .pvt{{font-family:'{mono_fam}',monospace;}}
.brut .pcta-btn{{border-radius:0;font-family:'{mono_fam}',monospace;}}
.brut .pfoot{{border-top:2px solid var(--acc);}}
.brut .pcount,.brut .pseed{{font-family:'{mono_fam}',monospace;}}
.brut .dmcap{{font-family:'{mono_fam}',monospace;font-size:22px;line-height:1.35;}}
/* SPEC-SHEET LEADER LINES - ref20's "RAPID CELL..... 100%". The dots run from the
   end of the label to a right-aligned index, so a list reads as a parts schedule
   rather than bullets. `order` is what puts the pseudo-elements AFTER the label:
   ::before would otherwise render first, ahead of the marker. */
.brut .pitems{{counter-reset:li;}}
.brut .pli{{counter-increment:li;display:flex;align-items:baseline;gap:16px;}}
.brut .pli > .pdot2{{order:1;}}
.brut .pli > span:last-of-type{{order:2;flex:0 1 auto;}}
.brut .pli::before{{content:"";order:3;flex:1 1 auto;min-width:40px;
  border-bottom:3px dotted var(--bd);margin:0 4px 9px;}}
.brut .pli::after{{content:counter(li,decimal-leading-zero);order:4;flex:0 0 auto;
  font-family:'{mono_fam}',monospace;font-size:28px;font-weight:700;color:var(--acc);}}

/* CORNER REGISTRATION MARKS - ref29 frames its content this way. Not decoration
   here: they mark the live area, which is the whole point of the reference. */
.brut .pbody::before,.brut .pbody::after{{content:"";position:absolute;top:52px;
  width:20px;height:20px;border-top:2px solid var(--acc);}}
.brut .pbody::before{{left:46px;border-left:2px solid var(--acc);}}
.brut .pbody::after{{right:46px;border-right:2px solid var(--acc);}}

/* the pager reads as a code, mono and bracketed, without inventing fake telemetry */
.brut .pcount::before{{content:"[";opacity:.5;}}
.brut .pcount::after{{content:"]";opacity:.5;}}

/* ---- pushed harder: ground, weight, density ----
   Since 2026-09-28 (Anton D3) the light canvas IS hard white in brand.json, so
   this override is now a no-op kept only as the brutalist posture's guarantee. Rules double to 2px, the body tightens 22px, and
   the display tracking closes up. Registration marks gain their bottom pair so
   the live area is actually framed rather than hinted at. */
.brut.light{{background:#FFFFFF;--bg:#FFFFFF;}}
.brut .pbody{{padding-top:96px;}}
.brut .phook{{letter-spacing:-.055em;}}
.brut .ph2{{letter-spacing:-.05em;}}
.brut .pbody > .peyebrow{{border-bottom-width:2px;padding-bottom:20px;}}
.brut .pitems{{border-top-width:2px;}}
.brut .pli{{padding:19px 0;}}
.brut .pli:last-child{{border-bottom-width:2px;}}
.brut .pchip{{border-width:2px;}}
.brut .pversus .pvcol.acc{{border-left-width:2px;}}
.brut .pvli + .pvli{{border-top-width:2px;}}
.brut .pbody::before,.brut .pbody::after{{width:24px;height:24px;border-width:3px;}}
/* bottom pair, mirrored */
.brut .pcorner{{position:absolute;bottom:24px;width:24px;height:24px;
  border-bottom:3px solid var(--acc);}}
.brut .pcorner.l{{left:46px;border-left:3px solid var(--acc);}}
.brut .pcorner.r{{right:46px;border-right:3px solid var(--acc);}}
</style></head><body>{body}</body></html>"""

def build(cfg):
    if cfg.get("size") == "portrait" or cfg.get("wordmark") or any(
            s.get("type") in ("hook", "bignum", "quote", "cta") or s.get("theme") == "light"
            for s in cfg.get("slides", [])):
        return build_portrait(cfg)
    return build_square(cfg)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand", help="path to brand.json")
    a = ap.parse_args()
    _bind(brandkit.load(a.brand))
    cfg = json.loads(pathlib.Path(a.config).read_text())
    pathlib.Path(a.out).write_text(build(cfg))
    print(f"wrote {a.out} ({len(cfg['slides'])} slides)")

if __name__ == "__main__":
    main()
