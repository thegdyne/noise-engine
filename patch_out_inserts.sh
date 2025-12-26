#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"

limiters=(
  "astro_command/alert_pulse"
  "barbican_hound/routemaster"
  "arctic_henge/aurora"
  "arctic_henge/icebell"
  "beacon_vigil/crown"
  "rlyeh/VESSEL"
  "rakshasa/gold_ring"
  "summer_of_love/golden_haze"
  "amber-threshold/StonePath"
  "seagrass_bay/submerged_drone"
)

leakdcs=(
  "maratus/eye_gleam"
  "leviathan/abyss_drone"
  "leviathan/whale_song"
  "rlyeh/RLYEH"
  "rakshasa/fang_strike"
  "seagrass_bay/current_drift"
)

die() { echo "ERROR: $*" >&2; exit 1; }

[[ -d packs ]] || die "run from repo root (missing ./packs)"

# Resolve "pack/gen" to a .scd file path.
# Tries:
#   packs/<pack>/generators/<gen>.scd
#   packs/<pack>/<gen>.scd
#   packs/<pack>/synthdefs/<gen>.scd
# then falls back to find under the pack dir (case-insensitive).
resolve_scd() {
  local genref="$1"
  local pack="${genref%/*}"
  local gen="${genref#*/}"

  # Find pack directory (exact/case-insensitive, with '-' <-> '_' fallback)
  local pack_alt="${pack//-/_}"
  local packdir=""
  packdir="$(find packs -maxdepth 2 -type d \( -name "$pack" -o -iname "$pack" -o -name "$pack_alt" -o -iname "$pack_alt" \) -print -quit 2>/dev/null || true)"

  # If packdir not found, bail early
  [[ -n "$packdir" ]] || return 1

  # Common exact layouts first
  local candidates=(
    "$packdir/generators/$gen.scd"
    "$packdir/$gen.scd"
    "$packdir/synthdefs/$gen.scd"
  )
  for c in "${candidates[@]}"; do
    if [[ -f "$c" ]]; then
      printf "%s\n" "$c"
      return 0
    fi
  done

  # Fallback: search within packdir for matching filename (case-insensitive)
  local matches=""
  matches="$(find "$packdir" -type f \( -iname "$gen.scd" \) -print 2>/dev/null || true)"
  if [[ -n "$matches" ]]; then
    # If multiple, pick the first but warn
    local count
    count="$(printf "%s\n" "$matches" | wc -l | tr -d ' ')"
    if [[ "$count" -gt 1 ]]; then
      echo "WARN: multiple matches for $genref; using first:" >&2
      printf "%s\n" "$matches" | sed -n '1,10p' >&2
    fi
    printf "%s\n" "$matches" | head -n 1
    return 0
  fi

  return 1
}

# Patch a file by wrapping or inserting right at Out.ar(out, ...);
# op_expr examples:
#   Limiter.ar(__ARG__, 0.95)
#   LeakDC.ar(__ARG__)
#
# - If Out.ar(out, sig); => insert "sig = OP(sig);" above it
# - Else Out.ar(out, <expr>); => replace with Out.ar(out, OP(<expr>));
patch_out() {
  local f="$1" op_name="$2" op_expr="$3" label="$4"

  [[ -f "$f" ]] || { echo "SKIP (missing): $f"; return 1; }

  # Only treat as "already applied" if it appears within ~15 lines before Out.ar
  if awk -v op="$op_name" '
    /Out\.ar\(\s*out\s*,/ { out=NR }
    { lines[NR]=$0 }
    END {
      if (!out) exit 1
      for (i = (out-15); i < out; i++) {
        if (i >= 1 && lines[i] ~ (op "\\.ar")) exit 0
      }
      exit 1
    }
  ' "$f"; then
    echo "SKIP (already has $label near Out): $f"
    return 1
  fi

  local tmp status=0
  tmp="$(mktemp "${f}.tmp.XXXXXX")"


  # NOTE: OP_TMPL must contain "__ARG__"
  OP_TMPL="$op_expr" perl -pe '
    BEGIN {
      $op_tmpl = $ENV{OP_TMPL}; # contains __ARG__
      $did = 0;
    }

    # Case 1: exact sig line => insert sig = OP(sig); above it
    if (!$did && /^(\s*)Out\.ar\(\s*out\s*,\s*sig\s*\);\s*$/) {
      my $indent = $1;
      (my $op = $op_tmpl) =~ s/__ARG__/sig/g;
      $_ = "${indent}sig = ${op};\n${indent}Out.ar(out, sig);\n";
      $did = 1;
    }
    # Case 2: single-line Out.ar(out, <expr>); => wrap expr
    elsif (!$did && /^(\s*)Out\.ar\(\s*out\s*,\s*(.+?)\s*\);\s*$/) {
      my $indent = $1;
      my $arg = $2;
      (my $op = $op_tmpl) =~ s/__ARG__/$arg/g;
      $_ = "${indent}Out.ar(out, ${op});\n";
      $did = 1;
    }

    END { exit($did ? 0 : 2); }
  ' "$f" > "$tmp" || status=$?

  if [[ "$status" -eq 2 ]]; then
    rm -f "$tmp"
    echo "WARN (no Out.ar(out, ...) line matched): $f"
    return 2
  fi

  if cmp -s "$f" "$tmp"; then
    rm -f "$tmp"
    echo "SKIP (no change): $f"
    return 1
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN would patch ($label): $f"
    diff -u "$f" "$tmp" || true
    rm -f "$tmp"
    return 0
  fi

  mv "$tmp" "$f"
  echo "PATCHED ($label): $f"
  return 0
}


patch_one_ref() {
  local genref="$1"
  local f=""
  if ! f="$(resolve_scd "$genref")"; then
    echo "SKIP (missing pack/gen): $genref"
    return 1
  fi

  # LeakDC first (safe ordering: DC removal before limiting)
  case " ${leakdcs[*]} " in
    *" ${genref} "*) patch_out "$f" "LeakDC"  "LeakDC.ar(__ARG__)"        "DC" ;;
  esac

  case " ${limiters[*]} " in
    *" ${genref} "*) patch_out "$f" "Limiter" "Limiter.ar(__ARG__, 0.95)" "clipping" ;;
  esac
}

# union of both lists
declare -A seen=()
for g in "${limiters[@]}" "${leakdcs[@]}"; do
  seen["$g"]=1
done

for g in "${!seen[@]}"; do
  patch_one_ref "$g" || true
done

