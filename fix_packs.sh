#!/bin/bash
# Fix pack validation errors for fuego_celeste, beacon_vigil, and boneyard
# Run from noise-engine root directory

set -e

echo "Fixing pack validation errors..."

# =============================================================================
# FIX 1: fuego_celeste - Fix all labels to be exactly 3 chars
# =============================================================================
echo ""
echo "=== Fixing fuego_celeste labels ==="

# magma_drone.json
sed -i '' 's/"label": "DPTH"/"label": "DPT"/g' packs/fuego_celeste/generators/magma_drone.json
sed -i '' 's/"label": "CHURN"/"label": "CHR"/g' packs/fuego_celeste/generators/magma_drone.json
sed -i '' 's/"label": "HEAT"/"label": "HET"/g' packs/fuego_celeste/generators/magma_drone.json
sed -i '' 's/"label": "PRESS"/"label": "PRS"/g' packs/fuego_celeste/generators/magma_drone.json
sed -i '' 's/"label": "RUMBL"/"label": "RMB"/g' packs/fuego_celeste/generators/magma_drone.json
echo "  ✓ magma_drone.json"

# stellar_void.json
sed -i '' 's/"label": "VAST"/"label": "VST"/g' packs/fuego_celeste/generators/stellar_void.json
sed -i '' 's/"label": "DRIFT"/"label": "DFT"/g' packs/fuego_celeste/generators/stellar_void.json
sed -i '' 's/"label": "COLD"/"label": "CLD"/g' packs/fuego_celeste/generators/stellar_void.json
sed -i '' 's/"label": "STARS"/"label": "STR"/g' packs/fuego_celeste/generators/stellar_void.json
sed -i '' 's/"label": "DIST"/"label": "DST"/g' packs/fuego_celeste/generators/stellar_void.json
echo "  ✓ stellar_void.json"

# lava_burst.json
sed -i '' 's/"label": "FORCE"/"label": "FRC"/g' packs/fuego_celeste/generators/lava_burst.json
sed -i '' 's/"label": "SPRAY"/"label": "SPY"/g' packs/fuego_celeste/generators/lava_burst.json
sed -i '' 's/"label": "GLOW"/"label": "GLW"/g' packs/fuego_celeste/generators/lava_burst.json
sed -i '' 's/"label": "ROCK"/"label": "RCK"/g' packs/fuego_celeste/generators/lava_burst.json
sed -i '' 's/"label": "SIZZL"/"label": "SZL"/g' packs/fuego_celeste/generators/lava_burst.json
echo "  ✓ lava_burst.json"

# star_ping.json
sed -i '' 's/"label": "TWNKL"/"label": "TWK"/g' packs/fuego_celeste/generators/star_ping.json
sed -i '' 's/"label": "DIST"/"label": "DST"/g' packs/fuego_celeste/generators/star_ping.json
sed -i '' 's/"label": "COLOR"/"label": "CLR"/g' packs/fuego_celeste/generators/star_ping.json
sed -i '' 's/"label": "SIZE"/"label": "SIZ"/g' packs/fuego_celeste/generators/star_ping.json
sed -i '' 's/"label": "ECHO"/"label": "ECH"/g' packs/fuego_celeste/generators/star_ping.json
echo "  ✓ star_ping.json"

# ash_rise.json
sed -i '' 's/"label": "RISE"/"label": "RIS"/g' packs/fuego_celeste/generators/ash_rise.json
sed -i '' 's/"label": "BILOW"/"label": "BLW"/g' packs/fuego_celeste/generators/ash_rise.json
sed -i '' 's/"label": "CHOKE"/"label": "CHK"/g' packs/fuego_celeste/generators/ash_rise.json
sed -i '' 's/"label": "GREY"/"label": "GRY"/g' packs/fuego_celeste/generators/ash_rise.json
sed -i '' 's/"label": "CURL"/"label": "CRL"/g' packs/fuego_celeste/generators/ash_rise.json
echo "  ✓ ash_rise.json"

# galactic_core.json
sed -i '' 's/"label": "CORE"/"label": "COR"/g' packs/fuego_celeste/generators/galactic_core.json
sed -i '' 's/"label": "SPIRL"/"label": "SPL"/g' packs/fuego_celeste/generators/galactic_core.json
sed -i '' 's/"label": "PINK"/"label": "PNK"/g' packs/fuego_celeste/generators/galactic_core.json
sed -i '' 's/"label": "MASS"/"label": "MAS"/g' packs/fuego_celeste/generators/galactic_core.json
sed -i '' 's/"label": "ANCNT"/"label": "ANC"/g' packs/fuego_celeste/generators/galactic_core.json
echo "  ✓ galactic_core.json"

# ember_trail.json
sed -i '' 's/"label": "SPARK"/"label": "SPK"/g' packs/fuego_celeste/generators/ember_trail.json
sed -i '' 's/"label": "FLOW"/"label": "FLW"/g' packs/fuego_celeste/generators/ember_trail.json
sed -i '' 's/"label": "GLOW"/"label": "GLW"/g' packs/fuego_celeste/generators/ember_trail.json
sed -i '' 's/"label": "COOL"/"label": "COL"/g' packs/fuego_celeste/generators/ember_trail.json
sed -i '' 's/"label": "SCATR"/"label": "SCT"/g' packs/fuego_celeste/generators/ember_trail.json
echo "  ✓ ember_trail.json"

# cosmic_dust.json
sed -i '' 's/"label": "CLOUD"/"label": "CLD"/g' packs/fuego_celeste/generators/cosmic_dust.json
sed -i '' 's/"label": "SHIMR"/"label": "SHM"/g' packs/fuego_celeste/generators/cosmic_dust.json
sed -i '' 's/"label": "FINE"/"label": "FIN"/g' packs/fuego_celeste/generators/cosmic_dust.json
sed -i '' 's/"label": "DRIFT"/"label": "DFT"/g' packs/fuego_celeste/generators/cosmic_dust.json
sed -i '' 's/"label": "GLIT"/"label": "GLT"/g' packs/fuego_celeste/generators/cosmic_dust.json
echo "  ✓ cosmic_dust.json"

echo "  fuego_celeste: 40 label errors fixed"

# =============================================================================
# FIX 2: beacon_vigil - Fix synthdef names (forge_beacon_X -> forge_beacon_vigil_X)
# =============================================================================
echo ""
echo "=== Fixing beacon_vigil synthdef names ==="

# Fix JSON files
for gen in torch crown harbor vigil passage beacon threshold diaspora; do
    sed -i '' "s/forge_beacon_${gen}/forge_beacon_vigil_${gen}/g" packs/beacon_vigil/generators/${gen}.json
    echo "  ✓ ${gen}.json"
done

# Fix SCD files
for gen in torch crown harbor vigil passage beacon threshold diaspora; do
    sed -i '' "s/forge_beacon_${gen}/forge_beacon_vigil_${gen}/g" packs/beacon_vigil/generators/${gen}.scd
    echo "  ✓ ${gen}.scd"
done

echo "  beacon_vigil: 16 synthdef naming errors fixed"

# =============================================================================
# FIX 3: boneyard - Fix 'UV' label to be 3 chars
# =============================================================================
echo ""
echo "=== Fixing boneyard labels ==="

sed -i '' 's/"label": "UV"/"label": "UVR"/g' packs/boneyard/generators/canopy.json
echo "  ✓ canopy.json"
echo "  boneyard: 1 label error fixed"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "============================================================"
echo "All fixes applied!"
echo ""
echo "Label changes summary:"
echo "  fuego_celeste:"
echo "    DPTH→DPT, CHURN→CHR, HEAT→HET, PRESS→PRS, RUMBL→RMB"
echo "    VAST→VST, DRIFT→DFT, COLD→CLD, STARS→STR, DIST→DST"
echo "    FORCE→FRC, SPRAY→SPY, GLOW→GLW, ROCK→RCK, SIZZL→SZL"
echo "    TWNKL→TWK, COLOR→CLR, SIZE→SIZ, ECHO→ECH"
echo "    RISE→RIS, BILOW→BLW, CHOKE→CHK, GREY→GRY, CURL→CRL"
echo "    CORE→COR, SPIRL→SPL, PINK→PNK, MASS→MAS, ANCNT→ANC"
echo "    SPARK→SPK, FLOW→FLW, COOL→COL, SCATR→SCT"
echo "    CLOUD→CLD, SHIMR→SHM, FINE→FIN, GLIT→GLT"
echo ""
echo "  beacon_vigil: forge_beacon_* → forge_beacon_vigil_*"
echo ""
echo "  boneyard: UV→UVR"
echo ""
echo "Run validator to confirm:"
echo "  python tools/forge_validate.py packs/fuego_celeste"
echo "  python tools/forge_validate.py packs/beacon_vigil"
echo "  python tools/forge_validate.py packs/boneyard"
echo "============================================================"
