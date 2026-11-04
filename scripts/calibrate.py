#!/usr/bin/env python3
"""
calibrate.py — pin the cheapest critic tier that actually catches defects.

    python3 calibrate.py fixtures [--outdir dir]    # build the seeded-defect set
    python3 calibrate.py run [--tiers a,b] [--apply]  # measure, optionally pin
    python3 calibrate.py                             # self-check

Routing critics to a cheaper model saves most of the pipeline's cost. It is only
safe if the cheaper model still catches real defects, otherwise the review quietly
becomes ceremony: it runs, it costs less, and it approves everything.

So the tier is a MEASUREMENT, not a preference. This builds a fixture set where
every card has exactly one known, seeded defect (plus clean controls), asks a tier
to review each one, and reports catch rate and false-positive rate. Two-sided by
house standard: a tier that flags the clean controls is not "strict", it is broken.

`--apply` writes the winner into pipeline.json with the date and the model ids it
was measured against, so the pin has provenance and an expiry.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _pipeline():
    return json.loads((ROOT / "pipeline.json").read_text())


def _tiers_by_cost(pl):
    """Priced model ids cheapest-first. pricing carries a $comment key; skip non-dicts."""
    pricing = {m: p for m, p in pl["pricing"].items() if isinstance(p, dict)}
    return sorted(pricing, key=lambda m: pricing[m]["in"] + pricing[m]["out"])


# Workflow's agent() takes the ALIAS, not the model id; taste-loop.js routes on
# `.alias`. A pin that only writes `model` changes nothing at runtime.
_ALIAS_TOKEN = re.compile(r"(haiku|sonnet|opus|fable)")


def _alias_for(model_id):
    m = _ALIAS_TOKEN.search(model_id)
    return m.group(1) if m else None

# One seeded defect per fixture, each mapping to a gate a critic should catch by
# LOOKING. Deterministic checks (palette, dimensions) are excluded on purpose:
# qa-visual already catches those for free, so they measure nothing about a tier.
DEFECTS = {
    "clean-control-a": {"expect": "clean", "mutate": None},
    "clean-control-b": {"expect": "clean", "mutate": None},
    "tiny-label": {
        "expect": "defect", "gate": "legibility at feed size",
        "mutate": {"note": "*Measured across every engine* at a size nobody can read on a phone"},
        "css": (".note .main{{font-size:22px", ".note .main{{font-size:9px"),
    },
    "duplicated-identity": {
        "expect": "defect", "gate": "identity duplicated between header and footer",
        "mutate": {"window_title": "Anton Vnukov"},
    },
    "empty-footer-right": {
        "expect": "defect", "gate": "footer balance",
        "brand": {"footer": {"tagline": {"accent": "", "rest": ""}}},
    },
    "hero-metric-cliche": {
        "expect": "defect", "gate": "hero-metric cliche / eyebrow that says nothing",
        "mutate": {"headline": "Number", "note": "Data", "pill": "Info", "source": ""},
    },
    "overstated-claim": {
        "expect": "defect", "gate": "the same figure presented as two findings",
        "mutate": {"note": "*62.1%* of citations, and 62.1% of the value"},
    },
}

CRITIC_PROMPT = """You are an independent design reviewer. Look at the image at {png}.

Judge it against these gates:
{gates}

Reply with ONLY a JSON object, no prose:
{{"defectFound": true|false, "gate": "<which gate failed, or empty>", "why": "<one sentence>"}}

Set defectFound=false if the card satisfies every gate. Do not invent problems: a card that is
merely plain, or that you would have designed differently, is not a defect."""


def build_fixtures(outdir):
    """Render one card per defect. Returns [{name, png, expect, gate}]."""
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    base_cfg = json.loads((ROOT / "examples" / "bar-card.example.json").read_text())
    brand = json.loads((ROOT / "brand.example.json").read_text())
    node = _node()
    built = []

    for name, spec in DEFECTS.items():
        cfg = json.loads(json.dumps(base_cfg))
        cfg.update(spec.get("mutate") or {})
        cfg_path = outdir / f"{name}.json"
        cfg_path.write_text(json.dumps(cfg, indent=2))

        brand_path = ROOT / "brand.example.json"
        if spec.get("brand"):
            b = json.loads(json.dumps(brand))
            for k, v in spec["brand"].items():
                b[k] = {**b.get(k, {}), **v} if isinstance(v, dict) else v
            brand_path = outdir / f"{name}.brand.json"
            brand_path.write_text(json.dumps(b, indent=2))

        html = outdir / f"{name}.html"
        subprocess.run([sys.executable, str(SCRIPTS / "bar-card.py"), "--config", str(cfg_path),
                        "--theme", "light", "--brand", str(brand_path), "--out", str(html)],
                       check=True, capture_output=True)
        if spec.get("css"):
            find, repl = spec["css"]
            html.write_text(html.read_text().replace(find, repl))

        png_dir = outdir / f"{name}-png"
        subprocess.run([node, str(SCRIPTS / "capture.js"), "--html", str(html), "--slides", "1",
                        "--outdir", str(png_dir), "--scale", "2"], check=True, capture_output=True)
        png = outdir / f"{name}.png"
        shutil.copy(png_dir / "slide-1.png", png)
        built.append({"name": name, "png": str(png), "expect": spec["expect"], "gate": spec.get("gate", "")})

    (outdir / "fixtures.json").write_text(json.dumps(built, indent=2) + "\n")
    return built


def _node():
    cands = sorted(pathlib.Path.home().glob(".nvm/versions/node/*/bin/node"))
    return str(cands[-1]) if cands else (shutil.which("node") or "node")


def _gates_text():
    from_base = (ROOT / "gates" / "base.md").read_text().splitlines()
    return "\n".join(l.strip() for l in from_base if l.strip() and l.strip()[0].isdigit())


def review(png, model):
    """Ask one tier to review one fixture. Returns dict or None if the call failed."""
    prompt = CRITIC_PROMPT.format(png=png, gates=_gates_text())
    # The reviewer has to open the PNG, so Read must be allowed explicitly:
    # a nested `claude -p` defaults to asking, and there is nobody to ask.
    # CLAUDECODE must be unset or the child refuses to start inside a session.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        out = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--allowedTools", "Read"],
            capture_output=True, text=True, timeout=300, env=env,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"error": str(e)}
    text = (out.stdout or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        return {"error": f"no JSON in response: {text[:120]}"}
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        return {"error": f"bad JSON: {e}"}


def run(tiers, fixtures_dir, apply_result, voters=3):
    fx_path = pathlib.Path(fixtures_dir) / "fixtures.json"
    fixtures = json.loads(fx_path.read_text()) if fx_path.is_file() else build_fixtures(fixtures_dir)

    results = {}
    for tier in tiers:
        caught = missed = false_pos = errors = 0
        detail = []
        for f in fixtures:
            # Calibrate against the decision rule the PROTOCOL actually uses:
            # a majority of N critics, not one binary verdict. A single call is a
            # harsher test than the loop applies, so it measures the wrong thing
            # and rejects tiers the real protocol would handle fine.
            votes, errs = [], []
            for _ in range(voters):
                r = review(f["png"], tier)
                (errs if r.get("error") else votes).append(r)
            if not votes:
                errors += 1
                detail.append({"fixture": f["name"], "error": errs[0]["error"] if errs else "no votes"})
                continue
            yes = sum(1 for v in votes if v.get("defectFound"))
            found = yes * 2 > len(votes)
            if f["expect"] == "defect":
                caught += found
                missed += (not found)
            else:
                false_pos += found
            detail.append({"fixture": f["name"], "expect": f["expect"], "defectFound": found,
                           "votes": f"{yes}/{len(votes)}",
                           "gates": [v.get("gate", "") for v in votes if v.get("defectFound")]})
        n_def = sum(1 for f in fixtures if f["expect"] == "defect")
        n_clean = len(fixtures) - n_def
        results[tier] = {
            "caught": caught, "ofDefects": n_def, "missed": missed,
            "falsePositives": false_pos, "ofClean": n_clean, "errors": errors,
            "qualifies": errors == 0 and missed == 0 and false_pos == 0,
            "detail": detail,
        }
        print(f"{tier}: caught {caught}/{n_def}, false positives {false_pos}/{n_clean}, "
              f"errors {errors} -> {'QUALIFIES' if results[tier]['qualifies'] else 'no'}")

    winner = next((t for t in tiers if results[t]["qualifies"]), None)
    out = pathlib.Path(fixtures_dir) / "calibration.json"
    out.write_text(json.dumps({"tiersTested": tiers, "winner": winner, "results": results}, indent=2) + "\n")
    print(f"\nwrote {out}")

    if not winner:
        print("No tier qualified. Keep the current critic and re-run after adjusting fixtures or tiers.")
        return 1
    print(f"Cheapest qualifying tier: {winner}")

    if apply_result:
        import datetime
        alias = _alias_for(winner)
        if not alias:
            print(f"Cannot derive a Workflow alias from {winner!r}; NOT applying. "
                  "Pin it by hand in pipeline.json — both models.critic.model AND .alias.")
            return 1
        pj = ROOT / "pipeline.json"
        cfg = json.loads(pj.read_text())
        cfg["models"]["critic"]["model"] = winner
        # The alias is what actually routes (taste-loop.js reads `.alias`); the
        # first --apply wrote only `model` and silently pinned nothing.
        cfg["models"]["critic"]["alias"] = alias
        when = datetime.date.today().isoformat()
        cfg["calibration"]["calibratedAt"] = when
        cfg["calibration"]["measuredAgainst"] = tiers
        # Replace the note, never just delete it: the pin keeps its provenance.
        cfg["calibration"]["note"] = (
            f"Pinned {winner} (alias {alias}) on {when}: cheapest tier that caught "
            "every seeded defect with zero false positives on the clean controls."
        )
        pj.write_text(json.dumps(cfg, indent=2) + "\n")
        print(f"pinned critic -> {winner} (alias {alias}) in pipeline.json")
    else:
        print("(re-run with --apply to pin it)")
    return 0


def _demo():
    assert sum(1 for s in DEFECTS.values() if s["expect"] == "clean") >= 2, "need clean controls"
    assert sum(1 for s in DEFECTS.values() if s["expect"] == "defect") >= 4, "need enough defects"
    gates = _gates_text()
    assert gates.count("\n") >= 5, "base gates did not load"
    # A tier only qualifies on a perfect two-sided result: catching everything while
    # flagging a clean control is not strictness, it is noise.
    for missed, fp, err, want in ((0, 0, 0, True), (1, 0, 0, False), (0, 1, 0, False), (0, 0, 1, False)):
        assert (err == 0 and missed == 0 and fp == 0) is want
    assert "Do not invent problems" in CRITIC_PROMPT, "prompt must guard against false positives"
    # The pin must write the field the loop actually reads: the alias.
    assert _alias_for("claude-haiku-4-5-20251001") == "haiku"
    assert _alias_for("claude-sonnet-5") == "sonnet"
    assert _alias_for("gpt-5.5") is None, "an unknown family must refuse to pin, not guess"
    # Defaults come from pipeline.json, cheapest first — never a baked-in string.
    pl = _pipeline()
    by_cost = _tiers_by_cost(pl)
    assert by_cost[0] == "claude-haiku-4-5-20251001", by_cost
    assert all(_alias_for(m) for m in by_cost), "every priced tier must map to an alias"
    assert isinstance(pl["loop"]["critics"], int) and pl["loop"]["critics"] >= 1
    print("calibrate OK")
    print(f"  {len(DEFECTS)} fixtures: "
          f"{sum(1 for s in DEFECTS.values() if s['expect']=='defect')} seeded defects, "
          f"{sum(1 for s in DEFECTS.values() if s['expect']=='clean')} clean controls")
    print("  next: python3 calibrate.py fixtures  then  python3 calibrate.py run --apply")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fixtures"); f.add_argument("--outdir", default="/tmp/lv-calibration")
    r = sub.add_parser("run")
    r.add_argument("--tiers", default=None,
                   help="comma-separated model ids; default: pipeline.json pricing tiers, cheapest first")
    r.add_argument("--fixtures", default="/tmp/lv-calibration")
    r.add_argument("--apply", action="store_true")
    r.add_argument("--voters", type=int, default=None,
                   help="critics per fixture; default: pipeline.json loop.critics")
    a = ap.parse_args()

    if a.cmd == "fixtures":
        built = build_fixtures(a.outdir)
        print(f"built {len(built)} fixtures in {a.outdir}")
        for b in built:
            print(f"  {b['name']:22} {b['expect']:7} {b['gate']}")
    elif a.cmd == "run":
        # pipeline.json is the only file that names a model; defaults come from
        # it, never from a string baked in here.
        pl = _pipeline()
        tiers = ([t.strip() for t in a.tiers.split(",") if t.strip()] if a.tiers
                 else _tiers_by_cost(pl))
        voters = a.voters if a.voters is not None else pl["loop"]["critics"]
        sys.exit(run(tiers, a.fixtures, a.apply, voters))
    else:
        _demo()


if __name__ == "__main__":
    main()
