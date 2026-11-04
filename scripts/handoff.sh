#!/usr/bin/env bash
# handoff.sh — hand a GATED card to a design tool so it stays editable.
#
#   bash scripts/handoff.sh paper <card.html> [outdir]
#   bash scripts/handoff.sh figma <card.html> [outdir]
#
# A rendered PNG is final. Sometimes you want to keep tuning by hand, which means
# getting the card into Paper (paper.design) or Figma as real editable layers.
#
# THE RULE: only ever hand off output that has already passed the gate. Building a
# card freehand inside Paper or Figma skips the palette check, the claims ledger
# and the taste loop entirely, which is the whole point of having them.
#
# Both targets need an MCP server the plugin cannot install for you, so this script
# prepares everything and prints the exact remaining steps rather than pretending
# to push. Check connectivity with `claude mcp list`.
set -euo pipefail

TARGET="${1:?usage: handoff.sh <paper|figma> <card.html> [outdir]}"
HTML="${2:?path to a gated card HTML required}"
OUTDIR="${3:-$(dirname "$HTML")/handoff}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$OUTDIR"

[ -f "$HTML" ] || { echo "no such file: $HTML" >&2; exit 1; }

# Refuse to hand off something that never passed the gate.
if ! grep -q "data-s\|slide-1" "$HTML" 2>/dev/null; then
  echo "warning: $HTML does not look like pipeline output." >&2
  echo "Hand off gated pipeline output only, never a hand-authored file." >&2
fi

NODE="$(ls -d "$HOME"/.nvm/versions/node/*/bin/node 2>/dev/null | tail -1 || command -v node || true)"

case "$TARGET" in
paper)
  echo "Preparing a Paper (paper.design) handoff"
  echo

  # SVG-as-image-fill does not render in Paper, so any vector mark has to be a
  # rasterized transparent PNG. Playwright, not qlmanage: QuickLook forces a white
  # background, which makes a white wordmark invisible.
  if [ -n "$NODE" ]; then
    cat > "$OUTDIR/rasterize.js" <<'JS'
// Rasterize an SVG to a transparent PNG for Paper. qlmanage forces a white
// background, which silently destroys white-on-dark marks.
const path = require('path');
const { chromium } = require(path.join(__dirname, '..', '..', 'node_modules', 'playwright'));
(async () => {
  const [svg, out] = process.argv.slice(2);
  if (!svg) { console.log('usage: node rasterize.js <in.svg> <out.png>'); process.exit(0); }
  const b = await chromium.launch();
  const p = await b.newPage({ deviceScaleFactor: 3 });
  await p.setContent(`<body style="margin:0">${require('fs').readFileSync(svg, 'utf8')}</body>`);
  await p.locator('svg').screenshot({ path: out, omitBackground: true });
  await b.close();
})();
JS
    echo "  wrote $OUTDIR/rasterize.js (for any SVG mark)"
  fi

  cp "$HTML" "$OUTDIR/source.html"
  echo "  wrote $OUTDIR/source.html"
  echo
  cat "$HERE/../docs/paper-adapter-rules.md" 2>/dev/null || true
  echo
  echo "Remaining steps (needs the Paper MCP server; check: claude mcp list):"
  echo "  1. Adapt $OUTDIR/source.html to Paper nodes following the rules above."
  echo "  2. Push with write_html into the EXISTING Paper file, not a new one per card."
  echo "  3. Tune by hand, then export back."
  ;;

figma)
  echo "Preparing a Figma handoff"
  echo
  cp "$HTML" "$OUTDIR/source.html"

  # The Figma html-to-design capture script must be in <head> before serving.
  if grep -q "mcp.figma.com/mcp/html-to-design/capture.js" "$OUTDIR/source.html"; then
    echo "  capture script already present"
  else
    python3 - "$OUTDIR/source.html" <<'PY'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
tag = '<script src="https://mcp.figma.com/mcp/html-to-design/capture.js" async></script>'
s = re.sub(r"</head>", f"  {tag}\n</head>", s, count=1) if "</head>" in s else tag + s
p.write_text(s)
print("  injected the Figma capture script into <head>")
PY
  fi

  cat > "$OUTDIR/serve.sh" <<'SH'
#!/usr/bin/env bash
# Figma's capture script needs the page served over HTTP, not file://.
cd "$(dirname "$0")" && exec python3 -m http.server "${1:-8321}"
SH
  chmod +x "$OUTDIR/serve.sh"
  echo "  wrote $OUTDIR/serve.sh"
  echo
  echo "Remaining steps (needs the Figma MCP server; check: claude mcp list):"
  echo "  1. bash $OUTDIR/serve.sh 8321"
  echo "  2. Verify it responds:  curl -sI http://localhost:8321/source.html | head -1"
  echo "  3. Run generate_figma_design against http://localhost:8321/source.html"
  echo "  4. For multi-slide decks, confirm slide navigation PRESERVES location.hash;"
  echo "     stripping it on navigation is the known capture-breaking bug."
  ;;

*)
  echo "unknown target: $TARGET (expected 'paper' or 'figma')" >&2
  exit 1
  ;;
esac

echo
echo "Reminder: hand off gated output only. Authoring inside the design tool bypasses"
echo "the palette check, the claims ledger and the taste loop."
