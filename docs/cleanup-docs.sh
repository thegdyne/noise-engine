#!/bin/bash
# Reorganize docs - run from ~/repos/noise-engine
# Creates archive/ and ideas/ folders, moves and deletes files

set -e
cd ~/repos/noise-engine/docs

echo "=== Doc Cleanup Script ==="
echo ""

# Create directories
mkdir -p archive
mkdir -p ideas

echo "📁 Created archive/ and ideas/ directories"

# =============================================================================
# MOVE TO ARCHIVE (completed features, reference only)
# =============================================================================
echo ""
echo "📦 Moving completed specs to archive/..."

mv -v PACK_SYSTEM_SPEC.md archive/ 2>/dev/null || true
mv -v PACK_SPEC.md archive/ 2>/dev/null || true
mv -v PACK_LOADER_SPEC.md archive/ 2>/dev/null || true
mv -v MASTER_COMPRESSOR.md archive/ 2>/dev/null || true
mv -v MASTER_EQ.md archive/ 2>/dev/null || true
mv -v MASTER_LIMITER.md archive/ 2>/dev/null || true
mv -v MASTER_OUT.md archive/ 2>/dev/null || true
mv -v MOD_SOURCES.md archive/ 2>/dev/null || true
mv -v MOD_SOURCES_CHECKLIST.md archive/ 2>/dev/null || true
mv -v MOD_SOURCES_PHASES.md archive/ 2>/dev/null || true
mv -v MOD_MATRIX_BACKLOG.md archive/ 2>/dev/null || true
mv -v MOD_MATRIX_ROLLOUT.md archive/ 2>/dev/null || true
mv -v MODULATION_SYSTEM.md archive/ 2>/dev/null || true
mv -v FEATURE_LFO_QUADRATURE.md archive/ 2>/dev/null || true
mv -v FADER_POPUPS.md archive/ 2>/dev/null || true
mv -v CHANNEL_EQ.md archive/ 2>/dev/null || true
mv -v SKIN_PHASES.md archive/ 2>/dev/null || true
mv -v RELATIVE_MOD_ROLLOUT.md archive/ 2>/dev/null || true
mv -v GENERATOR_ENVELOPE_COMPLIANCE.md archive/ 2>/dev/null || true
mv -v FXBUS.md archive/ 2>/dev/null || true
mv -v WIDGET_NAMING.md archive/ 2>/dev/null || true
mv -v LAYOUT_DEBUGGING.md archive/ 2>/dev/null || true
mv -v WHY_LAYOUT_DEBUG.md archive/ 2>/dev/null || true
mv -v layout-tuning.md archive/ 2>/dev/null || true
mv -v REFERENCES.md archive/ 2>/dev/null || true
mv -v DUAL_AI_WORKFLOW.md archive/ 2>/dev/null || true
mv -v PROJECT_STRATEGY.md archive/ 2>/dev/null || true
mv -v BLUEPRINT.md archive/ 2>/dev/null || true

# =============================================================================
# MOVE TO IDEAS (future dreams, not committed)
# =============================================================================
echo ""
echo "💡 Moving future ideas to ideas/..."

mv -v FUTURE_IDEAS.md ideas/ 2>/dev/null || true
mv -v IDEAS.md ideas/ 2>/dev/null || true
mv -v ROADMAP_IDEAS.md ideas/ 2>/dev/null || true
mv -v INTEGR8TOR.md ideas/ 2>/dev/null || true
mv -v KEYBOARD_MODE.md ideas/ 2>/dev/null || true
mv -v GENERATOR_POWER.md ideas/ 2>/dev/null || true
mv -v SERVER_CONTROLS.md ideas/ 2>/dev/null || true
mv -v PIN_MATRIX_DESIGN.md ideas/ 2>/dev/null || true

# =============================================================================
# DELETE (ephemeral, merged, or redundant)
# =============================================================================
echo ""
echo "🗑️  Deleting ephemeral and merged files..."

rm -v SESSION_SUMMARY_*.md 2>/dev/null || true
rm -v DISCORD_UPDATE_*.md 2>/dev/null || true
rm -v DISCORD.md 2>/dev/null || true
rm -v TODO.md 2>/dev/null || true
rm -v TECH_DEBT.md 2>/dev/null || true
rm -v NEXT_RELEASE.md 2>/dev/null || true
rm -v ALIASES.md 2>/dev/null || true
rm -v SHELL_ALIASES.md 2>/dev/null || true

# =============================================================================
# MOVE DEMO HTML FILES
# =============================================================================
echo ""
echo "🎨 Moving demo HTML files to demos/..."

mkdir -p demos
mv -v demo-*.html demos/ 2>/dev/null || true
mv -v mod-matrix-process.html demos/ 2>/dev/null || true
mv -v process.html demos/ 2>/dev/null || true
mv -v index.html demos/ 2>/dev/null || true

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo "=== Summary ==="
echo ""
echo "Root docs (what remains):"
ls -1 *.md 2>/dev/null || echo "  (none)"
echo ""
echo "Archive:"
ls -1 archive/*.md 2>/dev/null | wc -l | xargs echo "  files:"
echo ""
echo "Ideas:"
ls -1 ideas/*.md 2>/dev/null | wc -l | xargs echo "  files:"
echo ""
echo "Demos:"
ls -1 demos/*.html 2>/dev/null | wc -l | xargs echo "  files:"
echo ""
echo "✅ Done! Now copy the new BACKLOG.md from Downloads."
