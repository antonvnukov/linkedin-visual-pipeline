#!/usr/bin/env node

// Resolve playwright from known locations
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

// Plugin-local first (npm install at the repo root), then a global install.
// No machine-specific paths: a fallback into one developer's home directory is
// how a "clean clone works" test passes while every other machine fails.
const playwrightPaths = [
  path.join(__dirname, '..', 'node_modules', 'playwright'),
];
let playwright;
for (const p of playwrightPaths) {
  try { playwright = require(p); break; } catch (e) { /* next */ }
}
if (!playwright) {
  try { playwright = require('playwright'); } catch (e) {
    console.error('Playwright not found. Run: bash scripts/setup.sh');
    process.exit(1);
  }
}
const { chromium } = playwright;

// Parse CLI args
const args = process.argv.slice(2);
function getArg(name) {
  const idx = args.indexOf(`--${name}`);
  return idx !== -1 && args[idx + 1] ? args[idx + 1] : null;
}

const htmlPath = getArg('html');
const slideCount = parseInt(getArg('slides'), 10);
const outDir = getArg('outdir') || '/tmp/carousel-slides';
const scaleFactor = parseInt(getArg('scale'), 10) || 2;

if (!htmlPath || !slideCount) {
  console.error('Usage: node capture.js --html <path> --slides <count> [--outdir <dir>] [--scale 1|2]');
  process.exit(1);
}

(async () => {
  // Ensure output directory exists
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: scaleFactor });

  const fileUrl = htmlPath.startsWith('/') ? `file://${htmlPath}` : `file://${path.resolve(htmlPath)}`;
  await page.goto(fileUrl, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000); // wait for Google Fonts

  const pngPaths = [];

  for (let i = 1; i <= slideCount; i++) {
    const el = await page.$(`#slide-${i}`);
    if (el) {
      const pngPath = path.join(outDir, `slide-${i}.png`);
      await el.screenshot({ path: pngPath, type: 'png' });
      pngPaths.push(pngPath);
      console.log(`Captured slide ${i} → ${pngPath}`);
    } else {
      console.error(`WARNING: #slide-${i} not found`);
    }
  }

  await browser.close();

  // Verify dimensions of first slide
  if (pngPaths.length > 0) {
    try {
      const info = execSync(`sips -g pixelWidth -g pixelHeight "${pngPaths[0]}"`, { encoding: 'utf8' });
      console.log(`\nFirst slide dimensions:\n${info.trim()}`);
    } catch (e) {
      // sips not available (non-macOS), skip dimension check
    }
  }

  // Combine PNGs into PDF using Python + PIL
  if (pngPaths.length > 0) {
    const pdfPath = path.join(outDir, 'carousel.pdf');

    const pyScript = path.join(outDir, '_combine.py');
    fs.writeFileSync(pyScript, `
import sys, json
from PIL import Image

png_paths = json.loads(sys.argv[1])
pdf_path = sys.argv[2]

images = []
for p in png_paths:
    img = Image.open(p).convert('RGB')
    images.append(img)

if images:
    images[0].save(
        pdf_path,
        save_all=True,
        append_images=images[1:],
        resolution=144.0
    )
    print(f"PDF saved: {pdf_path} ({len(images)} pages)")
`);

    try {
      execSync(
        `python3 "${pyScript}" '${JSON.stringify(pngPaths)}' "${pdfPath}"`,
        { stdio: 'inherit' }
      );
      fs.unlinkSync(pyScript);
    } catch (e) {
      // The PDF IS the carousel's deliverable. Swallowing this let render.sh print
      // "-> <base>.pdf (N slides)" for a PDF that did not exist, and CI (no Pillow)
      // passed every carousel that way (2026-09-22). Fail loud instead.
      console.error('PDF generation failed:', e.message);
      console.error('PNGs are still available in:', outDir);
      process.exit(1);
    }
  }

  console.log(`\nDone. Output: ${outDir}`);
})();
