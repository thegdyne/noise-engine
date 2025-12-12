#!/bin/bash
# Add debug output to key functions for troubleshooting
# Usage: ./tools/debug_add.sh
# Remove with: ./tools/debug_remove.sh

REPO_DIR=~/repos/noise-engine
BACKUP_DIR="$REPO_DIR/.debug_backup"

echo "🔧 Adding debug output..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# ============================================
# PYTHON DEBUG POINTS
# ============================================

# 1. main_frame.py - on_generator_changed
FILE="$REPO_DIR/src/gui/main_frame.py"
if ! grep -q "DEBUG_MARKER" "$FILE" 2>/dev/null; then
    cp "$FILE" "$BACKUP_DIR/main_frame.py.bak"
    sed -i '' 's/def on_generator_changed(self, slot_id, new_type):/def on_generator_changed(self, slot_id, new_type):  # DEBUG_MARKER\
        print(f"DEBUG [on_generator_changed]: slot={slot_id}, type={new_type}, osc_connected={self.osc_connected}")/' "$FILE"
    echo "  ✓ Added debug to main_frame.py:on_generator_changed"
fi

# 2. main_frame.py - toggle_connection
if ! grep -q "DEBUG_MARKER.*toggle_connection" "$FILE" 2>/dev/null; then
    sed -i '' 's/def toggle_connection(self):/def toggle_connection(self):  # DEBUG_MARKER_toggle_connection\
        print(f"DEBUG [toggle_connection]: osc_connected={self.osc_connected}")/' "$FILE"
    echo "  ✓ Added debug to main_frame.py:toggle_connection"
fi

# 3. generator_slot.py - generator type emission
FILE="$REPO_DIR/src/gui/generator_slot.py"
if ! grep -q "DEBUG_MARKER" "$FILE" 2>/dev/null; then
    cp "$FILE" "$BACKUP_DIR/generator_slot.py.bak"
    # Add debug before generator_changed.emit
    sed -i '' 's/self.generator_changed.emit(self.slot_id, gen_type)/print(f"DEBUG [generator_slot]: emitting generator_changed slot={self.slot_id}, type={gen_type}")  # DEBUG_MARKER\
        self.generator_changed.emit(self.slot_id, gen_type)/' "$FILE"
    echo "  ✓ Added debug to generator_slot.py:generator_changed.emit"
fi

# ============================================
# SUPERCOLLIDER DEBUG
# ============================================

# Add OSC debug listener to scratch.scd
SCRATCH="$REPO_DIR/supercollider/scratch.scd"
if ! grep -q "DEBUG_OSC_LISTENER" "$SCRATCH" 2>/dev/null; then
    cp "$SCRATCH" "$BACKUP_DIR/scratch.scd.bak"
    cat >> "$SCRATCH" << 'SCEOF'

// === DEBUG_OSC_LISTENER ===
// Run this block to enable OSC debugging
(
"DEBUG: Adding OSC listener for /noise/start_generator".postln;
OSCdef(\debugStartGen, { |msg|
    "=== OSC RECEIVED: /noise/start_generator ===".postln;
    ("  slot: " ++ msg[1]).postln;
    ("  synth: " ++ msg[2]).postln;
}, '/noise/start_generator');

"DEBUG: Adding OSC listener for /noise/stop_generator".postln;
OSCdef(\debugStopGen, { |msg|
    "=== OSC RECEIVED: /noise/stop_generator ===".postln;
    ("  slot: " ++ msg[1]).postln;
}, '/noise/stop_generator');

"✓ Debug OSC listeners active. Run OSCdef.freeAll to remove.".postln;
)
// === END DEBUG_OSC_LISTENER ===
SCEOF
    echo "  ✓ Added debug OSC listeners to scratch.scd"
fi

echo ""
echo "================================"
echo "✅ Debug output added"
echo ""
echo "Python debug: Look for 'DEBUG [...]' in terminal"
echo "SC debug: Run the DEBUG_OSC_LISTENER block in scratch.scd"
echo ""
echo "To remove: ./tools/debug_remove.sh"
echo "================================"
