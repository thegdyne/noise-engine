# Keyboard Mode Spec v1.2 (FROZEN)

*CMD+K popup keyboard for MIDI triggering*
*Frozen: December 2025*

---

## What

A toggleable overlay that captures QWERTY keys and sends MIDI note-on/off to the focused slot (or all slots). Allows quick melodic input without external MIDI hardware.

## Why

- Quick sound design iteration without reaching for a MIDI controller
- Useful for laptop-only sessions
- Common feature in DAWs (Logic, Ableton)

---

## Behavior

| Aspect | Behavior |
|--------|----------|
| Trigger | Cmd+K (macOS) / Ctrl+K (Windows/Linux) toggles overlay |
| Dismiss | ESC or Cmd/Ctrl+K |
| Default target | Focused slot only |
| Multi-slot | Toggle buttons enable additional slots |
| Velocity | Selectable: 64 / 100 / 127 (default 100) |
| ENV interaction | Only triggers slots in MIDI mode |
| Position | Bottom-center, fixed 24px margin |
| Size | Fixed (not resizable) |
| Style | Match Noise Engine dark theme |

### Input Capture

- On show: `self.grabKeyboard()` and `self.setFocus(Qt.ActiveWindowFocusReason)`
- On hide/close: `self.releaseKeyboard()` (guarded)
- Ignore `keyPress` events where `event.isAutoRepeat() == True`
- Ignore `keyRelease` events where `event.isAutoRepeat() == True`
- Map keys using `Qt.Key_*` constants via `event.key()`, NOT `event.text()` (layout-independent)
- If key in `OCTAVE_KEYS`: handle octave change, `event.accept()`, return early (never stored in `_pressed`)

---

## Keyboard Layout (Logic-style)

```
 │ W │ E │   │ T │ Y │ U │   │ O │ P │
 │C#4│D#4│   │F#4│G#4│A#4│   │C#5│D#5│
┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
│ A │ S │ D │ F │ G │ H │ J │ K │ L │ ; │
│C4 │D4 │E4 │F4 │G4 │A4 │B4 │C5 │D5 │E5 │
└───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
```

**Octave control:**
- Z = octave down
- X = octave up
- Range: **Oct 0–7** (MIDI notes stay within 0–127)

---

## UI Layout

```
┌──────────────────────────────────────────────────────────────┐
│  ≡ KEYBOARD                    Vel: [64][•100][127]  Oct: 4  │  ← draggable header
├──────────────────────────────────────────────────────────────┤
│                                                              │
│      ┌─┐ ┌─┐     ┌─┐ ┌─┐ ┌─┐     ┌─┐ ┌─┐                    │
│      │W│ │E│     │T│ │Y│ │U│     │O│ │P│   Black keys       │
│      └─┘ └─┘     └─┘ └─┘ └─┘     └─┘ └─┘                    │
│     ┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐                         │
│     │A │S │D │F │G │H │J │K │L │; │     White keys          │
│     └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘                         │
│                                                              │
│     [Z] Oct-   [X] Oct+                                      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  Target: [1] [2] [3] [4] [5] [6] [7] [8]                     │
│          ●   ○   ○   ○   ○   ○   ○   ○                       │
└──────────────────────────────────────────────────────────────┘
```

- Keys highlight on press (keyed by `event.key()`, not text)
- Target buttons toggle which slots receive notes
- Focused slot auto-selected on open (filled ●)
- Non-MIDI-mode slots shown greyed/disabled
- Header bar is draggable (move only, no resize)
- Velocity buttons: radio-style selection, dot indicates active

---

## Implementation

### Key Mapping (Qt Key Codes)

```python
from PyQt5.QtCore import Qt

KEY_TO_SEMITONE = {
    # White keys (bottom row)
    Qt.Key_A: 0,   # C
    Qt.Key_S: 2,   # D
    Qt.Key_D: 4,   # E
    Qt.Key_F: 5,   # F
    Qt.Key_G: 7,   # G
    Qt.Key_H: 9,   # A
    Qt.Key_J: 11,  # B
    Qt.Key_K: 12,  # C+1
    Qt.Key_L: 14,  # D+1
    Qt.Key_Semicolon: 16,  # E+1
    
    # Black keys (top row)
    Qt.Key_W: 1,   # C#
    Qt.Key_E: 3,   # D#
    Qt.Key_T: 6,   # F#
    Qt.Key_Y: 8,   # G#
    Qt.Key_U: 10,  # A#
    Qt.Key_O: 13,  # C#+1
    Qt.Key_P: 15,  # D#+1
}

OCTAVE_KEYS = {
    Qt.Key_Z: -1,  # Octave down
    Qt.Key_X: +1,  # Octave up
}
```

MIDI note = `(octave + 1) * 12 + semitone`, clamped to 0–127

### Note State Tracking

```python
class KeyboardOverlay:
    def __init__(self):
        self._octave = 4  # C4 default
        self._velocity = 100  # 64, 100, or 127
        self._pressed: dict[int, int] = {}  # qt_key -> midi_note
        self._target_slots: set[int] = set()  # 0-7
```

**Rules:**
- `keyPressEvent`: 
  - If key in `OCTAVE_KEYS`: handle octave change, return early
  - If `event.isAutoRepeat()`: ignore
  - If key in map and key not in `_pressed`: compute note, store in `_pressed`, send note_on to all target slots
- `keyReleaseEvent`: 
  - If `event.isAutoRepeat()`: ignore
  - If key in `_pressed`: pop note, send note_off to all target slots

### Octave Change with Held Keys

On Z/X press:
1. Clamp new octave to 0–7
2. For each key in `_pressed`:
   - Send note_off for old midi_note to all target slots
   - Compute new midi_note with updated octave
   - Send note_on for new midi_note to all target slots
   - Update `_pressed[key] = new_note`
3. Update octave display

### OSC Endpoints

| Endpoint | Args | Description |
|----------|------|-------------|
| `/slot/{n}/midi/note_on` | `<note> <velocity>` | Trigger note |
| `/slot/{n}/midi/note_off` | `<note>` | Release note |
| `/slot/{n}/midi/all_notes_off` | none | Panic – release all |

### Dismissal / Cleanup

On overlay close (ESC, Cmd/Ctrl+K, or window deactivate):
1. **For slots 0–7**: send `/slot/{n}/midi/all_notes_off` (panic to all, not just targets)
2. Clear `_pressed`
3. `self.releaseKeyboard()`
4. Hide overlay

### Window Deactivation

On `QEvent.ApplicationDeactivate` or `QEvent.WindowDeactivate`:
1. Send all_notes_off to slots 0–7
2. Clear `_pressed`
3. **Auto-hide overlay** (simpler UX than inactive state)

### Files

| File | Changes |
|------|---------|
| `src/gui/keyboard_overlay.py` | New – QWidget overlay |
| `src/gui/main_frame.py` | Add Cmd/Ctrl+K shortcut, `_send_midi_note_on/off()`, `_send_all_notes_off()` |
| `src/config/__init__.py` | Add OSC paths for note_on/off/all_notes_off |

---

## Edge Cases

| Case | Behavior |
|------|----------|
| E1: No slots in MIDI mode | Show overlay, all target buttons greyed, info text "No slots in MIDI mode" |
| E2: Focused slot not in MIDI mode | Auto-select first MIDI-mode slot, or show info if none |
| E3: Key held + octave change | Note-off old pitch, note-on new pitch for ALL held keys |
| E4: Multiple keys held | Polyphonic – all notes sound |
| E5: Overlay open + real MIDI input | Both work simultaneously; no arbitration (generator handles voice policy) |
| E6: Cmd/Ctrl+K while typing in text field | Don't open overlay if `focusWidget()` is QLineEdit/QTextEdit/QSpinBox; but shortcut always closes if already open |
| E7: Overlay loses focus / app deactivates | Send all_notes_off to slots 0–7, auto-hide overlay |
| E8: Target slots change while keys held | Does NOT retrigger held notes; only affects subsequent note_on/off |

---

## Out of Scope (v1)

- Sustain pedal emulation
- Pitch bend / mod wheel
- Per-note velocity / aftertouch
- Key labels toggle
- MIDI learn from overlay
- Recording to sequencer
- Resizable overlay

---

## Success Criteria

- [ ] Cmd+K (macOS) / Ctrl+K (Win/Linux) toggles overlay
- [ ] Respects text field focus on open (doesn't hijack typing)
- [ ] Keys trigger notes on target slots via OSC
- [ ] No stuck notes on dismiss (all_notes_off sent to slots 0–7)
- [ ] Auto-repeat ignored (no note spam)
- [ ] Octave change re-pitches held notes correctly
- [ ] Octave range enforced (0–7), MIDI notes stay 0–127
- [ ] Slot buttons enable multi-slot targeting
- [ ] Z/X shift octave, display updates
- [ ] Only MIDI-mode slots shown as targetable
- [ ] Velocity selector (64/100/127) works
- [ ] ESC dismisses
- [ ] Header draggable
- [ ] Window deactivate triggers cleanup + auto-hide

---

**Status: FROZEN**
