#!/usr/bin/env bash
# render.sh — ONE command: config JSON -> ship-ready asset kit.
#
#   bash render.sh <config.json> <basename> [outdir] [brand.json]
#
# Reads `format`, `theme` and `motion` from the config, builds, gates, captures.
#
#   format   card-bar | card-dashboard | card-quote | card-infographic | carousel   (default: card-bar)
#   theme    light | dark | both                                 (default: brand.rules.defaultTheme)
#   motion   true | false                                        (single-frame formats only)
#
# Emits into outdir:
#   <base>-<theme>.png          image post, and the custom thumbnail for a video post
#   <base>-<theme>-motion.mp4   feed video (LinkedIn autoplays muted and loops)
#   <base>-<theme>-motion.gif   comments / DMs / X
#   <base>.pdf                  carousel document post
#
# ffmpeg is the only external dependency, and only for motion.
set -euo pipefail

CONFIG="${1:?config json required}"
BASE="${2:?basename required}"
OUTDIR="${3:-./out}"
BRAND="${4:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$OUTDIR"

NODE="$(command -v node || ls -d "$HOME"/.nvm/versions/node/*/bin/node 2>/dev/null | tail -1 || true)"
[ -z "$NODE" ] && { echo "node not found (needed for Playwright capture)" >&2; exit 1; }

# macOS ships bash 3.2 as /bin/bash and nothing newer. In bash < 4.4 an empty
# array expansion "${ARR[@]}" is an UNBOUND VARIABLE under `set -u`, so the array
# form killed every documented command on a stock Mac. A plain string is safe in
# every bash: BRAND is a single path we control, and word-splitting it is exactly
# the behaviour we want (empty -> no argument at all).
BRAND_ARG=""; [ -n "$BRAND" ] && BRAND_ARG="--brand $BRAND"
DEFAULT_THEME="$(python3 "$HERE/brandkit.py" $BRAND_ARG --get rules.defaultTheme)"
[ -z "$DEFAULT_THEME" ] && DEFAULT_THEME=dark

read -r FORMAT MOTION THEME MMS FPS SLIDES < <(python3 - "$CONFIG" "$DEFAULT_THEME" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
fmt = c.get("format", "carousel" if "slides" in c else "card-bar")
print(fmt,
      str(c.get("motion", False)).lower(),
      c.get("theme", sys.argv[2]),
      c.get("motion_ms", 5500),
      c.get("fps", 24),
      len(c.get("slides", [])) or 1)
PY
)

case "$FORMAT" in
  card-bar)       BUILDER=bar-card.py ;;
  card-dashboard) BUILDER=dashboard-card.py ;;
  card-flow)      BUILDER=flow-card.py ;;
  card-before-after) BUILDER=before-after-card.py ;;
  card-email)     BUILDER=email-card.py ;;
  card-quote)     BUILDER=quote-card.py ;;
  card-infographic) BUILDER=infographic-card.py ;;
  carousel)       BUILDER=carousel-card.py ;;
  *) echo "unknown format: $FORMAT (card-bar|card-dashboard|card-flow|card-before-after|card-email|card-quote|card-infographic|carousel)" >&2; exit 1 ;;
esac

# Variety gate: every other gate here judges ONE card. This one judges the
# sequence, because four consecutive card-flows shipped in Aug 2026 while every
# per-card gate stayed green. Composition varies; the shell never does.
python3 "$HERE/format-variety.py" check "$FORMAT" || exit 1
# Same idea for MOTION: never the same animation twice running, and something new
# every few cards (Anton, 2026-09-28). Blocks an identical signature; warns on a drought.
[ "$MOTION" = true ] && { python3 "$HERE/motion-variety.py" check "$CONFIG" || exit 1; }

# Claims ledger: a rendered figure needs a verified claim. The ledger lives
# beside the config as <config>.claims.json. A config with no figures needs no
# ledger; one WITH figures does not render without one — a generated draft
# cannot satisfy the check, so a human has said where each number came from.
CLAIMS="${CONFIG%.json}.claims.json"
CLAIMS_ARG=""
if [ -f "$CLAIMS" ]; then
  python3 "$HERE/claims.py" check "$CONFIG" "$CLAIMS" || {
    echo "  claims FAILED. Fix the ledger before rendering: $CLAIMS" >&2; exit 1; }
  CLAIMS_ARG="--claims $CLAIMS"
else
  FIGS="$(python3 "$HERE/claims.py" figures "$CONFIG")"
  if [ -n "$FIGS" ]; then
    echo "  FAIL [claims] the config renders figures but has no ledger ($CLAIMS):" >&2
    echo "$FIGS" | sed 's/^/         /' >&2
    echo "  Every number a card shows needs a classification and a source:" >&2
    echo "      python3 scripts/claims.py init $CONFIG   # then set each classification + source" >&2
    exit 1
  fi
fi

# A carousel is per-slide themed inside the config, so it renders once, not per
# theme, and the palette gate takes the union of both themes ("both").
if [ "$FORMAT" = carousel ]; then
  H="$OUTDIR/$BASE.html"
  python3 "$HERE/$BUILDER" --config "$CONFIG" $BRAND_ARG --out "$H"
  bash "$HERE/gate.sh" "$H" both ${BRAND:+"$BRAND"} || {
    echo "  gate FAILED. Not shipping a carousel that failed its own floor." >&2
    exit 1; }
  "$NODE" "$HERE/capture.js" --html "$H" --slides "$SLIDES" --outdir "$OUTDIR/$BASE-slides" --scale 2 >/dev/null
  # Canvas fill + top-edge drift, measured on the RENDERED PNGs. Every other gate
  # judges what is on the card; none judged the space around it, so a deck filling
  # 29% of the frame passed everything and shipped looking like a square floating
  # in a portrait canvas. Runs BEFORE the PDF is copied out, so a failing deck
  # produces no shippable artifact. Portrait only: the square family pins a pager
  # at the bottom, so its footer band is a different height.
  if [ "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('size',''))" "$CONFIG")" = portrait ]; then
    python3 "$HERE/layout-check.py" "$OUTDIR/$BASE-slides" || {
      echo "  layout FAILED. Not shipping a deck whose content floats in the frame." >&2
      exit 1; }
  fi
  [ -f "$OUTDIR/$BASE-slides/carousel.pdf" ] || {
    echo "  FAIL: no carousel.pdf was produced. Not reporting a PDF that does not exist." >&2; exit 1; }
  cp "$OUTDIR/$BASE-slides/carousel.pdf" "$OUTDIR/$BASE.pdf"
  # Same "record only on success" rule the card path uses at the bottom of this
  # file. The carousel branch exits before ever reaching that line, so carousels
  # were invisible to the variety gate: two in a row could never trip it.
  [ "${LV_NO_RECORD:-}" = 1 ] || python3 "$HERE/format-variety.py" record "$FORMAT" --config "$CONFIG"
  echo "  -> $BASE.pdf ($SLIDES slides) + per-slide PNGs in $BASE-slides/"
  echo "  note: no per-slide qa-visual bundle yet; palette, dash, claims and layout gates ran."
  echo "Done. Ship the PDF as a LinkedIn document post."
  exit 0
fi

THEMES="$THEME"; [ "$THEME" = both ] && THEMES="light dark"
for TH in $THEMES; do
  H="$OUTDIR/$BASE-$TH.html"
  python3 "$HERE/$BUILDER" --config "$CONFIG" --theme "$TH" $BRAND_ARG --out "$H"
  bash "$HERE/gate.sh" "$H" "$TH" ${BRAND:+"$BRAND"} || {
    echo "  gate FAILED. Not writing a shipped PNG from a card that failed its own floor." >&2
    exit 1; }

  # QA gate: the deterministic assertion suite runs on EVERY render, and the
  # shipped PNG is copied out of the candidate it certifies (native-2x), so the
  # artifact and its evidence are the same pixels by construction. Candidate
  # dirs are immutable — a fresh one per run, never --force over a reviewed one.
  CAND="$OUTDIR/$BASE-$TH-candidate-$(date +%Y%m%d-%H%M%S)-$$"
  QA_MANIFEST="${CONFIG%.json}.qa.json"
  MAN_ARG=""; [ -f "$QA_MANIFEST" ] && MAN_ARG="--manifest $QA_MANIFEST"
  "$NODE" "$HERE/qa-visual.cjs" --html "$H" --theme "$TH" --outdir "$CAND" $MAN_ARG $CLAIMS_ARG $BRAND_ARG || {
    echo "  QA FAILED (see $CAND/qa-report.json). Not shipping a card that failed its floor." >&2
    exit 1; }
  cp "$CAND/native-2x.png" "$OUTDIR/$BASE-$TH.png"
  echo "  -> $BASE-$TH.png"
  echo "  -> candidate $CAND  (qa-report.json + feed-preview.png = the taste loop's round-1 evidence)"

  if [ "$MOTION" = true ]; then
    HM="$OUTDIR/$BASE-$TH-motion.html"
    python3 "$HERE/$BUILDER" --config "$CONFIG" --theme "$TH" --motion $BRAND_ARG --out "$HM"
    FR="$OUTDIR/$BASE-$TH-frames"; rm -rf "$FR"
    "$NODE" "$HERE/record.js" "$HM" "$FR" "$MMS" "$FPS" >/dev/null
    # Seam, lossless, BEFORE encoding: record.js captures t = 0..motion_ms inclusive,
    # so the last frame must equal frame 0 exactly. check_seam() existed with a
    # self-test but nothing called it, and claim-check shipped a broken loop with QA
    # PASS (2026-09-27). Then drop that last frame: it IS frame 0, and encoding it
    # stalled every loop by one frame.
    python3 "$HERE/motion-check.py" seam-frames --dir "$FR" || {
      echo "  seam FAILED for $BASE-$TH. Not shipping a loop that jumps." >&2; exit 1; }
    LASTF="$(ls "$FR"/f*.png | tail -1)"; rm -f "$LASTF"
    # Excursion: report-only until its floor is calibrated on shipped cards.
    python3 "$HERE/motion-check.py" excursion --dir "$FR" >/dev/null || \
      echo "  WARN [excursion] $BASE-$TH barely moves (report-only; see motion-check.py EXCURSION_FLOOR_PCT)" >&2
    # Dead hold: some 1.5s window where under 0.2% of the frame changes (che-video-brain
    # MOTION.md rule). Report-only: every card built before motion_live fails it.
    DH="$(python3 "$HERE/motion-check.py" dead-hold --dir "$FR" --fps "$FPS")" || {
      echo "  WARN [dead-hold] $BASE-$TH freezes (report-only; try motion_live / motion_morph)" >&2
      echo "$DH" | grep -E "^  - " >&2 || true; }
    ffmpeg -y -framerate "$FPS" -i "$FR/f%04d.png" -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
      "$OUTDIR/$BASE-$TH-motion.mp4" >/dev/null 2>&1
    # Size the GIF FROM LinkedIn's pixel budget (width x height x frames) with the
    # same module that defines it, then ASSERT the result. The old fixed
    # 720px / 18fps fit a 5.5s card and silently blew the budget 4.5x on a 14s
    # infographic, because nothing checked the GIF this script emits (2026-09-22).
    IFS=, read -r VW VH < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
      -of csv=p=0 "$OUTDIR/$BASE-$TH-motion.mp4")
    read -r GW GH GFPS GFRAMES < <(python3 "$HERE/motion-check.py" gif-spec --width "$VW" --height "$VH" --duration-ms "$MMS")
    ffmpeg -y -i "$OUTDIR/$BASE-$TH-motion.mp4" \
      -vf "fps=$GFPS,scale=$GW:$GH:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 \
      "$OUTDIR/$BASE-$TH-motion.gif" >/dev/null 2>&1
    NGF="$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$OUTDIR/$BASE-$TH-motion.gif")"
    python3 "$HERE/motion-check.py" budget --width "$GW" --height "$GH" --frames "$NGF" --fps "$GFPS" \
      --bytes "$(wc -c < "$OUTDIR/$BASE-$TH-motion.gif" | tr -d ' ')" >/dev/null || {
      echo "  GIF budget FAILED for $BASE-$TH-motion.gif (${GW}x${GH}x${NGF}). Not shipping an oversized GIF." >&2
      rm -f "$OUTDIR/$BASE-$TH-motion.gif"; exit 1; }
    rm -rf "$FR"
    echo "  -> $BASE-$TH-motion.mp4 + .gif"
  fi
done

# Recorded only on success, so a failed render never counts against variety.
# LV_NO_RECORD=1 skips it for regression/test renders: a builder-change check
# is not a shipped post, and twice now one has manufactured a false streak.
# --config makes a re-render of the SAME card idempotent: this gate counts
# shipped posts, not render invocations.
[ "${LV_NO_RECORD:-}" = 1 ] || python3 "$HERE/format-variety.py" record "$FORMAT" --config "$CONFIG"
[ "${LV_NO_RECORD:-}" = 1 ] || [ "$MOTION" != true ] || python3 "$HERE/motion-variety.py" record "$CONFIG"

echo "Done. PNG = image post or video thumbnail. MP4 = video post (autoplay + loop)."
[ "$MOTION" = true ] && echo "Posting a video: upload the MP4 and SET THE CUSTOM THUMBNAIL to the PNG. Frame 0 is the empty pre-animation state."
exit 0
