#!/usr/bin/env bash
# animate.sh — same config, Remotion output.
#
#   bash animate.sh <config.json> <basename> [outdir] [brand.json]
#
# Builds the card's motion HTML with the normal builder, hands it to Remotion,
# and renders an MP4 (plus a GIF when ffmpeg is present). Remotion drives the
# SAME data-s/data-d/data-count/data-wipe contract the Playwright recorder uses,
# so the animation is identical, just rendered frame-accurately and in parallel.
#
# Use this instead of render.sh's built-in motion when you want:
#   remotion studio    live scrubbing while you tune timing
#   multi-scene        sequencing several cards into one video
#   audio              voiceover or music under the card
#
# First run needs `npm install` inside remotion/ (Remotion is not vendored).
set -euo pipefail

CONFIG="${1:?config json required}"
BASE="${2:?basename required}"
OUTDIR="${3:-./out}"
BRAND="${4:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
RE="$ROOT/remotion"
mkdir -p "$OUTDIR" "$RE/public"

if [ ! -d "$RE/node_modules" ]; then
  echo "Remotion is not installed. Run:  (cd $RE && npm install)" >&2
  exit 1
fi

# macOS ships bash 3.2 as /bin/bash and nothing newer. In bash < 4.4 an empty
# array expansion "${ARR[@]}" is an UNBOUND VARIABLE under `set -u`, so the array
# form killed every documented command on a stock Mac. A plain string is safe in
# every bash: BRAND is a single path we control, and word-splitting it is exactly
# the behaviour we want (empty -> no argument at all).
BRAND_ARG=""; [ -n "$BRAND" ] && BRAND_ARG="--brand $BRAND"
DEFAULT_THEME="$(python3 "$HERE/brandkit.py" $BRAND_ARG --get rules.defaultTheme)"
[ -z "$DEFAULT_THEME" ] && DEFAULT_THEME=dark

read -r FORMAT THEME MMS W H < <(python3 - "$CONFIG" "$DEFAULT_THEME" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
theme = c.get("theme", sys.argv[2])
if theme == "both":
    theme = sys.argv[2]                 # a video has one theme; pick the brand default
size = c.get("size", "square")
w, h = (1080, 1350) if size == "portrait" else (1080, 1080)
if isinstance(size, dict):
    w, h = int(size["w"]), int(size["h"])
print(c.get("format", "card-bar"), theme, c.get("motion_ms", 5500), w, h)
PY
)

# Required design inputs. Motion fails in time, which no screenshot shows, so the
# timing is authored and reviewed before a single frame renders.
STORY="${STORYBOARD:-${CONFIG%.json}.storyboard.md}"
if [ ! -f "$STORY" ]; then
  echo "No storyboard for this config. Motion requires one." >&2
  echo "  python3 $HERE/storyboard.py init $CONFIG" >&2
  exit 1
fi
python3 "$HERE/storyboard.py" check "$STORY" || {
  echo "  (fill in the storyboard above, then re-run)" >&2; exit 1; }

case "$FORMAT" in
  card-bar)       BUILDER=bar-card.py ;;
  card-dashboard) BUILDER=dashboard-card.py ;;
  card-flow)      BUILDER=flow-card.py ;;
  card-before-after) BUILDER=before-after-card.py ;;
  card-email)     BUILDER=email-card.py ;;
  card-infographic)
    # Animates through render.sh's Playwright recorder (verified 2026-09-22: 14s,
    # 1080x1350, lossless loop seam). This Remotion path has NOT been exercised at
    # a portrait canvas, so it refuses rather than implying it works.
    echo "card-infographic animates via render.sh (verified); the Remotion path is untested at 1080x1350." >&2
    echo "  bash $HERE/render.sh $CONFIG $BASE $OUTDIR" >&2
    exit 1 ;;
  card-quote)
    # quote-card.py has no --motion path (it rejects the flag), so routing it here
    # died mid-run with an argparse error. Quote is a static format by design.
    echo "card-quote is a static format: it has no motion path." >&2
    echo "Render it as a PNG:  bash $HERE/render.sh $CONFIG $BASE $OUTDIR" >&2
    exit 1 ;;
  *) echo "animate.sh handles single-frame formats only (got: $FORMAT)." >&2
     echo "For a multi-slide carousel, render the PDF with render.sh." >&2; exit 1 ;;
esac

# 1. build the motion HTML + gate it, exactly as the static path does
python3 "$HERE/$BUILDER" --config "$CONFIG" --theme "$THEME" --motion $BRAND_ARG \
  --out "$RE/public/card.html"
bash "$HERE/gate.sh" "$RE/public/card.html" "$THEME" ${BRAND:+"$BRAND"} || {
  echo "  gate FAILED. A gate that warns is a gate that gets scrolled past." >&2; exit 1; }

# 2. poster frame, which is also the video's custom thumbnail
python3 "$HERE/$BUILDER" --config "$CONFIG" --theme "$THEME" $BRAND_ARG \
  --out "$OUTDIR/$BASE-$THEME.html"
NODE="$(ls -d "$HOME"/.nvm/versions/node/*/bin/node 2>/dev/null | tail -1 || command -v node || true)"
"$NODE" "$HERE/capture.js" --html "$OUTDIR/$BASE-$THEME.html" --slides 1 \
  --outdir "$OUTDIR/$BASE-$THEME-png" --scale 2 >/dev/null
cp "$OUTDIR/$BASE-$THEME-png/slide-1.png" "$OUTDIR/$BASE-$THEME.png"

# 3. Remotion render
PROPS=$(python3 -c "import json,sys;print(json.dumps({'htmlFile':'card.html','width':int(sys.argv[1]),'height':int(sys.argv[2]),'durationMs':int(sys.argv[3])}))" "$W" "$H" "$MMS")
# The pixel budget is a GIF constraint. The master has no such ceiling, so gating
# it here forbade every card this repo ships and animate.sh could never emit an MP4.
read -r GW GH GFPS GFRAMES < <(python3 "$HERE/motion-check.py" gif-spec \
  --width "$W" --height "$H" --duration-ms "$MMS")
echo "  GIF derivative will be ${GW}x${GH} @${GFPS}fps, ${GFRAMES} frames (budget-compliant)"

MP4="$(cd "$OUTDIR" && pwd)/$BASE-$THEME-motion.mp4"
# Call the binary by absolute path: an nvm-managed shell exports `node`/`npx` as
# lazy-loading FUNCTIONS that recurse forever in a non-interactive shell.
NODE_BIN_DIR="$(dirname "$NODE")"
# PNG frames and a low CRF, because this card family is mostly static type. Remotion
# captures frames as JPEG q80 by default, and h264 then spends its bits on the moving
# nodes, so the header and footer text accumulates residual error across the render and
# snaps back to the crisp I-frame at the loop point. That reads as the whole chrome
# jumping on every repeat, which is exactly what it looked like.
(cd "$RE" && "$NODE_BIN_DIR/npx" remotion render Card "$MP4" --props="$PROPS" \
  --image-format=png --crf=12)

# A loop that does not close jumps on every repeat, and in a feed that is constant.
# Gate the seam on changed AREA, not peak channel delta. The master is lossy, so
# on a text-heavy card H.264 residual drift along glyph edges peaks around 240
# while the animation resets exactly. Measured on the flow card: a clean loop
# moves 1.2% of the frame, one node failing to dissolve moves 11.3%, and the
# broken master's PEAK delta (194) is lower than the clean one's (243) - which is
# why the old peak gate could not tell them apart. 2.5% sits between, ~2x either way.
python3 "$HERE/motion-check.py" seam --video "$MP4" --max-changed-pct 2.5 || \
  echo "  (seam is not clean: frame 0 and the closing hold must match)" >&2

if command -v ffmpeg >/dev/null; then
  ffmpeg -y -i "$MP4" \
    -vf "fps=${GFPS},scale=${GW}:${GH}:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=full[p];[s1][p]paletteuse=dither=none" \
    -loop 0 "${MP4%.mp4}.gif" >/dev/null 2>&1
  # Assert the ARTIFACT against the budget, never the ffmpeg exit code.
  python3 "$HERE/motion-check.py" budget --width "$GW" --height "$GH" --frames "$GFRAMES" \
    --fps "$GFPS" --bytes "$(wc -c < "${MP4%.mp4}.gif")" >/dev/null \
    && echo "  -> $BASE-$THEME-motion.gif (budget-compliant)" \
    || echo "  !! GIF exceeds LinkedIn's budget, do not upload it" >&2
fi

echo "  -> $BASE-$THEME.png (poster / custom thumbnail)"
echo "  -> $BASE-$THEME-motion.mp4"
echo "Scrub and tune timing:  (cd $RE && npx remotion studio)"
