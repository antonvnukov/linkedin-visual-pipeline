// Frame recorder: drives window.render(t) deterministically, one screenshot per frame.
// Usage: node record.js <html> <outdir> [durationMs=5500] [fps=24]
const path = require('path'), fs = require('fs'), os = require('os');
// Plugin-local only, then global. See capture.js for why no home-dir fallback.
const cands = [
  path.join(__dirname, '..', 'node_modules', 'playwright'),
];
let playwright;
for (const p of cands) { try { playwright = require(p); break; } catch (e) {} }
if (!playwright) {
  try { playwright = require('playwright'); } catch (e) {
    console.error('Playwright not found. Run: bash scripts/setup.sh');
    process.exit(1);
  }
}
const { chromium } = playwright;

const html = process.argv[2];
const outdir = process.argv[3];
const dur = +(process.argv[4] || 5500);
const fps = +(process.argv[5] || 24);

(async () => {
  if (!fs.existsSync(outdir)) fs.mkdirSync(outdir, { recursive: true });
  const b = await chromium.launch();
  const pg = await b.newPage({ deviceScaleFactor: 1 });
  await pg.goto('file://' + path.resolve(html), { waitUntil: 'networkidle' });
  // The card document carries the choreography, not the engine. Supplying GSAP
  // here (and via `import` in Card.tsx) keeps the vendored library out of the
  // HTML that gate.sh hex-greps. Must land before the first window.render call.
  const gsapPath = path.join(__dirname, '..', 'node_modules', 'gsap', 'dist', 'gsap.min.js');
  if (!fs.existsSync(gsapPath)) {
    console.error('GSAP not found at ' + gsapPath + '\nRun: (cd ' + path.join(__dirname, '..') + ' && npm install)');
    process.exit(1);
  }
  await pg.addScriptTag({ path: gsapPath });
  // Flip powers data-morph-to (one object changing shape). Vendored with GSAP.
  await pg.addScriptTag({ path: path.join(__dirname, '..', 'node_modules', 'gsap', 'dist', 'Flip.min.js') });
  await pg.waitForTimeout(2500); // Google Fonts
  const N = Math.round(dur / 1000 * fps);
  for (let i = 0; i <= N; i++) {
    await pg.evaluate((tt) => window.render(tt), i * (1000 / fps));
    const el = await pg.$('#slide-1');
    await el.screenshot({ path: path.join(outdir, 'f' + String(i).padStart(4, '0') + '.png') });
  }
  await b.close();
  console.log('frames captured:', N + 1);
})();
