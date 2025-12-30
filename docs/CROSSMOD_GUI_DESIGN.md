# Crossmod GUI Design Spec v1.2

**Status:** Draft  
**Reference Artifact:** `mod_matrix_window.py`, `mod_matrix_cell.py`, `mod_connection_popup.py`  
**Backend Contract:** `contracts/crossmod.yaml` (frozen, v1.0.0)  
**Date:** 2025-12-30

---

## Overview

A matrix window for routing generator outputs to modulate other generators' parameters.
Follows the established mod matrix pattern with adaptations for crossmod.

**Key difference from mod matrix:** Sources are the 8 generators (not LFO/Sloth), and self-modulation (feedback) is allowed.

---

## Layout

### Matrix Dimensions

| Axis | Count | Items |
|------|-------|-------|
| Rows | 8 | Source generators (Gen 1-8) |
| Columns | 80 | Target generators × params (8 × 10) |
| Cells | 640 | All routing points (including self-mod diagonal) |

### Column Headers

Same as mod matrix - generator + param labels:
```
G1 CUT | G1 RES | G1 FRQ | ... | G8 P5
```

### Row Headers

Source generator labels with **enable checkbox**:
```
[✓] GEN 1  |  ●  ●  ○  ...
[✓] GEN 2  |  ○  ●  ●  ...
[ ] GEN 3  |  ○  ○  ○  ...   ← follower disabled, all routes inactive
[✓] GEN 4  |  ●  ○  ○  ...
...
```

The checkbox controls the envelope follower for that source:
- **Checked:** Follower active, routes from this source work
- **Unchecked:** Follower disabled, saves CPU, all routes from this source output 0

### Self-Modulation (Diagonal)

**Allowed.** Cells where source == target work like any other cell.

Self-modulation is permitted and treated the same as any other route; UI does not gate/disable the diagonal.

Self-mod creates feedback loops (Gen 3 audio → Gen 3 cutoff → affects Gen 3 audio → ...).

Musical uses:
- Low amount: Subtle "breathing", organic movement
- With invert: Self-ducking/pumping
- High amount: Chaotic feedback effects

User controls feedback intensity via amount slider. Start low.

---

## Visual Design

### Source Colors (8 generators)

Row colors are local UI constants (theme integration deferred).

```python
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
```

### Cell States

| State | Visual | Description |
|-------|--------|-------------|
| Empty | Background only | No connection |
| Connected | Filled circle | Active route, size = amount |
| Connected + Inverted | Filled circle + notch/half-moon | Inverted route (for ducking) |
| Hovered | Subtle highlight | Mouse over |
| Selected | Blue border | Keyboard focus |

### Generator Tinting

Alternating column backgrounds by target generator (matches mod matrix):
- Odd generators (1,3,5,7): `#1a1a1a`
- Even generators (2,4,6,8): `#141414`

---

## Interaction

### Mouse

| Action | Behavior |
|--------|----------|
| Left click | Toggle connection (see rules below) |
| Shift + Left click | Toggle connection with invert flipped |
| Right click | Open connection popup |
| Click row checkbox | Toggle follower enabled for that source |

**Click toggle rules:**

- **Left click (toggle ON, no prior state):** Set `amount=0.5`, `offset=0.0`, `invert=0`
- **Left click (toggle ON, prior state exists):** Restore previous `amount/offset/invert`
- **Left click (toggle OFF):** Store current state as prior, send `/unroute`
- **Shift+click (toggle ON):** Same as above, but flip `invert`
- **Shift+click (already ON):** Toggle `invert` on existing connection

### Keyboard

| Key | Action |
|-----|--------|
| Arrow keys | Navigate cells |
| Shift + Arrow | Jump 5 cells |
| Ctrl + Arrow | Jump 10 cells (rows: 4) |
| Space | Toggle connection |
| Shift + Space | Toggle connection with invert |
| Delete/Backspace | Remove connection |
| D | Open connection popup |
| I | Toggle invert on existing connection |
| 1-9 | Set amount 10%-90% |
| 0 | Set amount 100% |
| Escape | Deselect |

---

## Connection Popup

Right-click (or D key) opens popup for selected cell. Based on `mod_connection_popup.py`:

```
┌─────────────────────────────┐
│  GEN 3 → G5 CUT [INV]       │  Header (source → target) [INV] shown when inverted
├─────────────────────────────┤
│  Amount   [━━━━━●━━━] 50%   │  Slider 0-100%
│  Offset   [━━━━━━━━●] 0%    │  Slider -100% to +100%
│  Invert   [✓]               │  Checkbox
├─────────────────────────────┤
│         [Remove]            │  Red button
└─────────────────────────────┘
```

Header format: `GEN <src> → G<tgt> <PARAM>` or `GEN <src> → G<tgt> <PARAM> [INV]` when inverted.

Changes update SC in real-time via OSC.

---

## Backend Integration

### OSC Endpoints

From `crossmod_osc.scd` backend:

```python
# Create/update route
osc.send("/noise/crossmod/route", [
    source,      # 1-8 (source generator)
    target,      # 1-8 (target generator)
    param,       # "cutoff", "resonance", "frequency", "attack", "decay", "p1"-"p5"
    depth,       # 0.0-1.0 (range width)
    amount,      # 0.0-1.0 (VCA level)
    offset,      # -1.0 to 1.0 (shifts mod range)
    polarity,    # 0=bipolar, 1=uni+, 2=uni-
    invert       # 0 or 1 (flip direction)
])

# Remove route
osc.send("/noise/crossmod/unroute", [source, target, param])

# Follower controls (per source)
osc.send("/noise/crossmod/enabled", [source, 0_or_1])
osc.send("/noise/crossmod/attack", [source, seconds])   # v2 only
osc.send("/noise/crossmod/release", [source, seconds])  # v2 only

# Clear all routes
osc.send("/noise/crossmod/clear")

# Examples:
# /noise/crossmod/enabled [3, 1]      # Enable follower for Gen 3
# /noise/crossmod/attack [3, 0.01]    # v2: Set Gen 3 attack to 10ms
# /noise/crossmod/release [3, 0.10]   # v2: Set Gen 3 release to 100ms
```

**Note:** All crossmod OSC endpoints use positional arguments; the slot index is always argument 0.
```

### Parameter Mapping (v1)

| UI Control | Backend Field | v1 Default |
|------------|---------------|------------|
| Amount slider | `amount` | 0.5 |
| Offset slider | `offset` | 0.0 |
| Invert checkbox | `invert` | 0 |
| (fixed) | `depth` | 1.0 |
| (fixed) | `polarity` | 0 (bipolar) |
| Row checkbox | `enabled` | 1 |

### State Management

```python
class CrossmodConnection:
    source_gen: int      # 1-8
    target_gen: int      # 1-8
    target_param: str    # 'cutoff', 'resonance', etc.
    amount: float        # 0.0 - 1.0
    offset: float        # -1.0 to 1.0
    invert: bool         # True = inverted (for ducking)

class FollowerState:
    enabled: bool        # v1: exposed
    attack_s: float      # v2: default 0.01 (v1: local only, not sent)
    release_s: float     # v2: default 0.1 (v1: local only, not sent)

# Note: attack_s and release_s are stored locally in v1 as defaults.
# v1 does NOT send /noise/crossmod/attack or /noise/crossmod/release.
# In v2, a Selected Source panel exposes ATK/REL and sends OSC updates.

class CrossmodRoutingState:
    connections: dict    # (source, target, param) -> CrossmodConnection
    followers: dict      # source (1-8) -> FollowerState
    
    # Connection methods
    def add_connection(conn: CrossmodConnection)
    def remove_connection(source, target, param)
    def get_connection(source, target, param) -> CrossmodConnection | None
    def set_amount(source, target, param, amount)
    def set_offset(source, target, param, offset)
    def set_invert(source, target, param, invert)
    def clear_all()
    
    # Follower methods
    def set_follower_enabled(source, enabled)
    
    # Signals
    connection_changed = pyqtSignal(int, int, str)  # source, target, param
    connection_removed = pyqtSignal(int, int, str)
    follower_changed = pyqtSignal(int)              # source
```

### OSC Bridge

```python
class CrossmodOSCBridge:
    """Syncs CrossmodRoutingState <-> SuperCollider via OSC."""
    
    # Fixed v1 defaults
    DEPTH = 1.0
    POLARITY = 0  # bipolar
    
    def __init__(self, state: CrossmodRoutingState, osc_client):
        self.state = state
        self.osc = osc_client
        self._connect_signals()
    
    def _on_connection_changed(self, source, target, param):
        conn = self.state.get_connection(source, target, param)
        if conn:
            self.osc.send("/noise/crossmod/route", [
                source, target, param,
                self.DEPTH,
                conn.amount,
                conn.offset,
                self.POLARITY,
                1 if conn.invert else 0
            ])
    
    def _on_connection_removed(self, source, target, param):
        self.osc.send("/noise/crossmod/unroute", [source, target, param])
    
    def _on_follower_changed(self, source):
        follower = self.state.followers[source]
        self.osc.send("/noise/crossmod/enabled", [source, 1 if follower.enabled else 0])
```

---

## Window Structure

### Header

```
CROSSMOD MATRIX                              [ENGINE] [CLEAR]
```

- Title: "CROSSMOD MATRIX"
- ENGINE button: Returns to main window (Ctrl+M)
- CLEAR button: Clears all crossmod routes

### Legend

```
Source: [●] Gen 1  [●] Gen 2  [●] Gen 3  ...  [●] Gen 8    [◐] = inverted
```

Color-coded dots matching source colors. Half-filled dot shows invert indicator.

### Shortcut

- Toggle: Ctrl+X (from main window)
- Close: Ctrl+X or Ctrl+M (when window focused)

---

## Files

| File | Purpose |
|------|---------|
| `crossmod_matrix_window.py` | Main window, grid layout, keyboard handling |
| `crossmod_matrix_cell.py` | Individual cell widget (adapt from mod_matrix_cell) |
| `crossmod_routing_state.py` | State management + signals |
| `crossmod_osc_bridge.py` | OSC sync to SuperCollider |
| `crossmod_connection_popup.py` | Amount/offset/invert popup (adapt from mod_connection_popup) |

---

## Implementation Notes

### Reuse from Mod Matrix

- Cell widget structure (adapt colors, add invert visual)
- Connection popup (add invert checkbox)
- Keyboard navigation logic
- Window geometry persistence
- Scroll area setup

### New Code

- 8-color source scheme
- Row header enable checkboxes
- Invert toggle (shift+click, popup checkbox)
- CrossmodRoutingState with follower state
- OSC bridge for `/noise/crossmod/*` endpoints

### Dependencies

- Backend must be running (crossmod buses initialized)
- OSC client connected to SuperCollider

---

## Success Criteria

1. [ ] Matrix displays 8×80 grid (640 cells, self-mod allowed)
2. [ ] Clicking cell toggles connection with correct source color
3. [ ] Shift+click creates inverted connection
4. [ ] Right-click popup shows amount/offset/invert controls
5. [ ] Row checkboxes toggle follower enabled
6. [ ] Keyboard navigation works (all cells navigable)
7. [ ] OSC messages sent correctly on all changes
8. [ ] Clear button removes all crossmod routes
9. [ ] Window geometry persisted
10. [ ] Ctrl+X toggles window from main

---

## v2 Roadmap (deferred)

- Follower ATK/REL controls (row header knobs or side panel)
- Depth/polarity in popup
- Visual feedback (animated dots showing live modulation)
- Preset save/load for crossmod configurations

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-30 | 1.0 | Initial spec from mod matrix reference |
| 2025-12-30 | 1.1 | AI review: Fixed OSC paths, added invert, row EN checkbox, allowed self-mod |
| 2025-12-30 | 1.2 | AI review fixes: OSC array args, click toggle semantics, ATK/REL v1 scope, INV indicator |
