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

# 9. Hardcoded array sizes that should match config
echo ""
echo "🔢 Checking for magic numbers in SC..."
MAGIC_HITS=$(grep -rn "! 8\|! 13\|Array.fill(8\|Array.fill(13" "$SC_DIR" --include="*.scd" 2>/dev/null)
if [ -n "$MAGIC_HITS" ]; then
    echo "⚠️  Magic numbers found (verify match config):"
    echo "$MAGIC_HITS" | sed 's/^/   /' | head -10
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ No suspicious magic numbers"
fi

# 10. Check OSC path consistency between SC and Python
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
else
    echo "⚠️  Config file not found at $CONFIG_FILE"
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
TOTAL_CHECKS=8
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
exit $ISSUES"
