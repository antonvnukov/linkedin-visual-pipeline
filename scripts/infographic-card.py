#!/usr/bin/env python3
"""
infographic-card.py — LinkedIn portrait infographic (1080x1350), config-driven.

A single-frame, dense reference sheet. Layout "spine": header -> a three-cell spec
strip -> a mono readout row -> N nodes (5 to 9) strung on ONE serpentine path that
turns alternately right and left -> a 0-to-1 threshold scale -> footer.

Use it when the content is a LIST THAT IS READ IN ORDER and each item carries a
two-part payload (a name and what to do about it): failure modes and their fixes,
steps and their owners. A card format cannot hold nine items; a carousel splits
the list across swipes, and the whole point of a reference sheet is that it is
one screen you save.

Design language: technical-drawing brutalism (visible grid, hairlines,
registration marks, mono telemetry, zero radius, one accent). Every colour comes
from brandkit; this file carries no literal hex (AGENTS.md rule 1).

Motion: `"motion": true` animates it with the shared runtime. The path DRAWS at
constant speed (data-draw) and each node lands when the pen reaches it, so the
reading order IS the animation. A card may carry a measured ease via `"ease":
"x1,y1,x2,y2"` and `"rise": <px>` (data-ease / data-rise on the root).

Usage:
  python3 infographic-card.py --config card.json --theme light --out /tmp/card.html
  python3 infographic-card.py --config card.json --theme light --motion --out /tmp/m.html

Accent: wrap words in *asterisks* in title / readout.
Config: examples/infographic-card.example.json
"""
import argparse, html, json, math, pathlib, re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandkit

SCRIPTS = pathlib.Path(__file__).resolve().parent
BRAND = None

W, H = 1080, 1350
M = 64                      # side margin
COMMON_KEYS = {
    "format", "layout", "theme", "motion", "motion_ms", "fps", "ease", "rise",
    "motion_return", "motion_live", "motion_morph",
    "meta_left", "meta_right", "title", "sub", "source", "$comment",
}
LAYOUT_KEYS = {
    "spine": {"cells", "readout", "nodes", "scale"},
    "cycle": {"steps", "core", "quote", "loop_note"},
    "decisions": {"decisions", "bands", "never", "motion_style"},
    "sort": {"columns", "readout"},
    "mega": {"sections", "legend"},
    "flow": {"stages", "legend", "rail", "height", "cta", "number_from"},
}
ALLOWED_KEYS = COMMON_KEYS | LAYOUT_KEYS["spine"]   # kept for the spine error message

# ---- geometry (CSS px). One place, so the static render, the motion render and
# the gates all see the same numbers.
Y_META = 56
Y_RULE = 88
Y_TITLE = 104
Y_SUB = 196
Y_CELLS, CELLS_H = 250, 134
Y_READOUT = 400
SY, SH = 442, 626            # spine box
Y_SCALE = 1098               # the 0-1 line
Y_SCALE_LABELS = 1140
Y_CAPTION = 1192
Y_FOOT_RULE = 1228
Y_FOOT = 1244

# ---- motion (ms). Durations follow the measured aimindset grammar the config
# names in "ease"/"rise": md 280 for every rise, lg 480 for section reveals,
# stagger 260 + n*150 inside a group.
MD, LG = 280, 480
T_META, T_TITLE, T_SUB = 200, 380, 640
T_CELLS = 900                 # + 260 + n*150
T_READOUT = 1750
T_FOOT = 1900
T_DRAW, D_DRAW = 2200, 6400
FIX_LAG = 150
T_SCALE = 8800
T_SCALE_LABELS = 9300         # + 260 + n*150
T_CAPTION = 10250
DISSOLVE_MS, DISSOLVE_D = 13000, 380


def esc(s):
    s = html.escape(str(s), quote=False).replace("'", "’")
    return re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', s)


def validate(cfg):
    layout = cfg.get("layout", "spine")
    if layout not in LAYOUT_KEYS:
        raise SystemExit(f"card-infographic: layout {layout!r} not built; built: {sorted(LAYOUT_KEYS)}")
    allowed = COMMON_KEYS | LAYOUT_KEYS[layout]
    unknown = sorted(set(cfg) - allowed)
    if unknown:
        # AGENTS.md rule 11: an unknown key must fail loud, never be dropped.
        raise SystemExit(f"card-infographic ({layout}): unknown config key(s) {unknown}. Allowed: {sorted(allowed)}")
    if layout == "cycle":
        return validate_cycle(cfg)
    if layout in ("decisions", "sort"):
        return validate_blocks(cfg, layout)
    if layout == "mega":
        return validate_mega(cfg)
    if layout == "flow":
        return validate_flow(cfg)
    n = len(cfg["nodes"])
    if not 5 <= n <= 9:
        raise SystemExit(f"card-infographic 'spine' renders 5 to 9 nodes, config has {n}")
    if len(cfg["cells"]) != 3:
        raise SystemExit(f"card-infographic renders exactly 3 spec cells, config has {len(cfg['cells'])}")
    for i, nd in enumerate(cfg["nodes"]):
        extra = set(nd) - {"name", "fix"}
        if extra or not nd.get("name") or not nd.get("fix"):
            raise SystemExit(f"node {i + 1}: needs exactly 'name' and 'fix', got {sorted(nd)}")
    sc = cfg.get("scale")
    if sc:
        extra = set(sc) - {"markers", "labels", "caption"}
        if extra:
            raise SystemExit(f"scale: unknown key(s) {sorted(extra)}")
        if not sc.get("caption"):
            # An example threshold without its caveat reads as a rule.
            raise SystemExit("scale: 'caption' is required (say whose thresholds these are)")


def spine(n):
    """Serpentine path geometry: lines, turns, node centres, cumulative length."""
    pitch = SH / n
    r = pitch / 2
    xL, xR = M + r + 10, W - M - r - 10
    ys = [SY + k * pitch for k in range(n + 1)]
    d = [f"M {xL:.1f} {ys[0]:.1f}", f"H {xR:.1f}"]
    seg_len = xR - xL
    lengths = [seg_len]                 # running list of segment lengths
    nodes = []
    for k in range(n):
        right = (k % 2 == 0)
        x = xR if right else xL
        # right turn bulges right (clockwise), left turn bulges left (counter-clockwise)
        d.append(f"A {r:.1f} {r:.1f} 0 0 {1 if right else 0} {x:.1f} {ys[k + 1]:.1f}")
        arc = math.pi * r
        before = sum(lengths)
        nodes.append({
            "k": k, "right": right,
            "cx": x + r if right else x - r,
            "cy": (ys[k] + ys[k + 1]) / 2,
            "band_top": ys[k], "pitch": pitch,
            "at": before + arc / 2,     # path length at the turn apex
        })
        lengths.append(arc)
        d.append(f"H {(xL if right else xR):.1f}")
        lengths.append(seg_len)
    total = sum(lengths)
    return {"d": " ".join(d), "nodes": nodes, "total": total, "pitch": pitch,
            "r": r, "xL": xL, "xR": xR}


def build(cfg, theme, motion):
    out = _build(cfg, theme, motion)
    if motion:
        out = motion_extras(cfg, out)
        check_loop_fits(cfg, out)
    return out


_TAG = re.compile(r'<[a-z]+\b[^>]*\bdata-s="(\d+)"[^>]*>')


def motion_extras(cfg, out):
    """Opt-in grammar on top of any layout (motion-review-2026-09-28, Phases 1-3).

    motion_return "reverse": exits play each entrance backwards, last-in first-out,
      one beat apart, instead of every element fading at the same instant.
    motion_live true: the abstain chip (the accent) pulses through the hold.
    motion_morph true: the abstain chip changes shape into the first confidence band
      and back, leaving a ghost (decisions layout: 'unresolved routes low').
    Rules: (private notes) section 4 (hold never frozen, morph not
    fade, stagger by a beat). check_loop_fits() runs AFTER this, on the result.
    """
    mode = cfg.get("motion_return")
    if mode not in (None, "reverse"):
        raise SystemExit(f"card-infographic: motion_return must be \"reverse\", got {mode!r}")
    tags = [(m.start(), m.end(), int(m.group(1)), m.group(0)) for m in _TAG.finditer(out)]
    outs = [int(o) for _, _, _, tg in tags for o in re.findall(r'data-out="(\d+)"', tg)]
    if not outs:
        return out
    base = min(outs)
    last_in = max(s + int(re.search(r'data-d="(\d+)"', tg).group(1)) for _, _, s, tg in tags)
    hold = (last_in + 200, base - 150)

    if mode == "reverse":
        gap = max(40, min(90, 1400 // max(1, len(tags))))
        rank = {id_: r for r, id_ in enumerate(sorted(range(len(tags)), key=lambda i: -tags[i][2]))}
        pieces, prev = [], 0
        for i, (a, b, _, tg) in enumerate(tags):
            pieces.append(out[prev:a])
            pieces.append(re.sub(r'data-out="\d+"', f'data-out="{base + rank[i] * gap}"', tg))
            prev = b
        out = "".join(pieces) + out[prev:]
        out = out.replace('<div id="slide-1"', '<div id="slide-1" data-return="reverse"', 1)

    ab = re.search(r'<span class="(?:chip|mc) ab"', out)
    if cfg.get("motion_morph"):
        if cfg.get("layout") != "decisions" or not ab or 'class="band b0"' not in out:
            raise SystemExit("card-infographic: motion_morph needs layout decisions with an abstain option and bands")
        out = out.replace('class="band b0"', 'id="morph-target" class="band b0"', 1)
        span = hold[1] - hold[0]
        win = f'{hold[0] + span // 6},{hold[0] + span // 6 + min(2400, span * 2 // 3)}'
        live_from = int(win.split(",")[1]) + 100
        extra = f' data-live="{live_from},{hold[1]}"' if hold[1] - live_from >= 900 else ""
        out = out[:ab.end()] + f' data-morph-to="#morph-target" data-morph="{win}"{extra}' + out[ab.end():]
    elif cfg.get("motion_live") and ab and hold[1] - hold[0] >= 900:
        out = out[:ab.end()] + f' data-live="{hold[0]},{hold[1]}"' + out[ab.end():]
    return out


def check_loop_fits(cfg, out):
    """Refuse a motion_ms that ends before the last dissolve finishes.

    Dissolve times are per-layout (and stage-count dependent for flow), so read
    them off the built HTML rather than re-deriving them. A loop shorter than
    this records its closing frame mid-build and the seam jumps on every repeat
    (claim-check, 2026-09-27: motion_ms 11500 == the dissolve START). render.sh
    falls back to 5500 when a config omits motion_ms; so does this check.
    """
    ends = [int(s) + int(d or DISSOLVE_D)
            for s, d in re.findall(r'data-out="(\d+)"(?: data-outd="(\d+)")?', out)]
    if not ends:
        return
    fps = int(cfg.get("fps", 24))
    need = max(ends) + math.ceil(1000 / fps)
    have = int(cfg.get("motion_ms", 5500))
    if have < need:
        raise SystemExit(f"card-infographic: motion_ms {have} ends before the last dissolve finishes "
                         f"({max(ends)} ms + one frame). Set motion_ms >= {need}, or the loop seam jumps.")


def _build(cfg, theme, motion):
    validate(cfg)
    if cfg.get("layout", "spine") == "cycle":
        return build_cycle(cfg, theme, motion)
    if cfg.get("layout") in ("decisions", "sort"):
        return build_blocks(cfg, theme, motion)
    if cfg.get("layout") == "mega":
        return build_mega(cfg, theme, motion)
    if cfg.get("layout") == "flow":
        return build_flow(cfg, theme, motion)
    T = brandkit.theme(BRAND, theme)
    font_family, _, font_import = brandkit.font(BRAND, cfg)
    mono_family, _ = brandkit.mono(BRAND)
    mono_family = mono_family or font_family
    F = brandkit.footer(BRAND, cfg)

    def anim(s, d=MD, extra=""):
        if not motion:
            return ""
        return (f' data-s="{int(s)}" data-d="{int(d)}"'
                f' data-out="{DISSOLVE_MS}" data-outd="{DISSOLVE_D}"{extra}')

    root_attrs = ""
    if motion and cfg.get("ease"):
        root_attrs += f' data-ease="{html.escape(cfg["ease"])}"'
        if cfg.get("rise"):
            root_attrs += f' data-rise="{int(cfg["rise"])}"'

    runtime = motion_css = ""
    if motion:
        motion_css = "[data-s]{opacity:0;}"
        runtime = "<script>" + (SCRIPTS / "motion-runtime.js").read_text() + "</script>"

    g = spine(len(cfg["nodes"]))

    # ---- background grid + registration marks (static: present on frame 0 AND the
    # last frame, so the loop seam holds without dissolving them)
    grid = []
    step = 48
    for x in range(M, W - M + 1, step):
        grid.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>')
    for y in range(0, H + 1, step):
        grid.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>')
    reg = []
    for (x, y, dx, dy) in [(24, 24, 1, 1), (W - 24, 24, -1, 1), (24, H - 24, 1, -1), (W - 24, H - 24, -1, -1)]:
        reg.append(f'<path d="M {x} {y + 22 * dy} V {y} H {x + 22 * dx}"/>')

    # ---- spine SVG: tick guide (static), the drawn path, the pen
    path_attrs = anim(T_DRAW, D_DRAW, ' data-draw data-tip="#pen"') if motion else ""
    svg = f"""<svg class="spine" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <g class="grid">{''.join(grid)}</g>
  <g class="reg">{''.join(reg)}</g>
  <path class="guide" d="{g['d']}"/>
  <path class="line" d="{g['d']}"{path_attrs}/>
  <g id="pen"><circle class="ring" r="0"/><circle class="tip" r="5"/></g>
</svg>"""

    # ---- nodes
    nodes_html = []
    side = 46
    for nd, spec in zip(g["nodes"], cfg["nodes"]):
        k = nd["k"]
        last = (k == len(cfg["nodes"]) - 1)
        t_node = T_DRAW + D_DRAW * nd["at"] / g["total"]
        box_x, box_y = nd["cx"] - side / 2, nd["cy"] - side / 2
        nodes_html.append(
            f'<div class="node{" is-last" if last else ""}" style="left:{box_x:.1f}px;top:{box_y:.1f}px;'
            f'width:{side}px;height:{side}px"{anim(t_node, MD)}>'
            f'<span class="xh"></span>{k + 1:02d}</div>')
        top = nd["band_top"] + (nd["pitch"] - 50) / 2
        if nd["right"]:
            pos = f"left:{g['xL'] + 6:.1f}px;text-align:left"
        else:
            pos = f"right:{W - g['xR'] - 6:.1f}px;text-align:right"
        nodes_html.append(
            f'<div class="item" style="top:{top:.1f}px;{pos}">'
            f'<p class="name"{anim(t_node, MD)}>{esc(spec["name"])}</p>'
            f'<p class="fix"{anim(t_node + FIX_LAG, MD)}>{esc(spec["fix"])}</p></div>')

    # ---- spec cells
    cells = []
    for i, c in enumerate(cfg["cells"]):
        cells.append(
            f'<div class="cell"{anim(T_CELLS + 260 + i * 150, LG)}>'
            f'<p class="clabel">[ {esc(c["label"])} ]</p>'
            f'<p class="cline">{esc(c["line"])}</p>'
            f'<p class="cdet">{esc(c["detail"])}</p>'
            f'<p class="cemph">{esc(c["emph"])}</p></div>')

    # ---- scale
    scale_html = ""
    sc = cfg.get("scale")
    if sc:
        span = W - 2 * M
        ticks = "".join(
            f'<span class="tick{" major" if i in (0, 10) else ""}" style="left:{M + span * i / 10:.1f}px"></span>'
            for i in range(11))
        ticklabels = "".join(
            f'<span class="tlab" style="left:{M + span * v:.1f}px">{v:g}</span>'
            for v in sorted({0.0, 1.0, *sc.get("markers", [])}))
        markers = "".join(
            f'<span class="mark" style="left:{M + span * v - 6:.1f}px"{anim(T_SCALE + LG, MD)}></span>'
            for v in sc.get("markers", []))
        labels = "".join(
            f'<p class="slab"{anim(T_SCALE_LABELS + 260 + i * 150, MD)}>{esc(l)}</p>'
            for i, l in enumerate(sc.get("labels", [])))
        scale_html = (
            # data-wipe animates width to 100% of the PARENT. On the slide root that
            # is 1080px, so the line overran the right margin in every motion frame
            # while the static PNG looked right. The wrapper fixes the 100%.
            f'<div class="scale-wrap"><div class="scale-line"{anim(T_SCALE, LG, " data-wipe")}></div></div>'
            f'<div class="ticks"{anim(T_SCALE, LG)}>{ticks}{ticklabels}</div>{markers}'
            f'<div class="slabels">{labels}</div>'
            f'<p class="caption"{anim(T_CAPTION, MD)}>{esc(sc["caption"])}</p>')

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
/* WRAP RULE: text-wrap inherits, so one declaration on the root covers every
   descendant (AGENTS.md rule 8 corollary). */
#slide-1{{text-wrap:balance;box-shadow:inset 0 0 0 1px {T['border']};position:relative;width:{W}px;height:{H}px;overflow:hidden;
  background:{T['canvas']};color:{T['text']};font-family:'{font_family}',sans-serif;}}
.spine{{position:absolute;left:0;top:0;}}
.grid line{{stroke:{T['hairline']};stroke-width:1;}}
.reg path{{fill:none;stroke:{T['accent']};stroke-width:2;}}
.guide{{fill:none;stroke:{T['muted']};stroke-width:7;stroke-dasharray:1 31;}}
.line{{fill:none;stroke:{T['accent']};stroke-width:2;}}
#pen{{opacity:0;}}
#pen .tip{{fill:{T['accent']};}}
#pen .ring{{fill:none;stroke:{T['accent']};stroke-width:1.5;}}
.abs{{position:absolute;left:{M}px;right:{M}px;}}
.meta{{top:{Y_META}px;display:flex;justify-content:space-between;font-family:'{mono_family}',monospace;
  font-size:15px;letter-spacing:.04em;color:{T['sub']};}}
.meta .g{{color:{T['accent']};}}
.rule{{top:{Y_RULE}px;height:0;border-top:1px solid {T['text']};}}
.title{{top:{Y_TITLE}px;font-size:84px;font-weight:700;letter-spacing:-.05em;line-height:1;}}
.sub{{top:{Y_SUB}px;font-size:22px;font-weight:400;color:{T['sub']};}}
.g{{color:{T['accent']};}}
.cells{{top:{Y_CELLS}px;height:{CELLS_H}px;display:grid;grid-template-columns:repeat(3,1fr);
  border:1px solid {T['text']};background:{T['canvas']};}}
.cell{{padding:14px 16px;border-left:1px solid {T['text']};}}
.cell:first-child{{border-left:0;}}
.clabel{{font-family:'{mono_family}',monospace;font-size:13px;font-weight:700;letter-spacing:.06em;color:{T['accent']};}}
.cline{{margin-top:8px;font-size:21px;font-weight:600;letter-spacing:-.02em;}}
.cdet,.cemph{{margin-top:6px;font-family:'{mono_family}',monospace;font-size:12.5px;line-height:1.3;color:{T['sub']};}}
.cemph{{margin-top:2px;font-weight:700;color:{T['text']};}}
.readout{{top:{Y_READOUT}px;font-family:'{mono_family}',monospace;font-size:14px;letter-spacing:.03em;
  color:{T['sub']};text-transform:uppercase;}}
.readout .g{{font-weight:700;}}
.node{{position:absolute;display:flex;align-items:center;justify-content:center;
  background:{T['canvas']};border:1px solid {T['text']};font-family:'{mono_family}',monospace;
  font-size:16px;font-weight:700;letter-spacing:-.02em;color:{T['text']};}}
.node.is-last{{background:{T['text']};color:{T['canvas']};}}
.node .xh{{position:absolute;left:-6px;top:-6px;width:11px;height:11px;
  border-left:1.5px solid {T['accent']};border-top:1.5px solid {T['accent']};}}
.item{{position:absolute;max-width:760px;}}
.name{{font-size:22px;font-weight:600;letter-spacing:-.02em;line-height:1.1;}}
.fix{{margin-top:5px;font-family:'{mono_family}',monospace;font-size:14px;line-height:1.3;color:{T['sub']};}}
.scale-wrap{{position:absolute;left:{M}px;top:{Y_SCALE}px;width:{W - 2 * M}px;height:2px;}}
.scale-line{{width:100%;height:0;border-top:1.5px solid {T['text']};}}
.ticks{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;pointer-events:none;}}
.tick{{position:absolute;top:{Y_SCALE - 4}px;width:0;height:8px;border-left:1px solid {T['text']};}}
.tick.major{{top:{Y_SCALE - 8}px;height:16px;}}
.tlab{{position:absolute;top:{Y_SCALE + 12}px;transform:translateX(-50%);font-family:'{mono_family}',monospace;
  font-size:12px;color:{T['sub']};}}
.mark{{position:absolute;top:{Y_SCALE - 6}px;width:12px;height:12px;background:{T['accent']};}}
.slabels{{position:absolute;left:{M}px;right:{M}px;top:{Y_SCALE_LABELS}px;display:grid;
  grid-template-columns:repeat(3,1fr);gap:24px;}}
.slab{{font-family:'{mono_family}',monospace;font-size:13px;line-height:1.35;color:{T['text']};}}
.caption{{position:absolute;left:{M}px;right:{M}px;top:{Y_CAPTION}px;font-family:'{mono_family}',monospace;
  font-size:12.5px;color:{T['sub']};}}
.foot-rule{{top:{Y_FOOT_RULE}px;height:0;border-top:1px solid {T['text']};}}
.foot{{top:{Y_FOOT}px;display:flex;align-items:center;justify-content:space-between;}}
.src{{font-family:'{mono_family}',monospace;font-size:12px;color:{T['sub']};text-align:right;}}
{motion_css}
{brandkit.footer_lock(T, F, 0.7)['css']}
</style></head><body><div id="slide-1"{root_attrs}>
{svg}
<div class="abs meta"{anim(T_META)}><span>{esc(cfg['meta_left'])}</span><span>{esc(cfg.get('meta_right', ''))}</span></div>
<div class="abs rule"{anim(T_META)}></div>
<h1 class="abs title"{anim(T_TITLE, LG)}>{esc(cfg['title'])}</h1>
<p class="abs sub"{anim(T_SUB)}>{esc(cfg['sub'])}</p>
<div class="abs cells"{anim(T_CELLS, LG)}>{''.join(cells)}</div>
<p class="abs readout"{anim(T_READOUT)}>{esc(cfg['readout'])}</p>
{''.join(nodes_html)}
{scale_html}
<div class="abs foot-rule"{anim(T_FOOT)}></div>
<div class="abs foot"{anim(T_FOOT)}>{brandkit.footer_lock(T, F, 0.7)['who']}
<div class="src">{esc(cfg.get('source', ''))}</div></div>
</div>{runtime}</body></html>"""


# ============================================================================
# Layout "cycle": six steps on ONE hexagonal loop, read clockwise from the top.
# For a process that REPEATS (calibration, review, release): the loop is the
# claim, so the pen draws the whole hexagon and comes back to where it started.
# ============================================================================
CY_TITLE_LINES = 2
CY_SUB = 292
CY_CX, CY_CY, CY_R, CY_RI = W / 2, 642, 240, 146   # outer / inner hexagon radii
CY_GAP = 26                  # clear space between the widest node and its text column
CY_QUOTE = 962
CY_NOTE = 1098
T_CORE = 1300
T_RING, D_RING = 1800, 6000
T_LOOP = 7900
T_QUOTE, T_NOTE = 8500, 9100
CY_DISSOLVE = 12000


def validate_cycle(cfg):
    steps = cfg.get("steps") or []
    if len(steps) != 6:
        raise SystemExit(f"card-infographic 'cycle' renders exactly 6 steps, config has {len(steps)}")
    for i, s in enumerate(steps):
        if set(s) - {"name", "detail"} or not s.get("name") or not s.get("detail"):
            raise SystemExit(f"step {i + 1}: needs exactly 'name' and 'detail', got {sorted(s)}")
    core = cfg.get("core") or {}
    if set(core) != {"kicker", "line"}:
        raise SystemExit(f"core: needs exactly 'kicker' and 'line', got {sorted(core)}")
    q = cfg.get("quote")
    if q is not None and (set(q) != {"text", "cite"} or not q["cite"]):
        # A quote without its source is a claim with no owner.
        raise SystemExit(f"quote: needs exactly 'text' and a non-empty 'cite', got {sorted(q)}")


def hexagon(cx, cy, r):
    """Pointy-top hexagon, vertices clockwise from the top."""
    return [(cx + r * math.cos(math.radians(-90 + 60 * k)),
             cy + r * math.sin(math.radians(-90 + 60 * k))) for k in range(6)]


def build_cycle(cfg, theme, motion):
    T = brandkit.theme(BRAND, theme)
    font_family, _, font_import = brandkit.font(BRAND, cfg)
    mono_family, _ = brandkit.mono(BRAND)
    mono_family = mono_family or font_family
    F = brandkit.footer(BRAND, cfg)

    def anim(s, d=MD, extra=""):
        if not motion:
            return ""
        return (f' data-s="{int(s)}" data-d="{int(d)}"'
                f' data-out="{CY_DISSOLVE}" data-outd="{DISSOLVE_D}"{extra}')

    root_attrs = ""
    if motion and cfg.get("ease"):
        root_attrs += f' data-ease="{html.escape(cfg["ease"])}"'
        if cfg.get("rise"):
            root_attrs += f' data-rise="{int(cfg["rise"])}"'
    runtime = motion_css = ""
    if motion:
        motion_css = "[data-s]{opacity:0;}"
        runtime = "<script>" + (SCRIPTS / "motion-runtime.js").read_text() + "</script>"

    outer = hexagon(CY_CX, CY_CY, CY_R)
    inner = hexagon(CY_CX, CY_CY, CY_RI)
    ring_d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in outer) + f" L {outer[0][0]:.1f} {outer[0][1]:.1f}"
    inner_d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in inner) + " Z"

    grid = []
    for x in range(M, W - M + 1, 48):
        grid.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>')
    for y in range(0, H + 1, 48):
        grid.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>')
    reg = [f'<path d="M {x} {y + 22 * dy} V {y} H {x + 22 * dx}"/>'
           for (x, y, dx, dy) in [(24, 24, 1, 1), (W - 24, 24, -1, 1), (24, H - 24, 1, -1), (W - 24, H - 24, -1, -1)]]

    # segment k = the band between outer edge k and inner edge k; the pen reaches
    # its middle at (k + 0.5) / 6 of the ring's length.
    segs, spokes, nodes, items, leaders = [], [], [], [], []
    side = 44
    for k, step in enumerate(cfg["steps"]):
        a, b = outer[k], outer[(k + 1) % 6]
        ia, ib = inner[k], inner[(k + 1) % 6]
        t_seg = T_RING + D_RING * (k + 0.5) / 6
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (a, b, ib, ia))
        segs.append(f'<polygon class="seg" points="{pts}"{anim(t_seg, LG)}/>')
        spokes.append(f'<line class="spoke" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{ia[0]:.1f}" y2="{ia[1]:.1f}"/>')
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        nodes.append(f'<div class="node" style="left:{mx - side / 2:.1f}px;top:{my - side / 2:.1f}px;'
                     f'width:{side}px;height:{side}px"{anim(t_seg, MD)}><span class="xh"></span>{k + 1:02d}</div>')
        right = mx > CY_CX
        # Columns start past the WIDEST node (the side vertices' edges), not at a
        # fixed width: a fixed 238px column put nodes 02/05 flush against their text.
        reach = CY_R * math.cos(math.radians(30)) + side / 2 + CY_GAP
        col_w = W - M - (CY_CX + reach)
        col_x = (CY_CX + reach) if right else M
        edge_x = col_x if right else col_x + col_w
        node_edge = mx + side / 2 if right else mx - side / 2
        leaders.append(f'<line class="leader" x1="{node_edge:.1f}" y1="{my:.1f}" x2="{edge_x:.1f}" y2="{my:.1f}"'
                       f'{anim(t_seg, MD)}/>')
        items.append(f'<div class="step{" r" if right else " l"}" style="left:{col_x:.1f}px;top:{my - 30:.1f}px;'
                     f'width:{col_w:.1f}px"><p class="sname"{anim(t_seg, MD)}>{esc(step["name"])}</p>'
                     f'<p class="sdet"{anim(t_seg + FIX_LAG, MD)}>{esc(step["detail"])}</p></div>')

    # loop mark: a chevron on the first edge just after the top vertex, drawn when
    # the pen closes the ring, so "it goes round again" is stated, not implied.
    v0, v1 = outer[0], outer[1]
    ux, uy = (v1[0] - v0[0]) / CY_R, (v1[1] - v0[1]) / CY_R
    px, py = v0[0] + ux * 34, v0[1] + uy * 34
    chev = (f'<path class="chev" d="M {px - 9 * ux - 7 * uy:.1f} {py - 9 * uy + 7 * ux:.1f} L {px:.1f} {py:.1f} '
            f'L {px - 9 * ux + 7 * uy:.1f} {py - 9 * uy - 7 * ux:.1f}"{anim(T_LOOP, MD)}/>')

    path_attrs = anim(T_RING, D_RING, ' data-draw data-tip="#pen"') if motion else ""
    svg = f"""<svg class="spine" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <g class="grid">{''.join(grid)}</g>
  <g class="reg">{''.join(reg)}</g>
  {''.join(segs)}
  <path class="inner" d="{inner_d}"/>
  {''.join(spokes)}
  <path class="guide" d="{ring_d}"/>
  <path class="line" d="{ring_d}"{path_attrs}/>
  {''.join(leaders)}
  {chev}
  <g id="pen"><circle class="ring" r="0"/><circle class="tip" r="5"/></g>
</svg>"""

    core = cfg["core"]
    q = cfg.get("quote")
    quote_html = (f'<div class="abs quote"{anim(T_QUOTE, LG)}><p class="qtext">“{esc(q["text"])}”</p>'
                  f'<p class="qcite">{esc(q["cite"])}</p></div>') if q else ""
    note_html = (f'<p class="abs loopnote"{anim(T_NOTE, MD)}>{esc(cfg["loop_note"])}</p>'
                 if cfg.get("loop_note") else "")

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
#slide-1{{text-wrap:balance;box-shadow:inset 0 0 0 1px {T['border']};position:relative;width:{W}px;height:{H}px;overflow:hidden;
  background:{T['canvas']};color:{T['text']};font-family:'{font_family}',sans-serif;}}
.spine{{position:absolute;left:0;top:0;}}
.grid line{{stroke:{T['hairline']};stroke-width:1;}}
.reg path{{fill:none;stroke:{T['accent']};stroke-width:2;}}
.seg{{fill:{T['island_bg']};stroke:none;}}
.inner{{fill:{T['canvas']};stroke:{T['text']};stroke-width:1;}}
.spoke{{stroke:{T['text']};stroke-width:1;}}
.guide{{fill:none;stroke:{T['muted']};stroke-width:7;stroke-dasharray:1 31;}}
.line{{fill:none;stroke:{T['accent']};stroke-width:2.5;stroke-linejoin:miter;}}
.leader{{stroke:{T['text']};stroke-width:1;}}
.chev{{fill:none;stroke:{T['accent']};stroke-width:2.5;}}
#pen{{opacity:0;}}
#pen .tip{{fill:{T['accent']};}}
#pen .ring{{fill:none;stroke:{T['accent']};stroke-width:1.5;}}
.abs{{position:absolute;left:{M}px;right:{M}px;}}
.meta{{top:{Y_META}px;display:flex;justify-content:space-between;font-family:'{mono_family}',monospace;
  font-size:15px;letter-spacing:.04em;color:{T['sub']};}}
.rule{{top:{Y_RULE}px;height:0;border-top:1px solid {T['text']};}}
.title{{top:{Y_TITLE}px;font-size:84px;font-weight:700;letter-spacing:-.05em;line-height:.98;}}
.sub{{top:{CY_SUB}px;font-size:22px;font-weight:400;color:{T['sub']};}}
.g{{color:{T['accent']};}}
.core{{position:absolute;left:{CY_CX - 120}px;width:240px;top:{CY_CY - 44}px;text-align:center;}}
.ckick{{font-family:'{mono_family}',monospace;font-size:14px;font-weight:700;letter-spacing:.08em;color:{T['accent']};}}
.cline{{margin-top:8px;font-size:22px;font-weight:600;letter-spacing:-.02em;line-height:1.1;}}
.node{{position:absolute;display:flex;align-items:center;justify-content:center;
  background:{T['canvas']};border:1px solid {T['text']};font-family:'{mono_family}',monospace;
  font-size:15px;font-weight:700;letter-spacing:-.02em;color:{T['text']};}}
.node .xh{{position:absolute;left:-6px;top:-6px;width:11px;height:11px;
  border-left:1.5px solid {T['accent']};border-top:1.5px solid {T['accent']};}}
.step{{position:absolute;}}
.step.r{{text-align:left;}} .step.l{{text-align:right;}}
.sname{{font-size:20px;font-weight:600;letter-spacing:-.02em;line-height:1.1;}}
.sdet{{margin-top:6px;font-family:'{mono_family}',monospace;font-size:13px;line-height:1.35;color:{T['sub']};}}
.quote{{top:{CY_QUOTE}px;border-left:3px solid {T['accent']};padding:4px 0 4px 20px;}}
.qtext{{font-size:23px;font-weight:500;letter-spacing:-.015em;line-height:1.28;}}
.qcite{{margin-top:10px;font-family:'{mono_family}',monospace;font-size:12.5px;color:{T['sub']};}}
.loopnote{{top:{CY_NOTE}px;font-family:'{mono_family}',monospace;font-size:14px;letter-spacing:.02em;color:{T['text']};}}
.loopnote .g{{font-weight:700;}}
.foot-rule{{top:{Y_FOOT_RULE}px;height:0;border-top:1px solid {T['text']};}}
.foot{{top:{Y_FOOT}px;display:flex;align-items:center;justify-content:space-between;}}
.src{{font-family:'{mono_family}',monospace;font-size:12px;color:{T['sub']};text-align:right;}}
{motion_css}
{brandkit.footer_lock(T, F, 0.7)['css']}
</style></head><body><div id="slide-1"{root_attrs}>
{svg}
<div class="abs meta"{anim(T_META)}><span>{esc(cfg['meta_left'])}</span><span>{esc(cfg.get('meta_right', ''))}</span></div>
<div class="abs rule"{anim(T_META)}></div>
<h1 class="abs title"{anim(T_TITLE, LG)}>{esc(cfg['title'])}</h1>
<p class="abs sub"{anim(T_SUB)}>{esc(cfg['sub'])}</p>
<div class="core"{anim(T_CORE, LG)}><p class="ckick">{esc(core['kicker'])}</p><p class="cline">{esc(core['line'])}</p></div>
{''.join(nodes)}
{''.join(items)}
{quote_html}
{note_html}
<div class="abs foot-rule"{anim(T_FOOT)}></div>
<div class="abs foot"{anim(T_FOOT)}>{brandkit.footer_lock(T, F, 0.7)['who']}
<div class="src">{esc(cfg.get('source', ''))}</div></div>
</div>{runtime}</body></html>"""


# ============================================================================
# Layouts "decisions" and "sort": the SAVE-WORTHY formats. They are not diagrams
# of an idea, they are the reference itself: the exact typed questions to copy
# ("decisions"), or a three-way table a reader sorts their own tasks against
# ("sort"). Blocks sit in normal flow between header and footer, so there is no
# hand-placed geometry beyond the page frame.
# ============================================================================
BL_TYPES = {"noul", "choice", "score"}
BL_BODY_BOTTOM = 1208
T_BLOCK = 1100
BL_DISSOLVE = 11500


def validate_blocks(cfg, layout):
    if layout == "decisions":
        ds = cfg.get("decisions") or []
        if not 3 <= len(ds) <= 5:
            raise SystemExit(f"card-infographic 'decisions' renders 3 to 5 decisions, config has {len(ds)}")
        for i, d in enumerate(ds):
            extra = set(d) - {"name", "type", "ask", "options", "abstain", "route"}
            if extra or not all(d.get(k) for k in ("name", "type", "ask", "route")):
                raise SystemExit(f"decision {i + 1}: needs name/type/ask/route (+ options, abstain), got {sorted(d)}")
            if d["type"] not in BL_TYPES:
                raise SystemExit(f"decision {i + 1}: type {d['type']!r} is not a Jev type {sorted(BL_TYPES)}")
            opts = d.get("options") or []
            if d["type"] == "noul" and opts:
                raise SystemExit(f"decision {i + 1}: a noul has no options (it returns one probability)")
            if d["type"] != "noul" and not 2 <= len(opts) <= 6:
                raise SystemExit(f"decision {i + 1}: {d['type']} needs 2 to 6 options on the card, has {len(opts)}")
            if d.get("abstain") and d["abstain"] not in opts:
                # The abstain option is the card's whole claim: it must be a real option.
                raise SystemExit(f"decision {i + 1}: abstain {d['abstain']!r} is not one of its options")
        b = cfg.get("bands") or {}
        if set(b) != {"markers", "labels", "caption"} or len(b["labels"]) != len(b["markers"]) + 1:
            raise SystemExit("bands: needs markers, labels (one more than markers) and a caption")
    else:
        cols = cfg.get("columns") or []
        if len(cols) != 3:
            raise SystemExit(f"card-infographic 'sort' renders exactly 3 columns, config has {len(cols)}")
        for i, c in enumerate(cols):
            if set(c) != {"label", "rule", "items"}:
                raise SystemExit(f"column {i + 1}: needs exactly label/rule/items, got {sorted(c)}")
            if not 3 <= len(c["items"]) <= 6:
                raise SystemExit(f"column {i + 1}: 3 to 6 items, has {len(c['items'])}")
            for j, it in enumerate(c["items"]):
                if set(it) != {"task", "why"}:
                    raise SystemExit(f"column {i + 1} item {j + 1}: needs exactly task/why, got {sorted(it)}")


def build_blocks(cfg, theme, motion):
    T = brandkit.theme(BRAND, theme)
    font_family, _, font_import = brandkit.font(BRAND, cfg)
    mono_family, _ = brandkit.mono(BRAND)
    mono_family = mono_family or font_family
    F = brandkit.footer(BRAND, cfg)

    def anim(s, d=MD, fx=None):
        # Header and footer never animate: frame 0 must read as the card, not an
        # empty grid (the feed autoplays from frame 0), and a static header is
        # identical on the first and last frame, so the loop seam still holds.
        if not motion:
            return ""
        return (f' data-s="{int(s)}" data-d="{int(d)}" data-out="{BL_DISSOLVE}" data-outd="{DISSOLVE_D}"'
                + (f' data-fx="{fx}"' if fx else ""))

    root_attrs = ""
    if motion and cfg.get("ease"):
        root_attrs += f' data-ease="{html.escape(cfg["ease"])}"'
        if cfg.get("rise"):
            root_attrs += f' data-rise="{int(cfg["rise"])}"'
    runtime = motion_css = ""
    if motion:
        motion_css = "[data-s]{opacity:0;}"
        runtime = "<script>" + (SCRIPTS / "motion-runtime.js").read_text() + "</script>"

    grid = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>' for x in range(M, W - M + 1, 48))
    grid += "".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>' for y in range(0, H + 1, 48))
    reg = "".join(f'<path d="M {x} {y + 22 * dy} V {y} H {x + 22 * dx}"/>'
                  for (x, y, dx, dy) in [(24, 24, 1, 1), (W - 24, 24, -1, 1), (24, H - 24, 1, -1), (W - 24, H - 24, -1, -1)])

    t = T_BLOCK
    body = []
    if cfg["layout"] == "decisions":
        headers_first = cfg.get("motion_style") == "headers_first"
        n_dec = len(cfg["decisions"])
        # "headers_first": a preview beat (all four numbered headers land fast, in
        # one breath) before any card fills in, instead of one card fully revealing
        # at a time. Same fx primitives, different rhythm — so a run of decisions
        # cards doesn't all play identically back to back in the feed.
        head_span = 260 + n_dec * 220 if headers_first else 0
        for i, d in enumerate(cfg["decisions"]):
            if headers_first:
                ts_head = t + 260 + i * 220
                ts = t + head_span + 200 + i * 480
            else:
                ts_head = ts = t + 260 + i * 700
            opts = d.get("options") or []
            chips = "".join(
                f'<span class="chip{" ab" if o == d.get("abstain") else ""}"{anim(ts + 300 + j * 150, MD, "pop")}>{esc(o)}</span>'
                for j, o in enumerate(opts))
            if d["type"] == "noul":
                chips = f'<span class="chip p"{anim(ts + 300)}>returns 0 to 1 · no confidence field</span>'
            fx = "scale" if headers_first else "unroll"
            body.append(
                f'<div class="dec"{anim(ts_head, LG, fx)}><div class="dnum">{i + 1:02d}<span class="ty">{d["type"]}</span></div>'
                f'<div class="dmain"><p class="dname"{anim(ts, MD, "left") if headers_first else ""}>{esc(d["name"])}</p>'
                f'<p class="dask">{esc(d["ask"])}</p>'
                f'<div class="chips">{chips}</div></div>'
                f'<p class="droute"{anim(ts + 300 + 150 * max(1, len(opts)), MD, "right")}>{esc(d["route"])}</p></div>')
        b = cfg["bands"]
        tb = t + (head_span + 200 + n_dec * 480 if headers_first else 260 + n_dec * 700)
        edges = [0.0, *b["markers"], 1.0]
        segs = "".join(
            f'<div class="band b{k}" style="flex:{edges[k + 1] - edges[k]:.3f}"{anim(tb + 260 + k * 150, MD, "left")}>'
            f'<span>{esc(lab)}</span></div>' for k, lab in enumerate(b["labels"]))
        ticks = "".join(f'<span class="btick" style="left:{v * 100:.2f}%">{v:g}</span>' for v in edges)
        body.append(f'<div class="bands"{anim(tb, LG)}><p class="bhead">confidence routing · choice + score only</p>'
                    f'<div class="brow">{segs}</div><div class="bticks">{ticks}</div>'
                    f'<p class="bcap">{esc(b["caption"])}</p></div>')
        if cfg.get("never"):
            body.append(f'<p class="never"{anim(tb + 900, 900, "type")}>{esc(cfg["never"])}</p>')
    else:
        if cfg.get("readout"):
            body.append(f'<p class="readout"{anim(t, 900, "type")}>{esc(cfg["readout"])}</p>')
        cols = []
        for i, c in enumerate(cfg["columns"]):
            tc = t + 260 + i * 150
            items = "".join(
                f'<li{anim(tc + 600 + j * 450, MD, "left")}><p class="task">{esc(it["task"])}</p>'
                f'<p class="why">{esc(it["why"])}</p></li>' for j, it in enumerate(c["items"]))
            cols.append(f'<div class="col c{i}"{anim(tc, LG, "unroll")}><p class="clab">{esc(c["label"])}</p>'
                        f'<p class="crule">{esc(c["rule"])}</p><ul>{items}</ul></div>')
        body.append(f'<div class="cols"{anim(t, LG, "unroll")}>{"".join(cols)}</div>')

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
#slide-1{{text-wrap:balance;box-shadow:inset 0 0 0 1px {T['border']};position:relative;width:{W}px;height:{H}px;overflow:hidden;
  background:{T['canvas']};color:{T['text']};font-family:'{font_family}',sans-serif;}}
.bg{{position:absolute;left:0;top:0;}}
.bg line{{stroke:{T['hairline']};stroke-width:1;}}
.bg path{{fill:none;stroke:{T['accent']};stroke-width:2;}}
.abs{{position:absolute;left:{M}px;right:{M}px;}}
.meta{{top:{Y_META}px;display:flex;justify-content:space-between;font-family:'{mono_family}',monospace;
  font-size:15px;letter-spacing:.04em;color:{T['sub']};}}
.rule{{top:{Y_RULE}px;height:0;border-top:1px solid {T['text']};}}
.frame{{top:{Y_TITLE}px;height:{BL_BODY_BOTTOM - Y_TITLE}px;display:flex;flex-direction:column;}}
.title{{font-size:72px;font-weight:700;letter-spacing:-.05em;line-height:.98;}}
.sub{{margin-top:18px;font-size:21px;font-weight:400;color:{T['sub']};}}
.g{{color:{T['accent']};}}
.body{{flex:1;margin-top:30px;display:flex;flex-direction:column;justify-content:space-between;gap:18px;}}
.dec{{display:grid;grid-template-columns:92px 1fr 196px;gap:20px;align-items:start;
  border:1px solid {T['text']};background:{T['canvas']};padding:20px 22px;}}
.dnum{{font-family:'{mono_family}',monospace;font-size:34px;font-weight:700;letter-spacing:-.04em;line-height:1;}}
.ty{{display:block;margin-top:10px;width:max-content;padding:3px 7px;background:{T['text']};color:{T['canvas']};
  font-size:12px;letter-spacing:.08em;text-transform:uppercase;}}
.dname{{font-size:27px;font-weight:600;letter-spacing:-.02em;line-height:1.1;}}
.dask{{margin-top:8px;font-family:'{mono_family}',monospace;font-size:15px;line-height:1.35;color:{T['sub']};}}
.chips{{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px;}}
.chip{{font-family:'{mono_family}',monospace;font-size:14px;padding:5px 10px;border:1px solid {T['text']};}}
.chip.ab{{border-color:{T['accent']};background:{T['accent']};color:{T['canvas']};font-weight:700;}}
.chip.p{{border-style:dashed;color:{T['sub']};}}
.droute{{font-family:'{mono_family}',monospace;font-size:14px;line-height:1.35;color:{T['text']};
  border-left:2px solid {T['accent']};padding-left:10px;}}
.bhead{{margin-bottom:8px;font-family:'{mono_family}',monospace;font-size:13px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:{T['accent']};}}
.brow{{display:flex;height:40px;border:1px solid {T['text']};}}
.band{{display:flex;align-items:center;padding-left:10px;font-family:'{mono_family}',monospace;font-size:13px;
  font-weight:700;letter-spacing:.06em;border-left:1px solid {T['text']};background:{T['canvas']};}}
.band.b0{{border-left:0;}}
.band:last-child{{background:{T['text']};color:{T['canvas']};}}
.bticks{{position:relative;height:22px;}}
.btick{{position:absolute;top:6px;transform:translateX(-50%);font-family:'{mono_family}',monospace;font-size:12px;
  color:{T['sub']};}}
.btick:first-child{{transform:none;}} .btick:last-child{{transform:translateX(-100%);}}
.bcap{{margin-top:2px;font-family:'{mono_family}',monospace;font-size:12.5px;color:{T['sub']};}}
.never{{font-family:'{mono_family}',monospace;font-size:14px;font-weight:700;letter-spacing:.02em;
  border-top:1px solid {T['text']};padding-top:12px;background:{T['canvas']};}}
.readout{{font-family:'{mono_family}',monospace;font-size:14px;letter-spacing:.03em;color:{T['sub']};}}
.readout .g{{font-weight:700;}}
.cols{{flex:1;margin-top:20px;display:grid;grid-template-columns:repeat(3,1fr);border:1px solid {T['text']};}}
.col{{padding:16px 16px 12px;border-left:1px solid {T['text']};background:{T['canvas']};}}
.col.c0{{border-left:0;}}
.col.c1{{background:{T['island_bg']};}}
.clab{{font-size:48px;font-weight:700;letter-spacing:-.04em;line-height:1;}}
.col.c1 .clab{{color:{T['accent']};}}
.crule{{margin-top:10px;padding-bottom:16px;border-bottom:1px solid {T['text']};font-family:'{mono_family}',monospace;
  font-size:14.5px;line-height:1.35;font-weight:700;}}
.col ul{{list-style:none;}}
.col li{{padding:22px 0;border-bottom:1px solid {T['hairline']};}}
.col li:last-child{{border-bottom:0;}}
.task{{font-size:22px;font-weight:600;letter-spacing:-.015em;line-height:1.15;}}
.why{{margin-top:7px;font-family:'{mono_family}',monospace;font-size:14px;line-height:1.3;color:{T['sub']};}}
.foot-rule{{top:{Y_FOOT_RULE}px;height:0;border-top:1px solid {T['text']};}}
.foot{{top:{Y_FOOT}px;display:flex;align-items:center;justify-content:space-between;}}
.src{{font-family:'{mono_family}',monospace;font-size:12px;color:{T['sub']};text-align:right;}}
{motion_css}
{brandkit.footer_lock(T, F, 0.7)['css']}
</style></head><body><div id="slide-1"{root_attrs}>
<svg class="bg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><g>{grid}</g><g>{reg}</g></svg>
<div class="abs meta"><span>{esc(cfg['meta_left'])}</span><span>{esc(cfg.get('meta_right', ''))}</span></div>
<div class="abs rule"></div>
<div class="abs frame"><h1 class="title">{esc(cfg['title'])}</h1>
<p class="sub">{esc(cfg['sub'])}</p>
<div class="body">{''.join(body)}</div></div>
<div class="abs foot-rule"></div>
<div class="abs foot">{brandkit.footer_lock(T, F, 0.7)['who']}
<div class="src">{esc(cfg.get('source', ''))}</div></div>
</div>{runtime}</body></html>"""


# ============================================================================
# Layout "mega": the dense cheat-sheet POSTER. Three columns (one per topic),
# 3 to 5 cards each. Deliberately small in the feed: titles read at feed size,
# the detail does not, and the full-resolution file is the lead magnet sent on
# request. Every card is one of three kinds, and the kind IS the lesson:
#   typed = ask a typed-decision model (type + options, abstain accented)
#   code  = compute it before asking anything (numbers, dates, counts)
#   human = the abstain queue a person works
# ============================================================================
MG_KINDS = {"typed", "code", "human"}
MG_DISSOLVE = 12000


def validate_mega(cfg):
    secs = cfg.get("sections") or []
    if len(secs) != 3:
        raise SystemExit(f"card-infographic 'mega' renders exactly 3 sections, config has {len(secs)}")
    for i, s in enumerate(secs):
        if set(s) != {"label", "question", "cards"}:
            raise SystemExit(f"section {i + 1}: needs exactly label/question/cards, got {sorted(s)}")
        if not 3 <= len(s["cards"]) <= 5:
            raise SystemExit(f"section {i + 1}: 3 to 5 cards, has {len(s['cards'])}")
        for j, c in enumerate(s["cards"]):
            where = f"section {i + 1} card {j + 1}"
            extra = set(c) - {"kind", "title", "type", "options", "abstain", "lines"}
            if extra or c.get("kind") not in MG_KINDS or not c.get("title") or not c.get("lines"):
                raise SystemExit(f"{where}: needs kind (typed/code/human), title, lines (+ type/options/abstain), got {sorted(c)}")
            if c["kind"] == "typed":
                if c.get("type") not in BL_TYPES:
                    raise SystemExit(f"{where}: a typed card needs type in {sorted(BL_TYPES)}")
                opts = c.get("options") or []
                if c["type"] == "noul" and opts:
                    raise SystemExit(f"{where}: a noul has no options")
                if c["type"] != "noul" and not 2 <= len(opts) <= 7:
                    raise SystemExit(f"{where}: {c['type']} needs 2 to 7 options, has {len(opts)}")
                if c.get("abstain") and c["abstain"] not in opts:
                    raise SystemExit(f"{where}: abstain {c['abstain']!r} is not one of its options")
            elif set(c) & {"type", "options", "abstain"}:
                # A code or human card carrying a question type would teach the wrong lesson.
                raise SystemExit(f"{where}: only a typed card may carry type/options/abstain")
    if not cfg.get("legend"):
        raise SystemExit("mega: 'legend' is required (one line per card kind), the poster is unreadable without it")


def build_mega(cfg, theme, motion):
    T = brandkit.theme(BRAND, theme)
    font_family, _, font_import = brandkit.font(BRAND, cfg)
    mono_family, _ = brandkit.mono(BRAND)
    mono_family = mono_family or font_family
    F = brandkit.footer(BRAND, cfg)

    def anim(s, d=MD, fx=None):
        # Header and footer never animate: frame 0 must read as the card, not an
        # empty grid (the feed autoplays from frame 0), and a static header is
        # identical on the first and last frame, so the loop seam still holds.
        if not motion:
            return ""
        return (f' data-s="{int(s)}" data-d="{int(d)}" data-out="{MG_DISSOLVE}" data-outd="{DISSOLVE_D}"'
                + (f' data-fx="{fx}"' if fx else ""))

    root_attrs = ""
    if motion and cfg.get("ease"):
        root_attrs += f' data-ease="{html.escape(cfg["ease"])}"'
        if cfg.get("rise"):
            root_attrs += f' data-rise="{int(cfg["rise"])}"'
    runtime = motion_css = ""
    if motion:
        motion_css = "[data-s]{opacity:0;}"
        runtime = "<script>" + (SCRIPTS / "motion-runtime.js").read_text() + "</script>"

    reg = "".join(f'<path d="M {x} {y + 22 * dy} V {y} H {x + 22 * dx}"/>'
                  for (x, y, dx, dy) in [(24, 24, 1, 1), (W - 24, 24, -1, 1), (24, H - 24, 1, -1), (W - 24, H - 24, -1, -1)])
    grid = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>' for x in range(M, W - M + 1, 48))
    grid += "".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>' for y in range(0, H + 1, 48))

    badge = {"typed": "TYPED", "code": "CODE", "human": "HUMAN"}
    cols, n = [], 0
    t0 = T_BLOCK
    for i, s in enumerate(cfg["sections"]):
        cards = []
        for j, c in enumerate(s["cards"]):
            n += 1
            ts = t0 + 260 + i * 150 + j * 700
            head = (f'<div class="mhead"><span class="mnum">{n:02d}</span><span class="mk {c["kind"]}">{badge[c["kind"]]}'
                    f'{" · " + c["type"] if c["kind"] == "typed" else ""}</span></div>')
            chips = ""
            if c["kind"] == "typed":
                opts = c.get("options") or []
                chips = "".join(f'<span class="mc{" ab" if o == c.get("abstain") else ""}"{anim(ts + 300 + k * 110, MD, "pop")}>{esc(o)}</span>'
                                for k, o in enumerate(opts))
                if c["type"] == "noul":
                    chips = '<span class="mc p">0 to 1 · no confidence</span>'
                chips = f'<div class="mchips">{chips}</div>'
            lines = "".join(f'<li>{esc(l)}</li>' for l in c["lines"])
            cards.append(f'<div class="mcard {c["kind"]}"{anim(ts, LG, "blur" if c["kind"] == "human" else "scale")}>{head}<p class="mtitle">{esc(c["title"])}</p>'
                         f'{chips}<ul class="mlines">{lines}</ul></div>')
        cols.append(f'<div class="mcol"><div class="msec"{anim(t0 + i * 150, 900, "type")}><p class="mlab">{esc(s["label"])}</p>'
                    f'<p class="mq">{esc(s["question"])}</p></div>{"".join(cards)}</div>')
    legend = "".join(f'<span class="lg"><span class="mk {k}">{badge[k]}</span>{esc(v)}</span>'
                     for k, v in cfg["legend"].items())

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
#slide-1{{text-wrap:balance;box-shadow:inset 0 0 0 1px {T['border']};position:relative;width:{W}px;height:{H}px;overflow:hidden;
  background:{T['canvas']};color:{T['text']};font-family:'{font_family}',sans-serif;}}
.bg{{position:absolute;left:0;top:0;}}
.bg line{{stroke:{T['hairline']};stroke-width:1;}}
.bg path{{fill:none;stroke:{T['accent']};stroke-width:2;}}
.abs{{position:absolute;left:{M}px;right:{M}px;}}
.meta{{top:{Y_META}px;display:flex;justify-content:space-between;font-family:'{mono_family}',monospace;
  font-size:15px;letter-spacing:.04em;color:{T['sub']};}}
.rule{{top:{Y_RULE}px;height:0;border-top:1px solid {T['text']};}}
.frame{{top:{Y_TITLE}px;height:{BL_BODY_BOTTOM - Y_TITLE}px;display:flex;flex-direction:column;}}
.title{{font-size:64px;font-weight:700;letter-spacing:-.05em;line-height:.98;}}
.sub{{margin-top:12px;font-size:19px;color:{T['sub']};}}
.g{{color:{T['accent']};}}
.legend{{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px 22px;font-family:'{mono_family}',monospace;font-size:12.5px;}}
.lg{{display:flex;align-items:center;gap:8px;}}
.mk{{font-family:'{mono_family}',monospace;font-size:10.5px;font-weight:700;letter-spacing:.08em;padding:2px 6px;
  border:1px solid {T['text']};}}
.mk.typed{{background:{T['accent']};border-color:{T['accent']};color:{T['canvas']};}}
.mk.code{{background:{T['text']};color:{T['canvas']};}}
.mk.human{{border-style:dashed;}}
.mgrid{{flex:1;margin-top:16px;display:grid;grid-template-columns:repeat(3,1fr);gap:12px;min-height:0;}}
.mcol{{display:flex;flex-direction:column;gap:8px;min-height:0;}}
.msec{{border-top:3px solid {T['text']};padding-top:8px;}}
.mlab{{font-size:26px;font-weight:700;letter-spacing:-.03em;line-height:1;}}
.mq{{margin-top:5px;font-family:'{mono_family}',monospace;font-size:12px;line-height:1.3;color:{T['sub']};}}
.mcard{{flex:1 0 auto;border:1px solid {T['text']};background:{T['canvas']};padding:9px 10px;}}
.mcard.typed{{background:{T['island_bg']};}}
.mcard.human{{border-style:dashed;}}
.mhead{{display:flex;align-items:center;gap:8px;}}
.mnum{{font-family:'{mono_family}',monospace;font-size:13px;font-weight:700;}}
.mtitle{{margin-top:6px;font-size:16px;font-weight:600;letter-spacing:-.015em;line-height:1.12;}}
.mchips{{margin-top:6px;display:flex;flex-wrap:wrap;gap:4px;}}
.mc{{font-family:'{mono_family}',monospace;font-size:10px;padding:1px 5px;border:1px solid {T['text']};background:{T['canvas']};}}
.mc.ab{{background:{T['accent']};border-color:{T['accent']};color:{T['canvas']};font-weight:700;}}
.mc.p{{border-style:dashed;color:{T['sub']};}}
.mlines{{margin-top:6px;list-style:none;font-family:'{mono_family}',monospace;font-size:10.5px;line-height:1.32;color:{T['sub']};}}
.mlines li::before{{content:"→ ";color:{T['accent']};}}
.foot-rule{{top:{Y_FOOT_RULE}px;height:0;border-top:1px solid {T['text']};}}
.foot{{top:{Y_FOOT}px;display:flex;align-items:center;justify-content:space-between;}}
.src{{font-family:'{mono_family}',monospace;font-size:12px;color:{T['sub']};text-align:right;}}
{motion_css}
{brandkit.footer_lock(T, F, 0.7)['css']}
</style></head><body><div id="slide-1"{root_attrs}>
<svg class="bg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><g>{grid}</g><g>{reg}</g></svg>
<div class="abs meta"><span>{esc(cfg['meta_left'])}</span><span>{esc(cfg.get('meta_right', ''))}</span></div>
<div class="abs rule"></div>
<div class="abs frame"><h1 class="title">{esc(cfg['title'])}</h1>
<p class="sub">{esc(cfg['sub'])}</p>
<div class="legend">{legend}</div>
<div class="mgrid">{''.join(cols)}</div></div>
<div class="abs foot-rule"></div>
<div class="abs foot">{brandkit.footer_lock(T, F, 0.7)['who']}
<div class="src">{esc(cfg.get('source', ''))}</div></div>
</div>{runtime}</body></html>"""


# ============================================================================
# Layout "flow": a TALL architecture poster (default 1080x2160) that builds top
# to bottom. Stages are stacked boxes joined by drawn connectors; a stage holds
# 1 to 3 cards side by side, an optional decision diamond (gate) and optional
# confidence bands. A left rail carries the standing rules. The build order IS
# the reading order: stage frame unrolls, its cards land, the connector draws
# down to the next stage.
# Card kinds: typed / code / human (as in "mega") plus llm (words get written).
# "height" 1350..2700 (1350 = feed portrait). Stage tags read 01, 02, ... by
# default; "number_from": 0 opts back into 00-based tags for an intake stage.
# ============================================================================
FL_KINDS = MG_KINDS | {"llm"}
FL_RAIL_W = 232
FL_GAP = 24
# Type floor for every small line in "flow" (badges, chips, detail lines, ticks,
# captions, footer): gates/card-infographic.md gate 6, 12.5px at 1080 wide. These
# sat at 10 to 12px and the impeccable detector flagged them on every render. If a
# config no longer fits, the fix is spacing or fewer words, never smaller type.
FL_MIN_PX = 12.5
# Feed-portrait profile (2026-10-04, from Taste Loop B, portrait flow at 1350).
# At 1350 a flow card has 4 or so stages and lots of air, and the reviewer scored
# the 12.5px floor as unreadable at feed width; this set passed the loop at 9.1.
# It applies only at FL_PORTRAIT_H: the 2160 poster carries twice the stages and
# would overflow at these sizes. Colours stay theme token NAMES, resolved per theme.
FL_PORTRAIT_H = 1350
FL_TYPE = {
    "tall": dict(rail_w=FL_RAIL_W, min_px=FL_MIN_PX, rail_justify="space-around", rail_gap=26,
                 rline_px=14, rline_mt=5, stag_px=13, mtitle_px=15,
                 mlines_px=FL_MIN_PX, mlines_mt=4, mlines_lh=1.3, mlines_color="sub", gq_px=14,
                 conn_h=26, conn_line=1.5, arrow_half=6, arrow_h=8, accent_figures=False),
    # Rail blocks spread over the stage column's full height (space-between) so the
    # rail ends where the last stage ends; detail lines move from sub to text colour
    # because 19px mono in the sub grey read as disabled. Heavier connectors keep the
    # build order legible at feed size. Proof figures in rail lines take the accent.
    "portrait": dict(rail_w=270, min_px=18, rail_justify="space-between", rail_gap=30,
                     rline_px=21, rline_mt=6, stag_px=16, mtitle_px=19,
                     mlines_px=19, mlines_mt=6, mlines_lh=1.35, mlines_color="text", gq_px=16,
                     conn_h=34, conn_line=3, arrow_half=11, arrow_h=14, accent_figures=True),
}
# A proof figure inside a rail line: 18, 310K, 110%, 2.5M.
FL_FIGURE = re.compile(r"(\d[\d.,]*[KM%]?)")


def validate_flow(cfg):
    h = cfg.get("height", 2160)
    if not 1350 <= int(h) <= 2700:
        raise SystemExit(f"flow: height {h} outside 1350..2700")
    stages = cfg.get("stages") or []
    if not 4 <= len(stages) <= 8:
        raise SystemExit(f"card-infographic 'flow' renders 4 to 8 stages, config has {len(stages)}")
    for i, st in enumerate(stages):
        # Stage numbers are generated (01, 02, ... or 00 with number_from 0): as config text they read as figures to the claims gate.
        extra = set(st) - {"title", "note", "cards", "gate", "bands"}
        if extra or not st.get("title") or not st.get("cards"):
            raise SystemExit(f"stage {i + 1}: needs title/cards (+ note, gate, bands), got {sorted(st)}")
        if not 1 <= len(st["cards"]) <= 3:
            raise SystemExit(f"stage {i + 1}: 1 to 3 cards, has {len(st['cards'])}")
        for j, c in enumerate(st["cards"]):
            where = f"stage {i + 1} card {j + 1}"
            extra = set(c) - {"kind", "title", "type", "options", "abstain", "lines"}
            if extra or c.get("kind") not in FL_KINDS or not c.get("title") or not c.get("lines"):
                raise SystemExit(f"{where}: needs kind {sorted(FL_KINDS)}, title, lines, got {sorted(c)}")
            if c["kind"] == "typed":
                if c.get("type") not in BL_TYPES:
                    raise SystemExit(f"{where}: typed card needs type in {sorted(BL_TYPES)}")
                opts = c.get("options") or []
                if c["type"] == "noul" and opts:
                    raise SystemExit(f"{where}: a noul has no options")
                if c["type"] != "noul" and not 2 <= len(opts) <= 6:
                    raise SystemExit(f"{where}: {c['type']} needs 2 to 6 options, has {len(opts)}")
                if c.get("abstain") and c["abstain"] not in opts:
                    raise SystemExit(f"{where}: abstain {c['abstain']!r} is not one of its options")
            elif set(c) & {"type", "options", "abstain"}:
                raise SystemExit(f"{where}: only a typed card may carry type/options/abstain")
        g = st.get("gate")
        if g is not None and set(g) != {"q", "yes", "no"}:
            raise SystemExit(f"stage {i + 1}: gate needs exactly q/yes/no, got {sorted(g)}")
        b = st.get("bands")
        if b is not None and (set(b) != {"markers", "labels", "caption"} or len(b["labels"]) != len(b["markers"]) + 1):
            raise SystemExit(f"stage {i + 1}: bands need markers, labels (markers + 1) and a caption")
    if cfg.get("number_from", 1) not in (0, 1) or isinstance(cfg.get("number_from"), bool):
        raise SystemExit(f"flow: number_from is 0 or 1 (default 1, steps read 01, 02, ...), got {cfg.get('number_from')!r}")
    rail = cfg.get("rail") or []
    if len(rail) > 4 or any(set(r) != {"head", "lines"} for r in rail):
        raise SystemExit("flow: rail is 0 to 4 blocks of exactly head/lines")
    if not cfg.get("legend"):
        raise SystemExit("flow: 'legend' is required")


def build_flow(cfg, theme, motion):
    T = brandkit.theme(BRAND, theme)
    font_family, _, font_import = brandkit.font(BRAND, cfg)
    mono_family, _ = brandkit.mono(BRAND)
    mono_family = mono_family or font_family
    F = brandkit.footer(BRAND, cfg)
    FH = int(cfg.get("height", 2160))
    P = FL_TYPE["portrait" if FH == FL_PORTRAIT_H else "tall"]
    n_st = len(cfg["stages"])
    first = cfg.get("number_from", 1)   # posts number steps from 1; 0 = opt-in for an intake stage
    STEP = 2000                      # ms per stage
    T0 = 900
    dissolve = T0 + n_st * STEP + 2600

    def anim(s, d=MD, fx=None):
        # Header, rail frame and footer never animate: frame 0 reads as the card.
        if not motion:
            return ""
        return (f' data-s="{int(s)}" data-d="{int(d)}" data-out="{dissolve}" data-outd="{DISSOLVE_D}"'
                + (f' data-fx="{fx}"' if fx else ""))

    root_attrs = ""
    if motion and cfg.get("ease"):
        root_attrs += f' data-ease="{html.escape(cfg["ease"])}"'
        if cfg.get("rise"):
            root_attrs += f' data-rise="{int(cfg["rise"])}"'
    runtime = motion_css = ""
    if motion:
        motion_css = "[data-s]{opacity:0;}"
        runtime = "<script>" + (SCRIPTS / "motion-runtime.js").read_text() + "</script>"

    grid = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{FH}"/>' for x in range(M, W - M + 1, 48))
    grid += "".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>' for y in range(0, FH + 1, 48))
    reg = "".join(f'<path d="M {x} {y + 22 * dy} V {y} H {x + 22 * dx}"/>'
                  for (x, y, dx, dy) in [(24, 24, 1, 1), (W - 24, 24, -1, 1), (24, FH - 24, 1, -1), (W - 24, FH - 24, -1, -1)])
    badge = {"typed": "TYPED", "code": "CODE", "human": "HUMAN", "llm": "LLM"}

    def card(c, ts):
        head = (f'<div class="mhead"><span class="mk {c["kind"]}">{badge[c["kind"]]}'
                f'{" · " + c["type"] if c["kind"] == "typed" else ""}</span></div>')
        chips = ""
        if c["kind"] == "typed":
            opts = c.get("options") or []
            chips = "".join(f'<span class="mc{" ab" if o == c.get("abstain") else ""}"{anim(ts + 350 + k * 110, MD, "pop")}>{esc(o)}</span>'
                            for k, o in enumerate(opts))
            if c["type"] == "noul":
                chips = f'<span class="mc p"{anim(ts + 350, MD, "pop")}>0 to 1 · no confidence</span>'
            chips = f'<div class="mchips">{chips}</div>'
        lines = "".join(f'<li>{esc(l)}</li>' for l in c["lines"])
        fx = {"typed": "scale", "code": "left", "human": "blur", "llm": "right"}[c["kind"]]
        return (f'<div class="fcard {c["kind"]}"{anim(ts, LG, fx)}>{head}<p class="mtitle">{esc(c["title"])}</p>'
                f'{chips}<ul class="mlines">{lines}</ul></div>')

    stages = []
    for i, st in enumerate(cfg["stages"]):
        ts = T0 + i * STEP
        cards = "".join(card(c, ts + 350 + j * 260) for j, c in enumerate(st["cards"]))
        gate = ""
        if st.get("gate"):
            g = st["gate"]
            gate = (f'<div class="gate"{anim(ts + 1100, MD, "pop")}><span class="dia"></span>'
                    f'<div><p class="gq">{esc(g["q"])}</p><p class="gy"><b>yes</b> {esc(g["yes"])}</p>'
                    f'<p class="gn"><b>no</b> {esc(g["no"])}</p></div></div>')
        bands = ""
        if st.get("bands"):
            b = st["bands"]
            edges = [0.0, *b["markers"], 1.0]
            segs = "".join(f'<div class="band b{k}" style="flex:{edges[k + 1] - edges[k]:.3f}"{anim(ts + 700 + k * 180, MD, "left")}>'
                           f'<span>{esc(lab)}</span></div>' for k, lab in enumerate(b["labels"]))
            ticks = "".join(f'<span class="btick" style="left:{v * 100:.2f}%">{v:g}</span>' for v in edges)
            bands = (f'<div class="fbands"><div class="brow">{segs}</div><div class="bticks"{anim(ts + 700, MD)}>{ticks}</div>'
                     f'<p class="bcap"{anim(ts + 1300, 900, "type")}>{esc(b["caption"])}</p></div>')
        note = f'<p class="snote"{anim(ts + 200, 800, "type")}>{esc(st["note"])}</p>' if st.get("note") else ""
        conn = (f'<div class="conn"{anim(ts - 380, 380, "unroll")}><span class="arrow"></span></div>' if i else "")
        stages.append(f'{conn}<section class="stage"{anim(ts, LG, "unroll")}><div class="shead"><span class="stag">{i + first:02d}</span>'
                      f'<p class="stitle">{esc(st["title"])}</p></div>{note}'
                      f'<div class="srow n{len(st["cards"])}">{cards}</div>{gate}{bands}</section>')

    def rline(l):
        # esc() emits no digits of its own (quote=False, no numeric entities), so the
        # figure regex only ever wraps text the config wrote.
        return FL_FIGURE.sub(r"<b>\1</b>", esc(l)) if P["accent_figures"] else esc(l)
    rline_b = f"\n.rline b{{font-weight:700;color:{T['accent']};}}" if P["accent_figures"] else ""

    rail = "".join(f'<div class="rblock"{anim(T0 + 200 + k * 2 * STEP, LG, "left")}><p class="rhead">{esc(r["head"])}</p>'
                   + "".join(f'<p class="rline">{rline(l)}</p>' for l in r["lines"]) + '</div>'
                   for k, r in enumerate(cfg.get("rail") or []))
    legend = "".join(f'<span class="lg"><span class="mk {k}">{badge[k]}</span>{esc(v)}</span>'
                     for k, v in cfg["legend"].items())
    y_foot_rule, y_foot = FH - 122, FH - 106
    cta = (f'<span class="cta">{esc(cfg["cta"])}</span>' if cfg.get("cta") else "")

    # Root padding:{M}px moves nothing (every child is absolute, placed from the
    # padding edge). It declares the real inset, so impeccable stops reading the
    # canvas as a container with children flush against its background.
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
#slide-1{{text-wrap:balance;box-shadow:inset 0 0 0 1px {T['border']};position:relative;width:{W}px;height:{FH}px;overflow:hidden;
  padding:{M}px;background:{T['canvas']};color:{T['text']};font-family:'{font_family}',sans-serif;}}
.bg{{position:absolute;left:0;top:0;}}
.bg line{{stroke:{T['hairline']};stroke-width:1;}}
.bg path{{fill:none;stroke:{T['accent']};stroke-width:2;}}
.abs{{position:absolute;left:{M}px;right:{M}px;}}
.meta{{top:{Y_META}px;display:flex;justify-content:space-between;font-family:'{mono_family}',monospace;
  font-size:15px;letter-spacing:.04em;color:{T['sub']};}}
.rule{{top:{Y_RULE}px;height:0;border-top:1px solid {T['text']};}}
.frame{{top:{Y_TITLE}px;height:{y_foot_rule - 20 - Y_TITLE}px;display:flex;flex-direction:column;}}
.title{{font-size:72px;font-weight:700;letter-spacing:-.05em;line-height:.98;}}
.sub{{margin-top:12px;font-size:20px;color:{T['sub']};max-width:820px;}}
.g{{color:{T['accent']};}}
.legend{{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px 22px;font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;}}
.lg{{display:flex;align-items:center;gap:8px;}}
.mk{{font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;font-weight:700;letter-spacing:.08em;padding:2px 6px;border:1px solid {T['text']};}}
.mk.typed{{background:{T['accent']};border-color:{T['accent']};color:{T['canvas']};}}
.mk.code{{background:{T['text']};color:{T['canvas']};}}
.mk.human{{border-style:dashed;}}
.mk.llm{{border-color:{T['accent']};color:{T['accent']};}}
.cols{{flex:1;margin-top:16px;display:grid;grid-template-columns:{P['rail_w']}px 1fr;gap:{FL_GAP}px;min-height:0;}}
.rail{{display:flex;flex-direction:column;justify-content:{P['rail_justify']};gap:{P['rail_gap']}px;border-right:1px solid {T['hairline']};padding-right:18px;}}
.rhead{{font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:{T['accent']};margin-bottom:6px;}}
.rline{{font-size:{P['rline_px']}px;line-height:1.3;margin-top:{P['rline_mt']}px;}}{rline_b}
.flow{{display:flex;flex-direction:column;justify-content:space-between;min-height:0;}}
.stage{{border:1.5px solid {T['text']};background:{T['canvas']};padding:10px 14px;}}
.shead{{display:flex;align-items:baseline;gap:10px;}}
.stag{{font-family:'{mono_family}',monospace;font-size:{P['stag_px']}px;font-weight:700;background:{T['text']};color:{T['canvas']};padding:2px 6px;}}
.stitle{{font-size:21px;font-weight:700;letter-spacing:-.02em;}}
.snote{{margin-top:4px;font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;color:{T['sub']};}}
.srow{{margin-top:8px;display:grid;gap:8px;}}
.srow.n1{{grid-template-columns:1fr;}} .srow.n2{{grid-template-columns:1fr 1fr;}} .srow.n3{{grid-template-columns:1fr 1fr 1fr;}}
.fcard{{border:1px solid {T['text']};background:{T['canvas']};padding:7px 9px;}}
.fcard.typed{{background:{T['island_bg']};}}
.fcard.human{{border-style:dashed;}}
.fcard.llm{{border-color:{T['accent']};}}
.mhead{{display:flex;align-items:center;gap:8px;}}
.mtitle{{margin-top:4px;font-size:{P['mtitle_px']}px;font-weight:600;letter-spacing:-.015em;line-height:1.3;}}
.mchips{{margin-top:5px;display:flex;flex-wrap:wrap;gap:4px;}}
.mc{{font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;padding:1px 5px;border:1px solid {T['text']};background:{T['canvas']};}}
.mc.ab{{background:{T['accent']};border-color:{T['accent']};color:{T['canvas']};font-weight:700;}}
.mc.p{{border-style:dashed;color:{T['sub']};}}
.mlines{{margin-top:{P['mlines_mt']}px;list-style:none;font-family:'{mono_family}',monospace;font-size:{P['mlines_px']}px;line-height:{P['mlines_lh']};color:{T[P['mlines_color']]};}}
.mlines li::before{{content:"→ ";color:{T['accent']};}}
.gate{{margin-top:8px;display:flex;align-items:center;gap:14px;}}
.dia{{flex:none;width:22px;height:22px;transform:rotate(45deg);border:1.5px solid {T['text']};background:{T['canvas']};}}
.gq{{font-size:{P['gq_px']}px;font-weight:600;}}
.gy,.gn{{font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;color:{T['sub']};}}
.gy b,.gn b{{color:{T['text']};margin-right:6px;}}
.fbands{{margin-top:8px;}}
.brow{{display:flex;height:30px;border:1px solid {T['text']};}}
.band{{display:flex;align-items:center;padding-left:8px;font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;font-weight:700;
  letter-spacing:.06em;border-left:1px solid {T['text']};background:{T['canvas']};}}
.band.b0{{border-left:0;}}
.band:last-child{{background:{T['text']};color:{T['canvas']};}}
.bticks{{position:relative;height:18px;}}
.btick{{position:absolute;top:3px;transform:translateX(-50%);font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;color:{T['sub']};}}
.btick:first-child{{transform:none;}} .btick:last-child{{transform:translateX(-100%);}}
.bcap{{font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;color:{T['sub']};}}
.conn{{position:relative;height:{P['conn_h']}px;display:flex;justify-content:center;}}
.conn::before{{content:"";width:0;height:100%;border-left:{P['conn_line']}px dashed {T['text']};}}
.arrow{{position:absolute;top:{P['conn_h'] - P['arrow_h']}px;width:0;height:0;border-left:{P['arrow_half']}px solid transparent;border-right:{P['arrow_half']}px solid transparent;
  border-top:{P['arrow_h']}px solid {T['text']};}}
.foot-rule{{top:{y_foot_rule}px;height:0;border-top:1px solid {T['text']};}}
.foot{{top:{y_foot}px;display:flex;align-items:center;justify-content:space-between;}}
.foot-r{{display:flex;align-items:center;gap:18px;}}
.src{{font-family:'{mono_family}',monospace;font-size:{P['min_px']}px;color:{T['sub']};text-align:right;}}
.cta{{font-family:'{mono_family}',monospace;font-size:13px;font-weight:700;background:{T['accent']};color:{T['canvas']};padding:7px 12px;}}
{motion_css}
{brandkit.footer_lock(T, F, 0.7)['css']}
</style></head><body><div id="slide-1"{root_attrs}>
<svg class="bg" viewBox="0 0 {W} {FH}" width="{W}" height="{FH}"><g>{grid}</g><g>{reg}</g></svg>
<div class="abs meta"><span>{esc(cfg['meta_left'])}</span><span>{esc(cfg.get('meta_right', ''))}</span></div>
<div class="abs rule"></div>
<div class="abs frame"><h1 class="title">{esc(cfg['title'])}</h1>
<p class="sub">{esc(cfg['sub'])}</p>
<div class="legend">{legend}</div>
<div class="cols"><div class="rail">{rail}</div><div class="flow">{''.join(stages)}</div></div></div>
<div class="abs foot-rule"></div>
<div class="abs foot">{brandkit.footer_lock(T, F, 0.7)['who']}
<div class="foot-r"><div class="src">{esc(cfg.get('source', ''))}</div>{cta}</div></div>
</div>{runtime}</body></html>"""


def self_test():
    """Two-sided: a valid config builds; each seeded violation is REJECTED."""
    ok_nodes = [{"name": f"N{i}", "fix": "do x"} for i in range(9)]
    base = {"format": "card-infographic", "layout": "spine", "meta_left": "m", "title": "t", "sub": "s",
            "cells": [{"label": "A", "line": "l", "detail": "d", "emph": "e"}] * 3, "readout": "r",
            "nodes": ok_nodes, "scale": {"markers": [0.5], "labels": ["a"], "caption": "c"}}
    global BRAND
    BRAND = brandkit.load(None)
    out = build(base, "light", False)
    assert out.count('class="node') == 9 and "data-s" not in out, "clean static build"
    m = _build(dict(base, ease="0.2,0.8,0.2,1", rise=16), "light", True)
    assert 'data-ease="0.2,0.8,0.2,1"' in m and "data-draw" in m and 'data-tip="#pen"' in m, "clean motion build"
    g = spine(9)
    ats = [n["at"] for n in g["nodes"]]
    assert ats == sorted(ats) and 0 < ats[0] < ats[-1] < g["total"], "node order follows the path"
    assert [n["right"] for n in g["nodes"]][:3] == [True, False, True], "turns alternate right/left"
    seeded = [
        ("unknown key", dict(base, eyebrow="x")),
        ("unknown node key", dict(base, nodes=[dict(ok_nodes[0], kicker="x")] + ok_nodes[1:])),
        ("too many nodes", dict(base, nodes=ok_nodes + ok_nodes[:1])),
        ("too few nodes", dict(base, nodes=ok_nodes[:4])),
        ("two cells", dict(base, cells=base["cells"][:2])),
        ("scale without caption", dict(base, scale={"markers": [0.5], "labels": ["a"]})),
        ("unbuilt layout", dict(base, layout="hexagon")),
    ]
    for name, cfg in seeded:
        try:
            build(cfg, "light", False)
        except SystemExit:
            continue
        raise AssertionError(f"seeded violation NOT rejected: {name}")
    # ---- layout "cycle"
    steps = [{"name": f"S{i}", "detail": "d"} for i in range(6)]
    cyc = {"format": "card-infographic", "layout": "cycle", "meta_left": "m", "title": "t", "sub": "s",
           "steps": steps, "core": {"kicker": "K", "line": "L"},
           "quote": {"text": "q", "cite": "c"}, "loop_note": "n"}
    out = build(cyc, "light", False)
    assert out.count('class="node"') == 6 and out.count('class="seg"') == 6 and "data-s" not in out, "clean cycle"
    m = _build(dict(cyc, ease="0.2,0.8,0.2,1"), "light", True)
    assert "data-draw" in m and 'data-ease="0.2,0.8,0.2,1"' in m, "clean cycle motion"
    hx = hexagon(0, 0, 10)
    assert abs(hx[0][0]) < 1e-9 and hx[0][1] < 0 and hx[1][0] > 0, "hexagon starts at the top, runs clockwise"
    cseeded = [
        ("cycle: 5 steps", dict(cyc, steps=steps[:5])),
        ("cycle: step extra key", dict(cyc, steps=[dict(steps[0], fix="x")] + steps[1:])),
        ("cycle: core missing line", dict(cyc, core={"kicker": "K"})),
        ("cycle: quote without cite", dict(cyc, quote={"text": "q", "cite": ""})),
        ("cycle: spine key in cycle", dict(cyc, nodes=ok_nodes)),
    ]
    for name, cfg in cseeded:
        try:
            build(cfg, "light", False)
        except SystemExit:
            continue
        raise AssertionError(f"seeded violation NOT rejected: {name}")
    # ---- layouts "decisions" + "sort"
    decs = [{"name": "N", "type": "noul", "ask": "a", "route": "r"},
            {"name": "T", "type": "choice", "ask": "a", "options": ["x", "y", "UNRESOLVED"], "abstain": "UNRESOLVED", "route": "r"},
            {"name": "S", "type": "score", "ask": "a", "options": ["lo", "hi"], "route": "r"}]
    dcfg = {"format": "card-infographic", "layout": "decisions", "meta_left": "m", "title": "t", "sub": "s",
            "decisions": decs, "bands": {"markers": [0.5, 0.9], "labels": ["A", "B", "C"], "caption": "c"}}
    out = build(dcfg, "light", False)
    assert out.count('class="dec"') == 3 and out.count('class="chip ab"') == 1 and "data-s" not in out, "clean decisions"
    assert "data-s" in _build(dict(dcfg, ease="0.2,0.8,0.2,1"), "light", True), "decisions motion"
    hf = _build(dict(dcfg, ease="0.2,0.8,0.2,1", motion_style="headers_first"), "light", True)
    assert hf.count('class="dec"') == 3 and 'data-fx="scale"' in hf, "decisions headers_first uses a different entrance"
    assert hf != _build(dict(dcfg, ease="0.2,0.8,0.2,1"), "light", True), "headers_first must not render identically to the default cascade"
    cols = [{"label": L, "rule": "r", "items": [{"task": "t", "why": "w"}] * 3} for L in "ABC"]
    scfg = {"format": "card-infographic", "layout": "sort", "meta_left": "m", "title": "t", "sub": "s", "columns": cols}
    out = build(scfg, "light", False)
    assert out.count("<li>") == 9 and out.count('class="col ') == 3, "clean sort"
    bseeded = [
        ("decisions: noul with options", dict(dcfg, decisions=[dict(decs[0], options=["a", "b"])] + decs[1:])),
        ("decisions: abstain not an option", dict(dcfg, decisions=[decs[0], dict(decs[1], abstain="none")] + decs[2:])),
        ("decisions: not a Jev type", dict(dcfg, decisions=[dict(decs[0], type="bool")] + decs[1:])),
        ("decisions: bands labels mismatch", dict(dcfg, bands={"markers": [0.5], "labels": ["A"], "caption": "c"})),
        ("decisions: two decisions", dict(dcfg, decisions=decs[:2])),
        ("sort: two columns", dict(scfg, columns=cols[:2])),
        ("sort: item extra key", dict(scfg, columns=[dict(cols[0], items=[{"task": "t", "why": "w", "x": 1}] * 3)] + cols[1:])),
    ]
    for name, cfg in bseeded:
        try:
            build(cfg, "light", False)
        except SystemExit:
            continue
        raise AssertionError(f"seeded violation NOT rejected: {name}")
    # ---- layout "mega"
    tc = {"kind": "typed", "title": "t", "type": "choice", "options": ["a", "b", "UNRESOLVED"], "abstain": "UNRESOLVED", "lines": ["l"]}
    cc = {"kind": "code", "title": "t", "lines": ["l"]}
    hc = {"kind": "human", "title": "t", "lines": ["l"]}
    secs = [{"label": "A", "question": "q", "cards": [tc, cc, hc]} for _ in range(3)]
    mcfg = {"format": "card-infographic", "layout": "mega", "meta_left": "m", "title": "t", "sub": "s",
            "sections": secs, "legend": {"typed": "x", "code": "y", "human": "z"}}
    out = build(mcfg, "light", False)
    assert out.count('class="mcard ') == 9 and out.count('class="mc ab"') == 3 and "data-s" not in out, "clean mega"
    mm = _build(dict(mcfg, ease="0.2,0.8,0.2,1"), "light", True)
    assert "data-s" in mm and 'data-fx="pop"' in mm, "mega motion"
    # Frame 0 must read as the card: header and footer carry no animation.
    for html_ in (mm, _build(dict(scfg, ease="0.2,0.8,0.2,1"), "light", True)):
        for cls in ('class="title"', 'class="sub"', 'class="abs meta"', 'class="abs foot"'):
            tag = html_[html_.index(cls):html_.index(">", html_.index(cls))]
            assert "data-s" not in tag, f"header element animates, frame 0 would be empty: {cls}"
    mseeded = [
        ("mega: two sections", dict(mcfg, sections=secs[:2])),
        ("mega: code card with options", dict(mcfg, sections=[{"label": "A", "question": "q", "cards": [tc, dict(cc, options=["a", "b"]), hc]}] + secs[1:])),
        ("mega: unknown kind", dict(mcfg, sections=[{"label": "A", "question": "q", "cards": [tc, dict(cc, kind="llm"), hc]}] + secs[1:])),
        ("mega: abstain not an option", dict(mcfg, sections=[{"label": "A", "question": "q", "cards": [dict(tc, abstain="none"), cc, hc]}] + secs[1:])),
        ("mega: no legend", {k: v for k, v in mcfg.items() if k != "legend"}),
    ]
    for name, cfg in mseeded:
        try:
            build(cfg, "light", False)
        except SystemExit:
            continue
        raise AssertionError(f"seeded violation NOT rejected: {name}")
    # ---- layout "flow"
    lc = {"kind": "llm", "title": "t", "lines": ["l"]}
    stg = [{"title": "s", "cards": [tc, cc]} for k in range(4)]
    stg[1] = dict(stg[1], gate={"q": "q", "yes": "y", "no": "n"}, cards=[cc])
    stg[2] = dict(stg[2], bands={"markers": [0.5, 0.9], "labels": ["a", "b", "c"], "caption": "c"}, cards=[tc, hc, lc])
    fcfg = {"format": "card-infographic", "layout": "flow", "meta_left": "m", "title": "t", "sub": "s", "stages": stg,
            "legend": {"typed": "x", "code": "y"}, "rail": [{"head": "h", "lines": ["l"]}], "height": 2160, "cta": "c"}
    out = build(fcfg, "light", False)
    assert out.count('class="stage"') == 4 and out.count('class="conn"') == 3 and 'class="gate"' in out and "height:2160px" in out, "clean flow"
    # Type floor, two-sided: no flow text under FL_MIN_PX, and the check sees a seeded 10.5px.
    small = lambda h: [x for x in re.findall(r"font-size:([\d.]+)px", h) if float(x) < FL_MIN_PX]
    assert not small(out) and not small(build(dict(fcfg, height=1350), "light", False)), f"flow type under the floor: {small(out)}"
    assert small(out.replace(f"font-size:{FL_MIN_PX}px", "font-size:10.5px", 1)), "floor check misses a seeded 10.5px"
    # Portrait profile, two-sided: 1350 gets the 9.1 type and accent figures, 2160 keeps the tall set.
    pc = dict(fcfg, height=FL_PORTRAIT_H, rail=[{"head": "h", "lines": ["310K students"]}])
    po, to = build(pc, "light", False), build(dict(pc, height=2160), "light", False)
    assert f"font-size:{FL_TYPE['portrait']['min_px']}px" in po and "<b>310K</b>" in po, "portrait profile not applied at 1350"
    assert "<b>310K</b>" not in to and f"grid-template-columns:{FL_RAIL_W}px" in to, "portrait profile leaked into the tall poster"
    assert not [x for x in re.findall(r"\.(?:legend|mk|rhead|snote|mc|mlines|rline)\{\{?[^}]*font-size:([\d.]+)px", po)
                if float(x) < FL_TYPE['portrait']['min_px']], "portrait small type under its 18px floor"
    tags = lambda h: re.findall(r'class="stag">(\d+)<', h)
    assert tags(out) == ["01", "02", "03", "04"], f"flow steps number from 01 by default, got {tags(out)}"
    assert tags(build(dict(fcfg, number_from=0), "light", False)) == ["00", "01", "02", "03"], "number_from 0 keeps 00"
    fm = _build(dict(fcfg, ease="0.2,0.8,0.2,1"), "light", True)
    for cls in ('class="title"', 'class="sub"', 'class="abs meta"', 'class="abs foot"'):
        tag = fm[fm.index(cls):fm.index(">", fm.index(cls))]
        assert "data-s" not in tag, f"flow header animates: {cls}"
    assert 'data-fx="unroll"' in fm and 'data-fx="blur"' in fm, "flow motion uses varied entrances"
    fseeded = [
        ("flow: three stages", dict(fcfg, stages=stg[:3])),
        ("flow: four cards in a stage", dict(fcfg, stages=[dict(stg[0], cards=[tc, cc, hc, lc])] + stg[1:])),
        ("flow: gate missing no", dict(fcfg, stages=[dict(stg[0], gate={"q": "q", "yes": "y"})] + stg[1:])),
        ("flow: height too tall", dict(fcfg, height=4000)),
        ("flow: llm card with options", dict(fcfg, stages=[dict(stg[0], cards=[dict(lc, options=["a", "b"])])] + stg[1:])),
        ("flow: number_from 2", dict(fcfg, number_from=2)),
        ("flow: number_from true", dict(fcfg, number_from=True)),
        ("flow: number_from on spine", dict(base, number_from=0)),
    ]
    for name, cfg in fseeded:
        try:
            build(cfg, "light", False)
        except SystemExit:
            continue
        raise AssertionError(f"seeded violation NOT rejected: {name}")
    # ---- loop length vs dissolve, every layout (two-sided). A motion_ms equal to
    # the dissolve START shipped a broken seam (claim-check, 2026-09-27).
    lseeded = 0
    for name, cfg in (("spine", base), ("cycle", cyc), ("decisions", dcfg), ("sort", scfg),
                      ("mega", mcfg), ("flow", fcfg)):
        html_ = _build(cfg, "light", True)
        end = max(int(s) + int(d) for s, d in re.findall(r'data-out="(\d+)" data-outd="(\d+)"', html_))
        build(dict(cfg, motion_ms=end + 42), "light", True)              # fits: builds
        for bad in (end - 380, None):                                     # the claim-check bug; the 5500 default
            c = dict(cfg, motion_ms=bad) if bad else {k: v for k, v in cfg.items() if k != "motion_ms"}
            try:
                build(c, "light", True)
            except SystemExit:
                lseeded += 1
                continue
            raise AssertionError(f"{name}: motion_ms {bad or 'default 5500'} before dissolve end {end} NOT rejected")
    # ---- motion_extras (return / live / morph), two-sided
    rv = build(dict(dcfg, motion_ms=20000, motion_return="reverse"), "light", True)
    assert 'id="slide-1" data-return="reverse"' in rv, "reverse marks the root"
    pairs = [(int(a), int(b)) for a, b in re.findall(r'data-s="(\d+)"[^>]*?data-out="(\d+)"', rv)]
    assert len({o for _, o in pairs}) > 1, "reverse staggers the exits"
    assert max(pairs)[1] == min(o for _, o in pairs), "last element in is the first out"
    lv = build(dict(dcfg, motion_ms=20000, motion_live=True), "light", True)
    assert len(re.findall(r'<span class="chip ab" data-live="\d+,\d+"', lv)) == 1, "live pulses the abstain chip"
    mo = build(dict(dcfg, motion_ms=20000, motion_morph=True), "light", True)
    assert 'data-morph-to="#morph-target"' in mo and 'id="morph-target" class="band b0"' in mo, "morph wires chip to band 0"
    xseeded = [("motion_return typo", dict(dcfg, motion_ms=20000, motion_return="rewind")),
               ("morph on sort", dict(scfg, motion_ms=20000, motion_morph=True)),
               ("reverse makes the loop longer", dict(dcfg, motion_return="reverse",
                                                      motion_ms=int(re.findall(r'data-out="(\d+)"', _build(dcfg, "light", True))[0]) + 420))]
    for name, cfg in xseeded:
        try:
            build(cfg, "light", True)
        except SystemExit:
            lseeded += 1
            continue
        raise AssertionError(f"seeded violation NOT rejected: {name}")
    print(f"PASS infographic-card self-test (spine + cycle + decisions + sort + mega + flow, clean static + motion builds, "
          f"{len(seeded) + len(cseeded) + len(bseeded) + len(mseeded) + len(fseeded) + lseeded} seeded violations rejected)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--theme", choices=["light", "dark"], default="light")
    ap.add_argument("--motion", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--brand", help="path to brand.json")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test()
        return
    if not (a.config and a.out):
        ap.error("--config and --out are required (or --self-test)")
    global BRAND
    BRAND = brandkit.load(a.brand)
    cfg = json.loads(pathlib.Path(a.config).read_text())
    pathlib.Path(a.out).write_text(build(cfg, a.theme, a.motion))
    print(f"wrote {a.out} ({a.theme}{', motion' if a.motion else ''})")


if __name__ == "__main__":
    main()
