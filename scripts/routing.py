#!/usr/bin/env python3
"""
routing.py — the only place the pipeline learns which model runs a stage.

The design constraint: a rigorous protocol that is expensive gets skipped, and
rigor that does not run is not rigor. So most stages are deterministic code
(free, therefore always on) and the few that need judgment route to the
cheapest tier that provably does the job.

    from routing import route, log_usage, cost_report
    r = route("critic")          # -> {"stage","model","effort","calibrated"}

Nothing outside this module and pipeline.json may name a model.

Self-check:  python3 routing.py
Cost report: python3 routing.py --report-cost <usage.jsonl>
"""
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
STAGES = ("extract", "author", "critic", "fixer", "escalate")
EFFORTS = ("low", "medium", "high", "xhigh", "max")


def _candidates(explicit=None):
    if explicit:
        yield pathlib.Path(explicit).expanduser()
    if os.environ.get("LV_PIPELINE"):
        yield pathlib.Path(os.environ["LV_PIPELINE"]).expanduser()
    yield pathlib.Path.cwd() / "pipeline.json"
    yield ROOT / "pipeline.json"


def load(explicit=None):
    for p in _candidates(explicit):
        if p.is_file():
            cfg = json.loads(p.read_text())
            cfg.setdefault("_path", str(p))
            return cfg
    raise SystemExit("routing: no pipeline.json found next to the plugin or in cwd.")


def route(stage, cfg=None, escalate=False):
    """Resolve a stage to {model, effort}. `escalate` swaps in the expensive tier."""
    cfg = cfg or load()
    if stage not in STAGES:
        raise KeyError(f"routing: unknown stage {stage!r}; known: {', '.join(STAGES)}")
    key = "escalate" if escalate else stage
    spec = cfg["models"][key]
    effort = spec.get("effort", "medium")
    if effort not in EFFORTS:
        raise ValueError(f"routing: {key}.effort={effort!r} not one of {EFFORTS}")
    return {
        "stage": stage,
        "model": spec["model"],
        # Workflow agent() takes a short alias, not the full model id.
        "alias": spec.get("alias", "sonnet"),
        "effort": effort,
        # A critic tier nobody measured is a default, not a measurement. Callers
        # surface this so an uncalibrated run is never mistaken for a verified one.
        "calibrated": bool(cfg.get("calibration", {}).get("calibratedAt")),
    }


def loop_cfg(cfg=None):
    cfg = cfg or load()
    return cfg.get("loop", {})


# ------------------------------------------------------------------ accounting

def log_usage(path, stage, model, tokens_in, tokens_out):
    """Append one model call to a JSONL ledger. Cost is derived at report time."""
    rec = {"stage": stage, "model": model, "in": int(tokens_in), "out": int(tokens_out)}
    with open(path, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def cost_report(usage_path, cfg=None):
    """Sum a usage ledger into per-stage and total USD. Unknown models cost 0 and are named."""
    cfg = cfg or load()
    pricing = cfg.get("pricing", {})
    by_stage, unpriced, total = {}, set(), 0.0
    for line in pathlib.Path(usage_path).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        p = pricing.get(r["model"])
        if not p:
            unpriced.add(r["model"])
            usd = 0.0
        else:
            usd = r["in"] / 1e6 * p["in"] + r["out"] / 1e6 * p["out"]
        s = by_stage.setdefault(r["stage"], {"calls": 0, "in": 0, "out": 0, "usd": 0.0})
        s["calls"] += 1
        s["in"] += r["in"]
        s["out"] += r["out"]
        s["usd"] += usd
        total += usd
    return {"byStage": by_stage, "totalUSD": round(total, 4), "unpricedModels": sorted(unpriced)}


def format_report(rep):
    lines = [f"{'stage':10} {'calls':>5} {'in':>9} {'out':>8} {'USD':>8}", "-" * 44]
    for stage, s in sorted(rep["byStage"].items(), key=lambda kv: -kv[1]["usd"]):
        lines.append(f"{stage:10} {s['calls']:5} {s['in']:9} {s['out']:8} {s['usd']:8.4f}")
    lines.append("-" * 44)
    lines.append(f"{'TOTAL':10} {'':5} {'':9} {'':8} {rep['totalUSD']:8.4f}")
    if rep["unpricedModels"]:
        lines.append(f"WARNING unpriced (counted as $0): {', '.join(rep['unpricedModels'])}")
    return "\n".join(lines)


def _demo():
    cfg = load()
    for stage in STAGES:
        r = route(stage, cfg)
        assert r["model"] and r["effort"] in EFFORTS, stage
        assert r["alias"], f"{stage} has no agent() alias"
    assert route("critic", cfg, escalate=True)["model"] == cfg["models"]["escalate"]["model"]
    try:
        route("nope", cfg)
        raise AssertionError("unknown stage must raise")
    except KeyError:
        pass

    # accounting round-trip, including the unpriced-model path
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        tmp = fh.name
    log_usage(tmp, "critic", "claude-sonnet-5", 100_000, 2_000)
    log_usage(tmp, "critic", "claude-sonnet-5", 100_000, 2_000)
    log_usage(tmp, "fixer", "made-up-model", 10_000, 1_000)
    rep = cost_report(tmp, cfg)
    assert rep["byStage"]["critic"]["calls"] == 2
    expect = 2 * (100_000 / 1e6 * 3.0 + 2_000 / 1e6 * 15.0)
    assert abs(rep["byStage"]["critic"]["usd"] - expect) < 1e-9, rep
    assert rep["unpricedModels"] == ["made-up-model"], "unpriced model must be surfaced, not hidden"
    os.unlink(tmp)

    print(f"routing OK  <- {cfg['_path']}")
    for stage in STAGES:
        r = route(stage, cfg)
        print(f"  {stage:9} {r['model']:28} effort={r['effort']}")
    cal = cfg.get("calibration", {}).get("calibratedAt")
    print(f"  calibrated: {cal or 'NO — critic tier is an untested default (run scripts/calibrate.py)'}")


if __name__ == "__main__":
    import sys
    if "--report-cost" in sys.argv:
        print(format_report(cost_report(sys.argv[sys.argv.index("--report-cost") + 1])))
    else:
        _demo()
