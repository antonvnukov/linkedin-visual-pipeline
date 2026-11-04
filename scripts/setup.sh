#!/usr/bin/env bash
# setup.sh — get a fresh clone from zero to a rendered card.
#
#   bash scripts/setup.sh            install everything, then PROVE it works
#   bash scripts/setup.sh --check    report what is missing, change nothing
#
# The proof at the end is deliberate. An installer that reports success from
# exit codes is how "it works on my machine" happens: the earlier version of
# this repo passed a clean-clone test only because Playwright happened to be
# resolvable from another project on that one machine.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

ok=0; warn=0; bad=0
say_ok()   { printf '  \033[32mok\033[0m    %s\n' "$1"; ok=$((ok+1)); }
say_warn() { printf '  \033[33mwarn\033[0m  %s\n' "$1"; warn=$((warn+1)); }
say_bad()  { printf '  \033[31mMISSING\033[0m %s\n     fix: %s\n' "$1" "$2"; bad=$((bad+1)); }

# nvm exports `node`/`npm` as lazy-loading shell FUNCTIONS that recurse forever in
# a non-interactive shell, so resolve the real binaries by path.
NODE="$(ls -d "$HOME"/.nvm/versions/node/*/bin/node 2>/dev/null | tail -1)"
[ -z "$NODE" ] && NODE="$(command -v node 2>/dev/null)"
NODE_DIR=""; [ -n "$NODE" ] && NODE_DIR="$(dirname "$NODE")"
NPM="${NODE_DIR:+$NODE_DIR/npm}"; NPX="${NODE_DIR:+$NODE_DIR/npx}"

echo "linkedin-visuals setup  ($ROOT)"
echo

# ---------------------------------------------------------------- prerequisites
echo "Prerequisites"

if command -v python3 >/dev/null; then
  PYV="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
  if python3 -c 'import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)'; then
    say_ok "python3 $PYV"
  else
    say_bad "python3 $PYV is too old (need 3.8+)" "install a newer python3"
  fi
else
  say_bad "python3 not found" "install python 3.8 or newer"
fi

if [ -n "$NODE" ]; then
  NV="$("$NODE" -v)"
  MAJOR="$(echo "$NV" | sed 's/^v\([0-9]*\).*/\1/')"
  if [ "$MAJOR" -ge 18 ] 2>/dev/null; then say_ok "node $NV"
  else say_bad "node $NV is too old (need 18+)" "install node 18 or newer"; fi
else
  say_bad "node not found" "install node 18+ (needed for Playwright capture)"
fi

if command -v ffmpeg >/dev/null; then
  say_ok "ffmpeg ($(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f3))"
else
  say_warn "ffmpeg not found — still images work, MP4 and GIF do not (brew install ffmpeg)"
fi

# ---------------------------------------------------------------- installs
echo
echo "Plugin dependencies"

PW_LOCAL="$ROOT/node_modules/playwright"
if [ -d "$PW_LOCAL" ]; then
  say_ok "playwright installed in the plugin"
elif [ "$CHECK_ONLY" = 1 ]; then
  say_bad "playwright not installed" "bash scripts/setup.sh"
elif [ -n "$NPM" ]; then
  echo "  installing playwright..."
  (cd "$ROOT" && "$NPM" install --no-audit --no-fund >/dev/null 2>&1)
  [ -d "$PW_LOCAL" ] && say_ok "playwright installed" || say_bad "playwright install failed" "cd $ROOT && npm install"
else
  say_bad "playwright not installed and npm is unavailable" "install node, then bash scripts/setup.sh"
fi

# A Playwright package with no browser binary is the single most common failure:
# every render dies with "Executable doesn't exist".
BROWSER_OK=0
if [ -d "$PW_LOCAL" ] && [ -n "$NODE" ]; then
  if "$NODE" -e "
    const {chromium}=require('$PW_LOCAL');
    chromium.launch({headless:true}).then(b=>b.close()).then(()=>process.exit(0)).catch(()=>process.exit(1));
  " >/dev/null 2>&1; then
    BROWSER_OK=1; say_ok "chromium browser binary"
  elif [ "$CHECK_ONLY" = 1 ]; then
    say_bad "chromium browser binary not downloaded" "npx playwright install chromium"
  else
    echo "  downloading chromium (~100MB, once)..."
    (cd "$ROOT" && "$NPX" playwright install chromium >/dev/null 2>&1)
    if "$NODE" -e "
      const {chromium}=require('$PW_LOCAL');
      chromium.launch({headless:true}).then(b=>b.close()).then(()=>process.exit(0)).catch(()=>process.exit(1));
    " >/dev/null 2>&1; then BROWSER_OK=1; say_ok "chromium browser binary"
    # Download succeeded but launch failed. On Linux that is almost always missing
    # system libraries, which re-downloading the binary cannot fix; install-deps
    # (root) pulls the apt packages Chromium needs. On macOS a retry is the fix.
    elif [ "$(uname)" = "Linux" ]; then
      say_bad "chromium launch failed (missing system libraries)" "sudo npx playwright install-deps chromium"
    else say_bad "chromium download failed" "cd $ROOT && npx playwright install chromium"; fi
  fi
fi

# ---------------------------------------------------------------- config
echo
echo "Configuration"

if [ -f "$ROOT/brand.json" ]; then
  say_ok "brand.json"
elif [ "$CHECK_ONLY" = 1 ]; then
  say_bad "brand.json missing" "cp brand.example.json brand.json"
else
  cp "$ROOT/brand.example.json" "$ROOT/brand.json"
  say_ok "brand.json created from the example (edit it: palette, font, footer)"
fi

[ -f "$ROOT/pipeline.json" ] && say_ok "pipeline.json (model routing)" \
  || say_bad "pipeline.json missing" "restore it from the repo"

if python3 "$HERE/brandkit.py" >/dev/null 2>&1; then say_ok "brandkit resolves the brand"
else say_bad "brandkit self-check failed" "python3 scripts/brandkit.py"; fi

if bash "$HERE/gate.sh" --has-impeccable >/dev/null 2>&1; then
  say_ok "impeccable detector (optional third gate check)"
else
  say_warn "impeccable not installed — that gate check is skipped, everything else runs"
  say_warn "  optional: npx impeccable  (Apache 2.0, installed from its own source, not bundled here)"
fi

# ---------------------------------------------------------------- proof
if [ "$CHECK_ONLY" = 0 ] && [ "$bad" = 0 ] && [ "$BROWSER_OK" = 1 ]; then
  echo
  echo "Proof (rendering a real card)"
  TMP="$(mktemp -d)"
  if python3 "$HERE/bar-card.py" --config "$ROOT/examples/bar-card.example.json" \
       --theme light --out "$TMP/proof.html" >/dev/null 2>&1 \
     && "$NODE" "$HERE/capture.js" --html "$TMP/proof.html" --slides 1 \
       --outdir "$TMP/png" --scale 2 >/dev/null 2>&1; then
    PNG="$TMP/png/slide-1.png"
    # Assert the ARTIFACT, not the exit code: a zero-byte or tiny PNG is a failure
    # that every exit code in this pipeline would happily report as success.
    SIZE=$(wc -c < "$PNG" 2>/dev/null || echo 0)
    if [ -f "$PNG" ] && [ "$SIZE" -gt 20000 ]; then
      say_ok "rendered a card ($((SIZE/1024))KB PNG)"
    else
      say_bad "render produced no usable PNG (${SIZE} bytes)" "bash scripts/setup.sh --check"
    fi
  else
    say_bad "render failed" "python3 scripts/bar-card.py --config examples/bar-card.example.json --theme light --out /tmp/t.html"
  fi
  rm -rf "$TMP"
fi

# ---------------------------------------------------------------- summary
echo
if [ "$bad" -gt 0 ]; then
  echo "NOT READY: $bad missing, $warn warning(s), $ok ok."
  [ "$CHECK_ONLY" = 1 ] && echo "Run without --check to install."
  exit 1
fi
echo "READY: $ok ok, $warn warning(s)."
echo
echo "Next:"
echo "  1. edit brand.json (palette, font, footer, avatar)"
echo "  2. bash scripts/render.sh examples/bar-card.example.json mycard ./out"
echo "  3. see skills/visual-pipeline/SKILL.md for the full protocol"
exit 0
