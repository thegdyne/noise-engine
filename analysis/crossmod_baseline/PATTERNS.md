# Crossmod GUI Patterns (from mod_matrix baseline)

> Derived from: mod_matrix_window.py, mod_matrix_cell.py, mod_connection_popup.py
> For: crossmod_matrix_window.py, crossmod_matrix_cell.py, crossmod_connection_popup.py

---

## Purpose

The mod_matrix files implement a routing matrix for LFO/Sloth → Generator parameter modulation.
Crossmod adapts this for Generator → Generator parameter modulation (audio-rate cross-modulation).

---

## Key Patterns to Preserve

### Window Structure (from mod_matrix_window.py)

1. **Header layout**: Title left, ENGINE button right, CLEAR button after ENGINE
2. **ScrollArea containing grid**: `QScrollArea` with `QGridLayout` inside
3. **Column headers**: Two-line format `G{n}\n{PARAM}` in fixed 28x36 cells
4. **Row headers**: Fixed width 50px, right-aligned with padding
5. **Generator tinting**: Odd generators `#1a1a1a`, even `#141414`
6. **Vertical separators**: 3px wide between generator groups
7. **Horizontal separators**: 2px high between row groups
8. **Legend at bottom**: Color dots + keyboard shortcuts
9. **Window geometry persistence**: `QSettings("NoiseEngine", "...")`

### Cell Widget (from mod_matrix_cell.py)

1. **Fixed size**: 28x24 pixels
2. **Signals**: `clicked` (left), `right_clicked` (right)
3. **Visual states**:
   - Empty: background tint only
   - Hovered: `#333333` fill + subtle dot
   - Selected: `#444466` fill + `#8888ff` border (2px)
   - Connected: filled circle, radius 3-10 based on amount
4. **No focus policy**: `Qt.NoFocus` (matrix window handles keyboard)
5. **Mouse tracking enabled**: for hover state

### Keyboard Navigation (from mod_matrix_window.py)

1. **Arrow keys**: Move selection (with timer for held keys)
2. **Modifiers**: Shift = 5 cells, Ctrl = 10 cols / 4 rows
3. **Space**: Toggle connection
4. **Delete/Backspace**: Remove connection
5. **D**: Open popup
6. **1-9**: Set amount 10%-90%
7. **0**: Set amount 100%
8. **Escape**: Clear selection
9. **Navigation timer**: 100ms repeat for held arrows

### State Management Pattern

1. **Separate state class**: `ModRoutingState` holds connections, emits signals
2. **Signal-driven updates**: Window connects to state signals, syncs cells
3. **Signals**: `connection_added`, `connection_removed`, `connection_changed`, `all_cleared`

### Popup Pattern (from mod_connection_popup.py)

1. **Header**: `{source} → {target}` format
2. **Sliders**: Amount (0-100%), Offset (-100% to +100%)
3. **Remove button**: Red styled, at bottom
4. **Real-time updates**: Changes emit signal immediately
5. **Positioned near cell**: `cell.mapToGlobal()` + offset

---

## Required Elements for Crossmod

### Classes

| Class | Based On | Key Changes |
|-------|----------|-------------|
| `CrossmodMatrixWindow` | `ModMatrixWindow` | 8 rows, row checkboxes, 8-color scheme |
| `CrossmodMatrixCell` | `ModMatrixCell` | 8 source colors, invert visual |
| `CrossmodRoutingState` | `ModRoutingState` | `FollowerState`, invert field |
| `CrossmodOSCBridge` | (new) | `/noise/crossmod/*` endpoints |
| `CrossmodConnectionPopup` | `ModConnectionPopup` | Invert checkbox |

### Methods (CrossmodMatrixWindow)

- `__init__(routing_state, parent)`
- `_setup_ui()` - adapted grid (8 rows, row checkboxes)
- `_build_column_headers(layout)` - same pattern
- `_build_rows(layout)` - 8 rows with enable checkboxes
- `_build_legend()` - 8-color legend + invert indicator
- `_on_cell_clicked(source, target, param)` - toggle logic
- `_on_cell_right_clicked(source, target, param)` - popup
- `keyPressEvent(event)` - add I for invert, Shift+Space
- `update_follower_enabled(source, enabled)` - new
- `sync_from_state()` - restore from state

### Methods (CrossmodMatrixCell)

- `__init__(source_gen, target_gen, target_param)`
- `set_connection(connected, amount, invert=False)`
- `set_source_gen(gen)` - for color
- `set_selected(selected)`
- `paintEvent(event)` - add invert visual (notch/half-moon)

### Constants

```python
# 8 source colors (per spec)
SOURCE_COLORS = {
    1: '#ff4444',  # Red
    2: '#ff8800',  # Orange
    3: '#ffcc00',  # Yellow
    4: '#44ff44',  # Green
    5: '#44ffff',  # Cyan
    6: '#4488ff',  # Blue
    7: '#aa44ff',  # Purple
    8: '#ff44aa',  # Pink
}

# Grid dimensions
NUM_SOURCE_GENS = 8
NUM_TARGET_GENS = 8
PARAMS_PER_GEN = 10
TOTAL_ROWS = 8
TOTAL_COLS = 80
```

---

## Allowed Deviations

1. **Row count**: 8 instead of 16 (8 generators vs 16 mod buses)
2. **Row headers**: `GEN {n}` with enable checkbox instead of `M{n}.{output}`
3. **Source colors**: 8-color scheme instead of 3-color (LFO/Sloth/Empty)
4. **Self-modulation**: Diagonal cells enabled (not blocked)
5. **Invert toggle**: New visual state + Shift+click + I key
6. **Follower enable**: Row checkbox controls `/noise/crossmod/enabled`
7. **OSC endpoints**: `/noise/crossmod/*` instead of `/noise/mod/*`
8. **Window title**: "CROSSMOD MATRIX" instead of "MOD ROUTING MATRIX"
9. **Shortcut**: Ctrl+X instead of Ctrl+M (Ctrl+M returns to engine)
10. **QSettings key**: "CrossmodMatrix" instead of "ModMatrix"

---

## OSC Integration (from spec)

```python
# Route message (positional args)
"/noise/crossmod/route" [source, target, param, depth, amount, offset, polarity, invert]

# Unroute message
"/noise/crossmod/unroute" [source, target, param]

# Follower enable
"/noise/crossmod/enabled" [source, 0_or_1]

# Clear all
"/noise/crossmod/clear"
```

**v1 Fixed values**: `depth=1.0`, `polarity=0` (bipolar)

---

## Dependencies

```python
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QPushButton, QCheckBox, QShortcut
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter, QKeySequence

from .theme import COLORS, FONT_FAMILY, FONT_SIZES, MONO_FONT
```

---

## File Structure

```
src/gui/
├── crossmod_matrix_window.py    # Main window
├── crossmod_matrix_cell.py      # Cell widget  
├── crossmod_routing_state.py    # State + signals
├── crossmod_osc_bridge.py       # OSC sync
└── crossmod_connection_popup.py # Popup dialog
```
