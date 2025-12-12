#!/bin/bash
# Single Source of Truth checker
# Dynamically finds violations of centralized config/theme

REPO_DIR=~/repos/noise-engine
SRC_DIR="$REPO_DIR/src"
SC_DIR="$REPO_DIR/supercollider"
CONFIG_FILE="$SRC_DIR/config/__init__.py"
ISSUES=0
WARNINGS=0

echo "🔍 Single Source of Truth Check"
echo "================================"
echo ""

# Helper to count lines
count_lines() {
    if [ -n "$1" ]; then
        echo "$1" | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

# ============================================
# PYTHON GUI CHECKS
# ============================================
echo "📦 PYTHON GUI CHECKS"
echo "--------------------"

# 1. Hardcoded fonts in QFont() calls
echo ""
echo "📝 Checking for hardcoded fonts..."
FONT_HITS=$(grep -rn "QFont(" "$SRC_DIR/gui" --include="*.py" 2>/dev/null | grep -v "FONT_FAMILY\|MONO_FONT" | grep -v "theme.py" | grep "'[A-Za-z]")
if [ -n "$FONT_HITS" ]; then
    echo "❌ Hardcoded fonts found:"
    echo "$FONT_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(count_lines "$FONT_HITS")))
else
    echo "✅ No hardcoded fonts"
fi

# 2. Hardcoded hex colors outside theme.py
echo ""
echo "🎨 Checking for hardcoded colors..."
COLOR_HITS=$(grep -rn "#[0-9a-fA-F]\{3,6\}" "$SRC_DIR/gui" --include="*.py" 2>/dev/null | grep -v "theme.py" | grep -v "COLORS\[")
if [ -n "$COLOR_HITS" ]; then
    echo "❌ Hardcoded colors found:"
    echo "$COLOR_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(count_lines "$COLOR_HITS")))
else
    echo "✅ No hardcoded colors"
fi

# 3. Hardcoded font sizes
echo ""
echo "🔢 Checking for hardcoded font sizes..."
SIZE_HITS=$(grep -rn "QFont(" "$SRC_DIR/gui" --include="*.py" 2>/dev/null | grep -v "theme.py" | grep -E ", [0-9]+[,)]" | grep -v "FONT_SIZES")
if [ -n "$SIZE_HITS" ]; then
    echo "❌ Hardcoded font sizes found:"
    echo "$SIZE_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(count_lines "$SIZE_HITS")))
else
    echo "✅ No hardcoded font sizes"
fi

# 4. Inline slider stylesheets
echo ""
echo "🎚️ Checking for inline slider stylesheets..."
SLIDER_HITS=$(grep -rn "QSlider::groove\|QSlider::handle" "$SRC_DIR/gui" --include="*.py" 2>/dev/null | grep -v "theme.py")
if [ -n "$SLIDER_HITS" ]; then
    echo "❌ Inline slider styles found (use slider_style()):"
    echo "$SLIDER_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(count_lines "$SLIDER_HITS")))
else
    echo "✅ No inline slider styles"
fi

# 5. Hardcoded OSC paths (should use OSC_PATHS)
echo ""
echo "📡 Checking for hardcoded OSC paths..."
OSC_HITS=$(grep -rn "'/noise/" "$SRC_DIR" --include="*.py" 2>/dev/null | grep -v "config/__init__.py" | grep -v "OSC_PATHS\[" | grep -v "OSC_PATHS.get")
if [ -n "$OSC_HITS" ]; then
    echo "❌ Hardcoded OSC paths found (use OSC_PATHS):"
    echo "$OSC_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(count_lines "$OSC_HITS")))
else
    echo "✅ No hardcoded OSC paths"
fi

# 6. Hardcoded MIDI channel numbers
echo ""
echo "🎹 Checking for hardcoded MIDI channels..."
MIDI_HITS=$(grep -rn "range(1, 17)\|range(16)" "$SRC_DIR/gui" --include="*.py" 2>/dev/null | grep -v "config\|MIDI_CHANNELS")
if [ -n "$MIDI_HITS" ]; then
    echo "⚠️  Possible hardcoded MIDI channel logic:"
    echo "$MIDI_HITS" | sed 's/^/   /' | head -5
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ No obvious hardcoded MIDI channels"
fi

# 7. Hardcoded clock rates
echo ""
echo "⏱️ Checking for hardcoded clock rates..."
CLOCK_HITS=$(grep -rn '"/32"\|"/16"\|"/8"\|"/4"\|"/2"\|"CLK"\|"x2"\|"x4"\|"x8"\|"x16"\|"x32"' "$SRC_DIR/gui" --include="*.py" 2>/dev/null | grep -v "config/__init__.py\|CLOCK_RATES")
if [ -n "$CLOCK_HITS" ]; then
    echo "⚠️  Possible hardcoded clock rates:"
    echo "$CLOCK_HITS" | sed 's/^/   /' | head -5
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ No hardcoded clock rates"
fi

# 8. Magic numbers in widget sizes
echo ""
echo "📐 Checking for hardcoded widget sizes..."
SIZES_HITS=$(grep -rn "setFixedWidth\|setFixedHeight\|setFixedSize\|setMinimumSize" "$SRC_DIR/gui" --include="*.py" 2>/dev/null | grep -E "\([0-9]+\)|\([0-9]+, [0-9]+\)" | grep -v "SIZES\[" | grep -v "theme.py")
if [ -n "$SIZES_HITS" ]; then
    echo "⚠️  Hardcoded sizes (consider SIZES config):"
    echo "$SIZES_HITS" | sed 's/^/   /' | head -10
    COUNT=$(count_lines "$SIZES_HITS")
    if [ "$COUNT" -gt 10 ]; then
        echo "   ... and $((COUNT - 10)) more"
    fi
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ No hardcoded widget sizes"
fi

# ============================================
# SUPERCOLLIDER CHECKS
# ============================================
echo ""
echo ""
echo "🎵 SUPERCOLLIDER CHECKS"
echo "-----------------------"

# 9. Check generators use ~envVCA helper
echo ""
echo "🔊 Checking generators use ~envVCA helper..."
GEN_DIR="$SC_DIR/generators"
MISSING_ENVVCA=""
for f in "$GEN_DIR"/*.scd; do
    if ! grep -q "~envVCA" "$f" 2>/dev/null; then
        MISSING_ENVVCA="$MISSING_ENVVCA   $(basename $f)\n"
    fi
done
if [ -n "$MISSING_ENVVCA" ]; then
    echo "❌ Generators NOT using ~envVCA helper:"
    echo -e "$MISSING_ENVVCA"
    ISSUES=$((ISSUES + 1))
else
    echo "✅ All generators use ~envVCA helper"
fi

# 10. Check generators use ~multiFilter helper
echo ""
echo "🎛️ Checking generators use ~multiFilter helper..."
MISSING_FILTER=""
for f in "$GEN_DIR"/*.scd; do
    if ! grep -q "~multiFilter" "$f" 2>/dev/null; then
        MISSING_FILTER="$MISSING_FILTER   $(basename $f)\n"
    fi
done
if [ -n "$MISSING_FILTER" ]; then
    echo "❌ Generators NOT using ~multiFilter helper:"
    echo -e "$MISSING_FILTER"
    ISSUES=$((ISSUES + 1))
else
    echo "✅ All generators use ~multiFilter helper"
fi

# 11. Check for old envEnabled pattern (should be envSource)
echo ""
echo "🔄 Checking for deprecated envEnabled pattern..."
OLD_ENV_HITS=$(grep -rn "envEnabled\s*>" "$SC_DIR/generators" --include="*.scd" 2>/dev/null | grep -v "envEnabledBus")
if [ -n "$OLD_ENV_HITS" ]; then
    echo "❌ Old envEnabled pattern found (use envSource):"
    echo "$OLD_ENV_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(count_lines "$OLD_ENV_HITS")))
else
    echo "✅ No deprecated envEnabled usage"
fi

# 12. Check for duplicated envelope code (should use helper)
echo ""
echo "📋 Checking for duplicated envelope code..."
DUP_ENV_HITS=$(grep -rn "Select.ar(envSource" "$SC_DIR/generators" --include="*.scd" 2>/dev/null)
if [ -n "$DUP_ENV_HITS" ]; then
    echo "❌ Inline envelope logic found (should use ~envVCA):"
    echo "$DUP_ENV_HITS" | sed 's/^/   /' | head -5
    COUNT=$(count_lines "$DUP_ENV_HITS")
    if [ "$COUNT" -gt 5 ]; then
        echo "   ... and $((COUNT - 5)) more"
    fi
    ISSUES=$((ISSUES + 1))
else
    echo "✅ No duplicated envelope code"
fi

# 13. Hardcoded array sizes that should match config
echo ""
echo "🔢 Checking for magic numbers in SC..."
MAGIC_HITS=$(grep -rn "In.ar(midiTrigBus, 8)\|In.ar(clockTrigBus, 13)" "$SC_DIR/generators" --include="*.scd" 2>/dev/null)
if [ -n "$MAGIC_HITS" ]; then
    echo "⚠️  Hardcoded bus sizes in generators (should be in helper):"
    echo "$MAGIC_HITS" | sed 's/^/   /' | head -5
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ No hardcoded bus sizes in generators"
fi

# 14. Check OSC path consistency between SC and Python
echo ""
echo "📡 Checking OSC path consistency..."
SC_PATHS=$(grep -roh "'/noise/[^']*'" "$SC_DIR" --include="*.scd" 2>/dev/null | sort -u | tr -d "'")
PY_PATHS=$(grep -o "'/noise/[^']*'" "$CONFIG_FILE" 2>/dev/null | sort -u | tr -d "'")

MISSING=""
for path in $SC_PATHS; do
    if ! echo "$PY_PATHS" | grep -q "^${path}$"; then
        MISSING="$MISSING   $path\n"
    fi
done

if [ -n "$MISSING" ]; then
    echo "⚠️  OSC paths in SC not in Python OSC_PATHS:"
    echo -e "$MISSING"
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ OSC paths consistent"
fi

# ============================================
# CONFIG COMPLETENESS (Dynamic)
# ============================================
echo ""
echo ""
echo "📋 CONFIG INVENTORY"
echo "-------------------"

if [ -f "$CONFIG_FILE" ]; then
    echo ""
    echo "Constants defined in config/__init__.py:"
    
    # Count generators in cycle
    GEN_COUNT=$(grep -A100 "^GENERATOR_CYCLE" "$CONFIG_FILE" | grep -m1 "^\]" -B100 | grep -c '"')
    echo "  • GENERATOR_CYCLE: $GEN_COUNT generators"
    
    # Count clock rates
    CLOCK_COUNT=$(grep "^CLOCK_RATES" "$CONFIG_FILE" | grep -o '"[^"]*"' | wc -l | tr -d ' ')
    echo "  • CLOCK_RATES: $CLOCK_COUNT rates"
    
    # Count filter types
    FILTER_COUNT=$(grep "^FILTER_TYPES" "$CONFIG_FILE" | grep -o '"[^"]*"' | wc -l | tr -d ' ')
    echo "  • FILTER_TYPES: $FILTER_COUNT types"
    
    # Count ENV sources
    ENV_COUNT=$(grep "^ENV_SOURCES" "$CONFIG_FILE" | grep -o '"[^"]*"' | wc -l | tr -d ' ')
    echo "  • ENV_SOURCES: $ENV_COUNT sources"
    
    # Count OSC paths
    OSC_COUNT=$(grep -c "'/noise/" "$CONFIG_FILE")
    echo "  • OSC_PATHS: $OSC_COUNT paths"
    
    # Count generator params
    PARAM_COUNT=$(grep -c "'key':" "$CONFIG_FILE")
    echo "  • GENERATOR_PARAMS: $PARAM_COUNT params"
    
    # Count SC generators
    SC_GEN_COUNT=$(ls -1 "$SC_DIR/generators"/*.scd 2>/dev/null | wc -l | tr -d ' ')
    echo "  • SC Generators: $SC_GEN_COUNT files"
else
    echo "⚠️  Config file not found at $CONFIG_FILE"
fi

# ============================================
# HELPERS INVENTORY
# ============================================
echo ""
echo ""
echo "🔧 HELPERS INVENTORY"
echo "--------------------"

HELPERS_FILE="$SC_DIR/core/helpers.scd"
if [ -f "$HELPERS_FILE" ]; then
    echo "Signal processing helpers in helpers.scd:"
    grep -o "~[a-zA-Z]*\s*=" "$HELPERS_FILE" | sed 's/\s*=$//' | sort -u | while read helper; do
        USAGE=$(grep -rl "$helper\." "$SC_DIR/generators" --include="*.scd" 2>/dev/null | wc -l | tr -d ' ')
        echo "  • $helper - used in $USAGE generators"
    done
else
    echo "⚠️  Helpers file not found at $HELPERS_FILE"
fi

# ============================================
# SUMMARY
# ============================================
echo ""
echo ""
echo "================================"
echo "SUMMARY"
echo "================================"

# Calculate compliance percentage
TOTAL_CHECKS=12
PASSED=$((TOTAL_CHECKS - ISSUES))
if [ $TOTAL_CHECKS -gt 0 ]; then
    PERCENT=$((PASSED * 100 / TOTAL_CHECKS))
else
    PERCENT=100
fi

if [ $ISSUES -eq 0 ]; then
    echo "✅ No critical SSOT violations found"
else
    echo "❌ Found $ISSUES critical violation(s)"
fi

if [ $WARNINGS -gt 0 ]; then
    echo "⚠️  Found $WARNINGS warning(s) to review"
fi

echo ""
echo "SSOT Compliance: ${PERCENT}% ($PASSED/$TOTAL_CHECKS checks passed)"
echo ""
echo "Legend:"
echo "  ❌ Critical - should be fixed"
echo "  ⚠️  Warning - review and fix if appropriate"
echo "  ✅ Pass"

# Output for automation (if --json flag)
if [ "$1" = "--json" ]; then
    echo ""
    echo "JSON_OUTPUT:{\"percent\":$PERCENT,\"issues\":$ISSUES,\"warnings\":$WARNINGS}"
fi

# Exit with error code if issues found
exit $ISSUES
