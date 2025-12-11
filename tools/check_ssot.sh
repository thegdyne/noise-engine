#!/bin/bash
# Single Source of Truth checker
# Finds common violations of centralized config/theme

REPO_DIR=~/repos/noise-engine
SRC_DIR="$REPO_DIR/src"
ISSUES=0

echo "🔍 Single Source of Truth Check"
echo "================================"
echo ""

# 1. Hardcoded fonts in QFont() calls
echo "📝 Checking for hardcoded fonts..."
FONT_HITS=$(grep -rn "QFont(" "$SRC_DIR/gui" --include="*.py" | grep -v "FONT_FAMILY\|MONO_FONT" | grep -v "theme.py" | grep "'[A-Za-z]")
if [ -n "$FONT_HITS" ]; then
    echo "❌ Hardcoded fonts found:"
    echo "$FONT_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(echo "$FONT_HITS" | wc -l)))
    echo ""
else
    echo "✅ No hardcoded fonts"
fi

# 2. Hardcoded hex colors outside theme.py
echo ""
echo "🎨 Checking for hardcoded colors..."
COLOR_HITS=$(grep -rn "#[0-9a-fA-F]\{3,6\}" "$SRC_DIR/gui" --include="*.py" | grep -v "theme.py" | grep -v "COLORS\[")
if [ -n "$COLOR_HITS" ]; then
    echo "❌ Hardcoded colors found:"
    echo "$COLOR_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(echo "$COLOR_HITS" | wc -l)))
    echo ""
else
    echo "✅ No hardcoded colors"
fi

# 3. Hardcoded font sizes (numbers after QFont)
echo ""
echo "🔢 Checking for hardcoded font sizes..."
SIZE_HITS=$(grep -rn "QFont(" "$SRC_DIR/gui" --include="*.py" | grep -v "theme.py" | grep -E ", [0-9]+[,)]" | grep -v "FONT_SIZES")
if [ -n "$SIZE_HITS" ]; then
    echo "❌ Hardcoded font sizes found:"
    echo "$SIZE_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(echo "$SIZE_HITS" | wc -l)))
    echo ""
else
    echo "✅ No hardcoded font sizes"
fi

# 4. Inline slider stylesheets (should use slider_style())
echo ""
echo "🎚️ Checking for inline slider stylesheets..."
SLIDER_HITS=$(grep -rn "QSlider::groove\|QSlider::handle" "$SRC_DIR/gui" --include="*.py" | grep -v "theme.py")
if [ -n "$SLIDER_HITS" ]; then
    echo "❌ Inline slider styles found (use slider_style()):"
    echo "$SLIDER_HITS" | sed 's/^/   /'
    ISSUES=$((ISSUES + $(echo "$SLIDER_HITS" | wc -l)))
    echo ""
else
    echo "✅ No inline slider styles"
fi

# 5. Hardcoded effect types outside config
echo ""
echo "🔌 Checking for hardcoded effect types..."
EFFECT_HITS=$(grep -rn '"Fidelity"\|"Empty"' "$SRC_DIR/gui" --include="*.py" | grep -v "effect_slot.py.*set_effect_type\|effect_slot.py.*effect_type ==")
if [ -n "$EFFECT_HITS" ]; then
    echo "⚠️  Hardcoded effect types (consider EFFECTS config):"
    echo "$EFFECT_HITS" | sed 's/^/   /'
    echo ""
fi

# 6. Magic numbers in widget sizes
echo ""
echo "📐 Checking for hardcoded widget sizes..."
SIZES_HITS=$(grep -rn "setFixedWidth\|setFixedHeight\|setFixedSize\|setMinimumSize\|setMaximumWidth" "$SRC_DIR/gui" --include="*.py" | grep -E "\([0-9]+\)|\([0-9]+, [0-9]+\)" | grep -v "SIZES\[" | grep -v "theme.py")
if [ -n "$SIZES_HITS" ]; then
    echo "⚠️  Hardcoded sizes (consider SIZES config):"
    echo "$SIZES_HITS" | sed 's/^/   /' | head -15
    COUNT=$(echo "$SIZES_HITS" | wc -l)
    if [ "$COUNT" -gt 15 ]; then
        echo "   ... and $((COUNT - 15)) more"
    fi
    echo ""
fi

# Summary
echo ""
echo "================================"
if [ $ISSUES -eq 0 ]; then
    echo "✅ No critical SSOT violations found"
else
    echo "❌ Found $ISSUES critical violation(s)"
fi
echo ""
echo "Note: ⚠️ warnings are suggestions, not errors"
