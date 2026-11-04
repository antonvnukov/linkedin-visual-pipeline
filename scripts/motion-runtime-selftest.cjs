#!/usr/bin/env node
// Two-sided self-check for motion-runtime.js's per-card bezier ease (data-ease).
// Run: node scripts/motion-runtime-selftest.cjs   (also in CI, deterministic step)
//
// Why it exists: GSAP core silently ignores "cubic-bezier(...)" strings, so a
// "measured" curve can quietly become the default ease with no error. The runtime
// solves the bezier itself; this proves the solver matches an INDEPENDENT reference
// (dense sampling of the parametric curve) and that the comparison can fail.
const fs = require("fs"), path = require("path"), vm = require("vm");
const src = fs.readFileSync(path.join(__dirname, "motion-runtime.js"), "utf8");
const sandbox = { window: {}, document: { querySelector: () => null, querySelectorAll: () => [] }, Math };
vm.createContext(sandbox);
vm.runInContext(src, sandbox);
const bezierEase = sandbox.window.__bezierEase;
if (typeof bezierEase !== "function") { console.error("FAIL: window.__bezierEase not exposed"); process.exit(1); }

// Independent reference: sample the parametric curve densely, then interpolate y at x.
function reference(x1, y1, x2, y2) {
  const N = 20000, xs = [], ys = [];
  for (let i = 0; i <= N; i++) {
    const t = i / N, u = 1 - t;
    xs.push(3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t);
    ys.push(3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t);
  }
  return (x) => {
    let lo = 0, hi = N;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] < x) lo = m; else hi = m; }
    const f = (x - xs[lo]) / ((xs[hi] - xs[lo]) || 1);
    return ys[lo] + f * (ys[hi] - ys[lo]);
  };
}
function maxErr(fn, ref) {
  let e = 0;
  for (let i = 0; i <= 100; i++) { const x = i / 100; e = Math.max(e, Math.abs(fn(x) - ref(x))); }
  return e;
}

const fails = [];
const curves = [[0.2, 0.8, 0.2, 1], [0.16, 0.8, 0.2, 1], [0.2, 0.8, 0.3, 1], [0.2, 0, 0, 1], [0, 0, 1, 1]];
for (const c of curves) {
  const e = maxErr(bezierEase(...c), reference(...c));
  if (e > 2e-3) fails.push(`clean: cubic-bezier(${c}) max error ${e.toFixed(5)} > 0.002`);
}
// The measured aimindset curve must NOT be linear (a silent fallback would be).
const aim = bezierEase(0.2, 0.8, 0.2, 1);
if (Math.abs(aim(0.5) - 0.5) < 0.1) fails.push("clean: aimindset curve at 0.5 is ~linear, solver not applied");
// Seeded violation: a wrong curve (control points swapped) must be CAUGHT by the same comparator.
const wrong = maxErr(bezierEase(0.8, 0.2, 1, 0.2), reference(0.2, 0.8, 0.2, 1));
if (wrong < 0.05) fails.push(`seeded: swapped-control-point curve passed the comparator (err ${wrong.toFixed(4)})`);
// Endpoints.
if (aim(0) !== 0 || aim(1) !== 1) fails.push("clean: endpoints must be exactly 0 and 1");

if (fails.length) { console.error("FAIL motion-runtime self-test:\n  - " + fails.join("\n  - ")); process.exit(1); }
console.log(`PASS motion-runtime self-test (${curves.length} curves vs reference, 1 seeded wrong curve caught, aim(0.5)=${aim(0.5).toFixed(3)})`);
