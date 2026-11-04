#!/usr/bin/env bash
# gate.sh — deterministic pre-ship checks on a built HTML card.
#
#   bash gate.sh <card.html> <light|dark> [brand.json]
#
# Three checks, all mechanical:
#   1. palette   every literal hex must be legal for this theme in brand.json
#   2. dashes    em/en dashes in copy (off by default via brand.rules.banDashes)
#   3. impeccable  anti-AI-slop detector, if the `impeccable` skill is installed
#
# This is a FLOOR, not a taste check. A card can pass every line here and still
# be mediocre. The taste loop in SKILL.md is what judges whether it is good.
set -uo pipefail

find_impeccable() {
  # Optional third-party dependency (Apache 2.0). Installed as a bare skill, as
  # part of a plugin, or vendored per project. Hardcoding one shape made the
  # check silently skip for anyone who installed it another way.
  #
  # It happened AGAIN on 2026-09-12: upstream replaced scripts/detect.mjs with a
  # multi-command CLI (`impeccable detect <file>`), so every path below missed
  # and the gate reported "not installed" while the skill sat right there. Both
  # entrypoint shapes are matched now, CLI first since that is current.
  local c
  for c in \
    "${IMPECCABLE_DETECT:-}" \
    "$HOME/.claude/skills/impeccable/scripts/impeccable" \
    "$HOME/.claude/plugins/marketplaces"/*/skills/impeccable/scripts/impeccable \
    "$HOME/.claude/plugins/cache"/*/*/skills/impeccable/scripts/impeccable \
    "./.claude/skills/impeccable/scripts/impeccable" \
    "$HOME/.claude/skills/impeccable/scripts/detect.mjs" \
    "$HOME/.claude/plugins/marketplaces"/*/skills/impeccable/scripts/detect.mjs \
    "$HOME/.claude/plugins/cache"/*/*/skills/impeccable/scripts/detect.mjs \
    "./.claude/skills/impeccable/scripts/detect.mjs"
  do
    [ -n "$c" ] && [ -f "$c" ] && { echo "$c"; return 0; }
  done
  return 1
}

if [ "${1:-}" = "--has-impeccable" ]; then
  find_impeccable >/dev/null && exit 0 || exit 1
fi

# --self-test: two-sided by house standard — seeded violations this gate must
# CATCH and a clean control it must PASS, exercised through the real code path
# (recursive invocation), against the repo's example brand so it is
# deterministic on any machine. A check that has never failed is not known to work.
if [ "${1:-}" = "--self-test" ]; then
  ST_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  EXB="$ST_HERE/../brand.example.json"
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  LIGHT="$(python3 "$ST_HERE/brandkit.py" --brand "$EXB" --palette light)"
  DARK="$(python3 "$ST_HERE/brandkit.py" --brand "$EXB" --palette dark)"
  L1="${LIGHT%% *}"
  DONLY=""; for h in $DARK; do case " $LIGHT " in *" $h "*) : ;; *) DONLY="$h"; break ;; esac; done
  BAD="";   for h in "#010203" "#040506" "#070809"; do
    case " $LIGHT $DARK " in *" $h "*) : ;; *) BAD="$h"; break ;; esac; done
  [ -n "$BAD" ] || { echo "gate self-test: could not find an off-palette hex" >&2; exit 1; }
  pass=0; fail=0
  t() {
    if bash "$0" "$3" "$4" "$EXB" >/dev/null 2>&1; then GOT=0; else GOT=1; fi
    if [ "$GOT" = "$2" ]; then echo "  ok    $1"; pass=$((pass+1))
    else echo "  FAIL  $1 (want exit $2, got $GOT)"; fail=$((fail+1)); fi
  }
  printf '<style>#slide-1{text-wrap:balance;}</style><div style="color:%s">clean, steady copy</div>' "$L1" > "$T/clean.html"
  printf '<div style="color:%s">off palette</div>' "$BAD" > "$T/off.html"
  printf '<div style="color:%s">a claim — with a dash</div>' "$L1" > "$T/dash.html"
  printf '<style>#slide-1{text-wrap:balance;}</style><div style="color:%s">light</div><div style="color:%s">dark</div>' "$L1" "$DONLY" > "$T/mix.html"
  t "clean control passes"        0 "$T/clean.html" light
  t "off-palette hex fails"       1 "$T/off.html"   light
  t "em-dash fails"               1 "$T/dash.html"  light
  printf '<style>#slide-1{color:%s;text-wrap:balance;}</style><div style="color:%s">wrapped</div>' "$L1" "$L1" > "$T/wrap-ok.html"
  printf '<style>#slide-1{color:%s;}</style><div style="color:%s">unwrapped</div>' "$L1" "$L1" > "$T/wrap-no.html"
  t "wrap rule present passes"    0 "$T/wrap-ok.html" light
  t "missing wrap rule fails"     1 "$T/wrap-no.html" light
  printf '<style>#slide-1{font-family:text-wrap:balance;%s;color:%s;text-wrap:balance;}</style><div style="color:%s">x</div>' "Arial" "$L1" "$L1" > "$T/font-bad.html"
  t "malformed font-family fails"  1 "$T/font-bad.html" light
  if [ -n "$DONLY" ]; then
    t "mixed themes fail single"  1 "$T/mix.html"   light
    t "mixed themes pass union"   0 "$T/mix.html"   both
  else
    echo "  skip  union test (example palettes fully overlap)"
  fi
  [ "$fail" -eq 0 ] && { echo "gate self-test: OK ($pass checks, both sides)"; exit 0; }
  echo "gate self-test: FAILED ($fail of $((pass+fail)))" >&2; exit 1
fi
HTML="${1:?usage: gate.sh <card.html> <light|dark|both> [brand.json]}"
THEME="${2:?theme required (light|dark|both)}"
BRAND="${3:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# macOS ships bash 3.2 as /bin/bash and nothing newer. In bash < 4.4 an empty
# array expansion "${ARR[@]}" is an UNBOUND VARIABLE under `set -u`, so the array
# form killed every documented command on a stock Mac. A plain string is safe in
# every bash: BRAND is a single path we control, and word-splitting it is exactly
# the behaviour we want (empty -> no argument at all).
BRAND_ARG=""; [ -n "$BRAND" ] && BRAND_ARG="--brand $BRAND"

fail=0


# 1. palette --------------------------------------------------------------
# "both" = the union of the two theme palettes: a carousel is per-slide themed,
# so one HTML file legally mixes light and dark hexes.
if [ "$THEME" = both ]; then
  ALLOWED=" $(python3 "$HERE/brandkit.py" $BRAND_ARG --palette light) $(python3 "$HERE/brandkit.py" $BRAND_ARG --palette dark) "
else
  ALLOWED=" $(python3 "$HERE/brandkit.py" $BRAND_ARG --palette "$THEME") "
fi
BAD=""
for HEX in $(grep -oE '#[0-9a-fA-F]{6}' "$HTML" | tr 'a-f' 'A-F' | sort -u); do
  case "$ALLOWED" in *" $HEX "*) : ;; *) BAD="$BAD $HEX" ;; esac
done
if [ -n "$BAD" ]; then
  echo "  FAIL [palette/$THEME] off-brand hex:$BAD" >&2
  echo "       legal:$ALLOWED (add to brand.rules.extraPaletteHex if intended)" >&2
  fail=1
else
  echo "  ok   [palette/$THEME]"
fi

# 2. dashes ---------------------------------------------------------------
if [ "$(python3 "$HERE/brandkit.py" $BRAND_ARG --get rules.banDashes)" = "True" ]; then
  if grep -qE '—|–|&mdash;|&ndash;' "$HTML"; then
    echo "  FAIL [dashes] em/en dash in copy" >&2
    grep -noE '.{0,40}(—|–|&mdash;|&ndash;).{0,40}' "$HTML" | head -3 >&2
    fail=1
  else
    echo "  ok   [dashes]"
  fi
fi

# 3. wrap ------------------------------------------------------------------
# text-wrap INHERITS, so one declaration on the card root covers every text node
# in it. All six card builders shipped with ZERO text-wrap declarations, which is
# how a 4-word chip rendered as "Clay to LinkedIn / Ads" - an orphaned last word
# on a 2-line fragment. Asserting the ROOT declaration (not a list of classes)
# is what makes a newly added element inherit the rule instead of missing it.
if grep -q "text-wrap:balance" "$HTML"; then
  echo "  ok   [wrap]"
else
  echo "  FAIL [wrap] no text-wrap:balance on the card root; short fragments will orphan" >&2
  fail=1
fi

# 4. font ------------------------------------------------------------------
# A font-family VALUE can never contain a colon. When one does, a property name
# has leaked into the declaration ("font-family:text-wrap:balance;'Space Grotesk'")
# and the whole rule is invalid, so the browser silently falls back to a serif.
# That shipped through palette, dashes, wrap, claims and layout untouched: the
# carousel path runs no qa-visual, so nothing else here looks at the typeface.
BADFF="$(grep -o "font-family:[^;\"}]*" "$HTML" | grep ":" | grep -v "^font-family:[^:]*$" || true)"
if [ -n "$BADFF" ]; then
  echo "  FAIL [font] malformed font-family (a property leaked into the value):" >&2
  echo "$BADFF" | sed 's/^/         /' >&2
  fail=1
elif grep -q "font-family:" "$HTML"; then
  echo "  ok   [font]"
fi

# 5. impeccable -----------------------------------------------------------
DET="$(find_impeccable || true)"
if [ -n "$DET" ] && [ -f "$DET" ]; then
  case "$DET" in
    # BOTH streams, always. The CLI writes every finding to STDERR and leaves
    # stdout empty (exit 2 when it finds something), so the previous `2>/dev/null`
    # captured nothing and the check reported a clean "ok" on a card the detector
    # had just flagged twice. Merging is safe for either entrypoint.
    *.mjs)
      NODE="$(command -v node || ls -d "$HOME"/.nvm/versions/node/*/bin/node 2>/dev/null | tail -1)"
      RAW="$([ -n "$NODE" ] && "$NODE" "$DET" "$HTML" 2>&1 || true)"
      # legacy detect.mjs prints findings as "  line N  <slug> ..."
      F="$(printf '%s\n' "$RAW" | grep -E '^[[:space:]]+line ' || true)" ;;
    *)
      RAW="$("$DET" detect "$HTML" 2>&1 || true)"
      # CLI prints findings as "  [slug] <description>"
      F="$(printf '%s\n' "$RAW" | grep -E '^[[:space:]]+\[' || true)" ;;
  esac
  # Drop findings that are BRAND LOCKS, true by construction on every card this
  # repo ships, so they would fire forever and train the reader to ignore the
  # whole check. Everything else still warns.
  #   single-font / overused-font  the typeface is one decision made once at
  #                                brand level; a per-card gate cannot re-litigate it.
  F="$(printf '%s\n' "$F" | grep -v 'single-font' | grep -v 'overused-font' || true)"
  F="$(printf '%s\n' "$F" | sed '/^$/d')"
  if [ -n "$F" ]; then echo "  WARN [impeccable]"; echo "$F"; else echo "  ok   [impeccable]"; fi
elif [ -d "$HOME/.claude/skills/impeccable" ]; then
  # Distinguish "absent" from "present but unrecognised" - the second is a bug
  # in this file, and reporting it as "not installed" is how it hid for weeks.
  echo "  skip [impeccable] skill is INSTALLED but no known entrypoint matched; update find_impeccable" >&2
else
  echo "  skip [impeccable] detector not installed"
fi

exit $fail
