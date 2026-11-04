#!/usr/bin/env node
/**
 * qa-visual.cjs — the deterministic pre-ship gate.
 *
 *   node qa-visual.cjs --html <built.html> --theme <light|dark> --outdir <new-dir>
 *                      [--manifest <qa.json>] [--claims <claims.json>]
 *                      [--brand <brand.json>] [--force]
 *   node qa-visual.cjs --self-test
 *
 * This is where most of the pipeline's rigor lives, and it is all code, so it
 * costs nothing to run and can therefore run on every artifact forever. A gate
 * that is expensive is a gate that gets skipped.
 *
 * Checks: artboard dimensions, images loaded, the COMPUTED font (per weight),
 * forbidden fonts per element, required/forbidden text, occurrence counts,
 * selector counts, allowed/forbidden colours, text escaping the artboard,
 * ancestor clipping, and geometry assertions. Emits a review bundle
 * (native-2x / final / feed-preview / critical crops / qa-report.json) into an
 * immutable candidate directory, checksummed.
 *
 * Palette and font default to brand.json, so a manifest only has to describe
 * what is specific to THIS artifact.
 */
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { pathToFileURL } = require("url");

const HERE = __dirname;

function loadPlaywright() {
  try {
    return require(path.join(HERE, "..", "node_modules", "playwright"));
  } catch (_) {
    try {
      return require("playwright");
    } catch (__) {
      console.error("Playwright not found. Run: bash scripts/setup.sh");
      process.exit(1);
    }
  }
}

function parseArgs(argv) {
  const parsed = { force: false, selfTest: false };
  const flags = ["--html", "--manifest", "--claims", "--outdir", "--brand", "--theme"];
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--force") { parsed.force = true; continue; }
    if (argv[i] === "--self-test") { parsed.selfTest = true; continue; }
    if (flags.includes(argv[i])) { parsed[argv[i].slice(2)] = argv[i + 1]; i += 1; continue; }
    throw new Error(`Unknown argument: ${argv[i]}`);
  }
  if (parsed.selfTest) return parsed;
  if (!parsed.html || !parsed.outdir) {
    throw new Error("Usage: qa-visual.cjs --html <built.html> --theme <light|dark> --outdir <dir> [--manifest f] [--claims f] [--brand f] [--force]");
  }
  return parsed;
}

/** An immutable candidate dir: a QA run must never silently overwrite a reviewed one. */
function prepareOutdir(outdir, force) {
  if (fs.existsSync(outdir) && fs.readdirSync(outdir).length > 0 && !force) {
    throw new Error(`Candidate directory is not empty (use --force to overwrite): ${outdir}`);
  }
  fs.mkdirSync(outdir, { recursive: true });
}

const sha256 = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");

function brandkit(args, brandPath) {
  const argv = [path.join(HERE, "brandkit.py")];
  if (brandPath) argv.push("--brand", brandPath);
  return execFileSync("python3", argv.concat(args), { encoding: "utf8" }).trim();
}

/** Manifest defaults pulled from the brand, so a manifest stays artifact-specific. */
function withBrandDefaults(manifest, theme, brandPath) {
  const m = { ...manifest };
  if (!m.allowedHexColors) {
    m.allowedHexColors = brandkit(["--palette", theme || "dark"], brandPath).split(/\s+/).filter(Boolean);
  }
  if (!m.fontFamily) m.fontFamily = brandkit(["--get", "font.family"], brandPath);
  // A brand may declare a second face (a monospace companion for template/code
  // cards). Every text node must still render in a DECLARED family: widening this
  // to the declared set keeps the check strict, where exempting the element that
  // uses mono would have blinded it to real drift on that element forever.
  if (!m.fontFamilies) {
    const monoFam = brandkit(["--get", "font.mono"], brandPath);
    m.fontFamilies = [m.fontFamily, monoFam].filter(Boolean);
  }
  if (!m.fontWeights) {
    const w = brandkit(["--get", "font.weights"], brandPath);
    m.fontWeights = w ? w.split(";").map(Number).filter(Boolean) : [400, 700];
  }
  return m;
}

async function runQa({ htmlPath, manifest, claims, outdir, theme }) {
  const expectedWidth = manifest.expectedWidth || 1080;
  const expectedHeight = manifest.expectedHeight || 1080;
  const feedWidth = manifest.feedWidth || 504;
  const feedHeight = Math.round((expectedHeight * feedWidth) / expectedWidth);
  const selector = manifest.artboardSelector || "#slide-1";

  // The claims ledger's occurrence caps ARE manifest counts. Merging them here
  // means a claim cap is enforced by the same arithmetic, not by good intentions.
  const ledgerCounts = {};
  for (const claim of claims?.claims || []) {
    for (const [value, count] of Object.entries(claim.allowedProminentOccurrences || {})) {
      if (Object.prototype.hasOwnProperty.call(ledgerCounts, value) && ledgerCounts[value] !== count) {
        throw new Error(`Conflicting claim-ledger occurrence counts for ${value}`);
      }
      ledgerCounts[value] = count;
    }
  }
  manifest.textOccurrenceCounts = { ...ledgerCounts, ...(manifest.textOccurrenceCounts || {}) };
  // These are read inside page.evaluate, so they must live ON the manifest,
  // not just in local scope, or the comparison is against undefined.
  manifest.expectedWidth = expectedWidth;
  manifest.expectedHeight = expectedHeight;

  const nativePath = path.join(outdir, "native-2x.png");
  const finalPath = path.join(outdir, "final.png");
  const feedPath = path.join(outdir, "feed-preview.png");
  const reportPath = path.join(outdir, "qa-report.json");

  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const runtimeErrors = [];

  const shoot = async (scale, outPath) => {
    const page = await browser.newPage({
      viewport: { width: expectedWidth, height: expectedHeight },
      deviceScaleFactor: scale,
    });
    page.on("console", (m) => { if (m.type() === "error") runtimeErrors.push(`console: ${m.text()}`); });
    page.on("pageerror", (e) => runtimeErrors.push(`page: ${e.message}`));
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    await page.locator(selector).screenshot({ path: outPath });
    return page;
  };

  // 2x native is the review master; final and feed are rescaled by re-rendering,
  // which keeps type crisp and avoids a macOS-only `sips` dependency.
  const page = await shoot(2, nativePath);

  const audit = await page.evaluate(({ manifest, selector }) => {
    const artboard = document.querySelector(selector);
    if (!artboard) throw new Error(`Missing artboard: ${selector}`);

    const artRect = artboard.getBoundingClientRect();
    const text = artboard.innerText;
    const checks = [];
    const add = (name, pass, details = {}) => checks.push({ name, pass, ...details });
    const roundRect = (r) => ({
      left: Math.round(r.left * 100) / 100, top: Math.round(r.top * 100) / 100,
      right: Math.round(r.right * 100) / 100, bottom: Math.round(r.bottom * 100) / 100,
      width: Math.round(r.width * 100) / 100, height: Math.round(r.height * 100) / 100,
    });
    const literalCount = (hay, needle) => hay.split(needle).length - 1;

    add("artboard-dimensions",
      Math.round(artRect.width) === manifest.expectedWidth && Math.round(artRect.height) === manifest.expectedHeight,
      { actual: { width: Math.round(artRect.width), height: Math.round(artRect.height) },
        expected: { width: manifest.expectedWidth, height: manifest.expectedHeight } });

    const missingImages = Array.from(artboard.querySelectorAll("img"))
      .filter((im) => !im.complete || im.naturalWidth === 0)
      .map((im) => (im.getAttribute("src") || "").slice(0, 120));
    add("images-loaded", missingImages.length === 0, { missingImages });

    // The check that would have caught the brand-font leak: assert the COMPUTED
    // family, not merely that a stylesheet mentions it.
    const fontFamily = manifest.fontFamily;
    // Only assert the weights the card ACTUALLY renders. A browser fetches a
    // webfont weight lazily, so a declared-but-unused weight always reports
    // unloaded and would fail every healthy card.
    // Weights that actually render glyphs: the parent of a non-empty TEXT NODE.
    // `el.textContent` includes descendants, so wrapper elements would otherwise
    // count as "using" a weight they never draw, and that weight is never fetched.
    // Weight AND family together. Checking every used weight against the primary
    // family alone reported a false failure the moment a brand gained a second
    // face: the mono body renders at 400, no element renders the SANS at 400, so
    // the browser never loads that face and check() correctly says "not loaded"
    // for a weight nothing actually needs. Assert the pairs that really render.
    const declared = manifest.fontFamilies || [fontFamily];
    const weightWalker = document.createTreeWalker(artboard, NodeFilter.SHOW_TEXT);
    const usedPairs = new Map();
    while (weightWalker.nextNode()) {
      const n = weightWalker.currentNode;
      if (!(n.nodeValue && n.nodeValue.trim() && n.parentElement)) continue;
      const cs = getComputedStyle(n.parentElement);
      const fam = declared.find((f) => cs.fontFamily.includes(f)) || fontFamily;
      usedPairs.set(`${cs.fontWeight}|${fam}`, { weight: cs.fontWeight, family: fam });
    }
    const fontChecks = Array.from(usedPairs.values())
      .sort((a, b) => (a.family + a.weight).localeCompare(b.family + b.weight))
      .map(({ weight, family }) => ({
        weight, family,
        loaded: document.fonts ? document.fonts.check(`${weight} 16px "${family}"`) : false,
      }));
    const weightsInUse = fontChecks.map((c) => `${c.family} ${c.weight}`);
    const fontLoaded = fontChecks.every((c) => c.loaded);
    const computedFont = getComputedStyle(artboard).fontFamily;

    // The root alone is not enough. A child override (`.head{font-family:Georgia}`)
    // leaves the artboard computing the brand face while the headline renders in
    // something else - which is exactly the leak this check is named after, and it
    // passed until 2026-08. Assert every element that actually draws glyphs.
    const offenders = [];
    const famWalker = document.createTreeWalker(artboard, NodeFilter.SHOW_TEXT);
    while (famWalker.nextNode()) {
      const n = famWalker.currentNode;
      if (!n.nodeValue || !n.nodeValue.trim() || !n.parentElement) continue;
      const fam = getComputedStyle(n.parentElement).fontFamily;
      if (!(manifest.fontFamilies || [fontFamily]).some((f) => fam.includes(f))) {
        offenders.push({
          text: n.nodeValue.trim().replace(/\s+/g, " ").slice(0, 40),
          element: n.parentElement.className || n.parentElement.tagName,
          fontFamily: fam,
        });
      }
    }
    add("font-loaded", fontLoaded && computedFont.includes(fontFamily) && offenders.length === 0,
      { fontFamily, weightsInUse, fontChecks, computedFont, fontLoaded, offenders: offenders.slice(0, 10) });

    for (const bad of manifest.forbiddenFontFamilies || []) {
      const offenders = [artboard, ...Array.from(artboard.querySelectorAll("*"))]
        .filter((el) => getComputedStyle(el).fontFamily.includes(bad))
        .slice(0, 20)
        .map((el) => ({ tag: el.tagName, className: el.className || "", fontFamily: getComputedStyle(el).fontFamily }));
      add(`forbidden-font:${bad}`, offenders.length === 0, { forbiddenFont: bad, offenders });
    }

    if (manifest.minFontPx) {
      // Legibility floor: any rendered text smaller than the floor fails (opt-in per manifest).
      const small = new Map();
      const walker = document.createTreeWalker(artboard, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        if (!n.textContent.trim() || !n.parentElement) continue;
        const px = parseFloat(getComputedStyle(n.parentElement).fontSize);
        if (px < manifest.minFontPx) small.set(n.textContent.trim().slice(0, 40), px);
      }
      add("min-font-px", small.size === 0, { floor: manifest.minFontPx, offenders: Array.from(small).slice(0, 10) });
    }

    for (const req of manifest.requiredText || []) add(`required-text:${req}`, text.includes(req), { required: req });
    for (const bad of manifest.forbiddenText || []) add(`forbidden-text:${bad}`, !text.includes(bad), { forbidden: bad });
    for (const [value, expected] of Object.entries(manifest.textOccurrenceCounts || {})) {
      const actual = literalCount(text, value);
      add(`text-count:${value}`, actual === expected, { value, expected, actual });
    }
    for (const [sel, expected] of Object.entries(manifest.selectorCounts || {})) {
      const actual = artboard.querySelectorAll(sel).length;
      add(`selector-count:${sel}`, actual === expected, { selector: sel, expected, actual });
    }

    const cssText = Array.from(document.querySelectorAll("style")).map((s) => s.textContent).join("\n");
    const parseColor = (token) => {
      const v = token.trim();
      const hex = v.match(/^#([0-9a-fA-F]{6})$/);
      if (hex) return [0, 2, 4].map((i) => parseInt(hex[1].slice(i, i + 2), 16));
      const rgb = v.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
      return rgb ? [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])] : null;
    };

    if (manifest.allowedHexColors) {
      const used = Array.from(new Set((cssText.match(/#[0-9a-fA-F]{6}\b/g) || []).map((c) => c.toUpperCase()))).sort();
      const allowed = manifest.allowedHexColors.map((c) => c.toUpperCase());
      const banned = used.filter((c) => !allowed.includes(c));
      add("allowed-hex-colors", banned.length === 0, { allowed: allowed.sort(), used, banned });
    }

    if (manifest.forbiddenColors) {
      const tokens = cssText.match(/#[0-9a-fA-F]{6}\b|rgba?\([^)]*\)/g) || [];
      const forbidden = manifest.forbiddenColors.map((v) => ({ value: v, rgb: parseColor(v) })).filter((e) => e.rgb);
      const offenders = tokens.filter((t) => {
        const rgb = parseColor(t);
        return rgb && forbidden.some((e) => e.rgb.every((ch, i) => ch === rgb[i]));
      });
      add("forbidden-colors", offenders.length === 0, { forbidden: manifest.forbiddenColors, offenders });
    }

    const textNodes = [];
    const walker = document.createTreeWalker(artboard, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const n = walker.currentNode;
      if (n.nodeValue && n.nodeValue.trim()) textNodes.push(n);
    }

    const outsideArtboard = [];
    const clippedByAncestor = [];
    for (const node of textNodes) {
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of Array.from(range.getClientRects())) {
        if (rect.width === 0 || rect.height === 0) continue;
        const label = node.nodeValue.trim().replace(/\s+/g, " ").slice(0, 80);
        if (rect.left < artRect.left - 0.5 || rect.top < artRect.top - 0.5 ||
            rect.right > artRect.right + 0.5 || rect.bottom > artRect.bottom + 0.5) {
          outsideArtboard.push({ text: label, rect: roundRect(rect) });
        }
        let parent = node.parentElement;
        while (parent && parent !== artboard) {
          const st = getComputedStyle(parent);
          const clipsX = ["hidden", "clip", "auto", "scroll"].includes(st.overflowX);
          const clipsY = ["hidden", "clip", "auto", "scroll"].includes(st.overflowY);
          if (clipsX || clipsY) {
            const pr = parent.getBoundingClientRect();
            const clipped = (clipsX && (rect.left < pr.left - 0.5 || rect.right > pr.right + 0.5)) ||
                            (clipsY && (rect.top < pr.top - 0.5 || rect.bottom > pr.bottom + 0.5));
            if (clipped) {
              clippedByAncestor.push({ text: label, ancestor: parent.className || parent.tagName,
                textRect: roundRect(rect), ancestorRect: roundRect(pr) });
              break;
            }
          }
          parent = parent.parentElement;
        }
      }
    }
    add("text-inside-artboard", outsideArtboard.length === 0, { outsideArtboard });
    add("no-ancestor-clipping", clippedByAncestor.length === 0, { clippedByAncestor });

    const rectFor = (s) => { const el = document.querySelector(s); return el ? el.getBoundingClientRect() : null; };
    const rectsFor = (sels) => sels.flatMap((s) => Array.from(document.querySelectorAll(s)).map((el) => el.getBoundingClientRect()));

    for (const g of manifest.geometry || []) {
      if (g.type === "no-overlap") {
        const a = rectFor(g.a), b = rectFor(g.b);
        if (!a || !b) { add(`geometry:${g.name}`, false, { error: "selector not found" }); continue; }
        const oX = a.left < b.right && a.right > b.left;
        const oY = a.top < b.bottom && a.bottom > b.top;
        const minGap = g.minGap || 0;
        const gap = g.axis === "vertical" ? Math.max(b.top - a.bottom, a.top - b.bottom)
                                          : Math.max(b.left - a.right, a.left - b.right);
        add(`geometry:${g.name}`, !(oX && oY) && gap >= minGap,
          { gap: Math.round(gap * 100) / 100, minGap, a: roundRect(a), b: roundRect(b) });
      } else if (["equal-top", "equal-height"].includes(g.type)) {
        const rects = rectsFor(g.selectors || []);
        if (rects.length < 2) { add(`geometry:${g.name}`, false, { error: "fewer than two matches", matches: rects.length }); continue; }
        const vals = rects.map((r) => (g.type === "equal-top" ? r.top : r.height));
        const spread = Math.max(...vals) - Math.min(...vals);
        const tol = g.tolerance ?? 1;
        add(`geometry:${g.name}`, spread <= tol,
          { spread: Math.round(spread * 100) / 100, tolerance: tol, values: vals.map((v) => Math.round(v * 100) / 100) });
      } else if (g.type === "paired-top") {
        const aEls = Array.from(document.querySelectorAll(g.a));
        const bEls = Array.from(document.querySelectorAll(g.b));
        if (aEls.length === 0 || aEls.length !== bEls.length) {
          add(`geometry:${g.name}`, false, { error: "paired selectors have unequal counts", aCount: aEls.length, bCount: bEls.length });
          continue;
        }
        const deltas = aEls.map((el, i) => Math.abs(el.getBoundingClientRect().top - bEls[i].getBoundingClientRect().top));
        const tol = g.tolerance ?? 1;
        add(`geometry:${g.name}`, Math.max(...deltas) <= tol,
          { maxDelta: Math.round(Math.max(...deltas) * 100) / 100, tolerance: tol, deltas: deltas.map((d) => Math.round(d * 100) / 100) });
      } else if (g.type === "center-y") {
        const a = rectFor(g.a), b = rectFor(g.b);
        if (!a || !b) { add(`geometry:${g.name}`, false, { error: "selector not found" }); continue; }
        const delta = Math.abs((a.top + a.height / 2) - (b.top + b.height / 2));
        const tol = g.tolerance ?? 1;
        add(`geometry:${g.name}`, delta <= tol, { delta: Math.round(delta * 100) / 100, tolerance: tol, a: roundRect(a), b: roundRect(b) });
      } else {
        add(`geometry:${g.name}`, false, { error: `unsupported geometry type: ${g.type}` });
      }
    }

    return { artboard: roundRect(artRect), checks, visibleTextLength: text.length };
  }, { manifest, selector });

  const cropResults = [];
  for (const region of manifest.criticalRegions || []) {
    const loc = page.locator(region.selector).first();
    if ((await loc.count()) === 0) {
      cropResults.push({ name: region.name, selector: region.selector, pass: false, error: "selector not found" });
      continue;
    }
    const cropPath = path.join(outdir, `critical-${region.name}-2x.png`);
    await loc.screenshot({ path: cropPath });
    cropResults.push({ name: region.name, selector: region.selector, pass: true, path: cropPath });
  }
  await page.close();

  await (await shoot(1, finalPath)).close();
  await (await shoot(feedWidth / expectedWidth, feedPath)).close();
  await browser.close();

  const unsupportedClaims = claims?.unsupportedClaims || [];
  const failures = [
    ...unsupportedClaims.map((claim) => ({ name: "unsupported-claim", claim })),
    ...runtimeErrors.map((error) => ({ name: "runtime-error", error })),
    ...audit.checks.filter((c) => !c.pass),
    ...cropResults.filter((c) => !c.pass).map((c) => ({ name: `critical-region:${c.name}`, ...c })),
  ];

  return {
    pass: failures.length === 0,
    candidateSha256: sha256(finalPath),
    theme,
    claimLedger: {
      loaded: Boolean(claims),
      unsupportedClaims,
      enforcedOccurrenceCounts: manifest.textOccurrenceCounts || {},
    },
    outputs: { native2x: nativePath, final: finalPath, feedPreview: feedPath },
    dimensions: { final: { width: expectedWidth, height: expectedHeight }, feed: { width: feedWidth, height: feedHeight } },
    runtimeErrors,
    audit,
    criticalRegions: cropResults,
    failures,
  };
}

// ---------------------------------------------------------------- self-test
// Two-sided by house standard: prove it CATCHES a seeded defect and PASSES a
// known-clean control. A one-sided pass proves nothing about false negatives.
async function selfTest() {
  const os = require("os");
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "qa-selftest-"));
  const clean = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    #slide-1{width:400px;height:400px;background:#FFFFFF;color:#0C0C0C;font-family:Helvetica,sans-serif;padding:20px;overflow:hidden}
    .n{font-size:40px}
    .deco{width:10px;height:4px;background:#0C0C0C}
  </style></head><body><div id="slide-1"><div class="n">42%</div><div class="deco"></div><p>one claim only</p></div></body></html>`;

  const manifest = {
    artboardSelector: "#slide-1", expectedWidth: 400, expectedHeight: 400, feedWidth: 200,
    fontFamily: "Helvetica", fontWeights: [400],
    allowedHexColors: ["#FFFFFF", "#0C0C0C"],
    requiredText: ["42%"], textOccurrenceCounts: { "42%": 1 },
    // opt-in checks that had no committed fixture until 2026-08. The clean control
    // proves each PASSES; the seeded cases below prove each CATCHES its own defect.
    forbiddenFontFamilies: ["Comic Sans MS"],
    selectorCounts: { ".n": 1 },
    forbiddenColors: ["#FF0000"],
    geometry: [{ name: "headline-above-body", type: "no-overlap", a: ".n", b: "p", axis: "vertical" }],
  };

  const cases = [
    ["control-clean", clean, true],
    ["wrong-dimensions", clean.replace("width:400px;height:400px", "width:390px;height:400px"), false],
    ["off-palette-hex", clean.replace("#0C0C0C", "#FF00FF"), false],
    ["missing-image", clean.replace("<p>one", '<img src="does-not-exist.png"><p>one'), false],
    // The real avatar case: a broken data URI logs NO console error, so this
    // must be caught by images-loaded itself, not by runtime-error noise.
    ["broken-data-uri", clean.replace("<p>one", '<img src="data:image/png;base64,zzzz"><p>one'), false],
    ["duplicated-stat", clean.replace("one claim only", "42% again"), false],
    ["text-overflows", clean.replace(".n{font-size:40px}", ".n{font-size:40px;position:absolute;left:900px}"), false],
    ["required-text-missing", clean.replace("42%", "7%"), false],
    // The leak the whole project was built around: a CHILD element overriding the
    // brand face while the artboard root still computes it.
    ["font-leak-on-child", clean.replace(".n{font-size:40px}", '.n{font-size:40px;font-family:Georgia,serif}'), false],
    // The four opt-in checks below had no committed fixture. Each seed trips ONLY
    // its target check, so a regression in that check alone still fails the case.
    // forbidden-font on a TEXTLESS element (font-loaded's text walker can't see it).
    ["forbidden-font-hit", clean.replace(".deco{width:10px;height:4px;background:#0C0C0C}", ".deco{width:10px;height:4px;background:#0C0C0C;font-family:'Comic Sans MS',cursive}"), false],
    // second .n → count 2 ≠ 1; geometry's querySelector(.n) still hits the first.
    ["selector-count-off", clean.replace('<div class="n">42%</div>', '<div class="n">42%</div><span class="n"></span>'), false],
    // rgb() form is invisible to the allowed-HEX check but caught by forbidden-colors.
    ["forbidden-color-hit", clean.replace("color:#0C0C0C", "color:rgb(255,0,0)"), false],
    // pull the body up under the headline → the two overlap.
    ["geometry-overlap", clean.replace("<p>one claim only</p>", '<p style="margin-top:-30px">one claim only</p>'), false],
  ];

  let failed = 0;
  for (const [name, html, shouldPass] of cases) {
    const htmlPath = path.join(tmp, `${name}.html`);
    fs.writeFileSync(htmlPath, html);
    const outdir = path.join(tmp, `${name}-out`);
    let report;
    try {
      report = await runQa({ htmlPath, manifest: JSON.parse(JSON.stringify(manifest)), claims: null, outdir, theme: "light" });
    } catch (e) {
      report = { pass: false, failures: [{ name: "threw", error: e.message }] };
      if (process.env.QA_DEBUG) console.error("  THREW:", e.message);
    }
    const ok = report.pass === shouldPass;
    if (!ok) failed += 1;
    const detail = report.pass ? "" : `  [${report.failures.map((f) => f.name).slice(0, 3).join(", ")}]`;
    console.log(`  ${ok ? "ok  " : "FAIL"}  ${name.padEnd(22)} expected ${shouldPass ? "PASS" : "FAIL"}, got ${report.pass ? "PASS" : "FAIL"}${detail}`);
  }
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(failed === 0 ? "qa-visual self-test: OK (catches seeded defects, passes clean control)"
                           : `qa-visual self-test: ${failed} case(s) wrong`);
  process.exit(failed === 0 ? 0 : 1);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.selfTest) return selfTest();

  const htmlPath = path.resolve(args.html);
  const outdir = path.resolve(args.outdir);
  prepareOutdir(outdir, args.force);

  const rawManifest = args.manifest ? JSON.parse(fs.readFileSync(path.resolve(args.manifest), "utf8")) : {};
  const manifest = withBrandDefaults(rawManifest, args.theme, args.brand);
  const claims = args.claims ? JSON.parse(fs.readFileSync(path.resolve(args.claims), "utf8")) : null;

  const report = await runQa({ htmlPath, manifest, claims, outdir, theme: args.theme || "dark" });
  report.inputs = { html: htmlPath, manifest: args.manifest || null, claims: args.claims || null };
  fs.writeFileSync(path.join(outdir, "qa-report.json"), `${JSON.stringify(report, null, 2)}\n`);

  if (report.pass) {
    console.log(`QA PASS  ${report.audit.checks.length} checks  sha256=${report.candidateSha256.slice(0, 12)}`);
  } else {
    console.log(`QA FAIL  ${report.failures.length} failure(s):`);
    for (const f of report.failures) console.log(`  - ${f.name}`);
    console.log(`  full report: ${path.join(outdir, "qa-report.json")}`);
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
