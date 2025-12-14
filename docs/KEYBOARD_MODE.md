# Computer Keyboard Mode - Design Document

**Status:** Planning  
**Created:** 2025-12-14

---

## Overview

A software MIDI keyboard triggered by CMD+K that allows playing generators directly from the computer keyboard. Sends pitch and gate messages identical to external MIDI input.

---

## Interaction Model

**Toggle:**
- CMD+K enters keyboard mode
- CMD+K or ESC exits keyboard mode

**Targeting:**
- Last clicked generator slot receives keyboard input
- Click a different slot while in keyboard mode to retarget

---

## Behaviour by Trigger Mode

| Slot was in | On CMD+K enter | While active | On exit |
|-------------|----------------|--------------|---------|
| OFF or CLK | Switch to MIDI | Keyboard sends pitch/gate | Restore previous mode |
| MIDI | No change | Keyboard sends pitch/gate (alongside sequencer) | No change |

**Conflict resolution:** Last message wins. No special logic. Keyboard and sequencer can both send to the same slot simultaneously.

---

## Key Mapping

Two-row chromatic layout (same as Ableton):

```
 W E   T Y U   O P
A S D F G H J K L ;
│ │ │ │ │ │ │ │ │ │
C C# D D# E F F# G G# A A# B C
```

**Octave controls:**
- Z = octave down
- X = octave up
- Default octave = 4 (middle C = 261.63 Hz)

---

## OSC Messages

Keyboard sends the same messages as MIDI input:

```
Key down  → /noise/slot/X/pitch <Hz>
          → /noise/slot/X/gate 1

Key up    → /noise/slot/X/gate 0
```

Where X = targeted slot number (1-8)

---

## Visual Feedback

**Status bar:**
- Shows `⌨ 3` when keyboard mode active (number = targeted slot)
- Clears on exit

**Targeted slot:**
- Subtle glow around slot
- Small keyboard icon indicator
- Both clear on exit

---

## Signal Flow

```
┌─────────────────────────────────────────────────────┐
│                    CMD+K Toggle                      │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Keyboard Mode Active                    │
│                                                      │
│  QWERTY keys → Note number → Hz conversion           │
│  Z/X keys → Octave shift                            │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│           Same path as MIDI input                    │
│                                                      │
│  /noise/slot/X/pitch <Hz>                           │
│  /noise/slot/X/gate 1/0                             │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Generator responds                      │
│                                                      │
│  FRQ ← pitch                                        │
│  ENV ← gate triggers attack/decay                   │
└─────────────────────────────────────────────────────┘
```

---

## Implementation Notes

**Files to modify:**
- `src/gui/main_frame.py` - CMD+K shortcut handling, keyboard mode state
- `src/gui/generator_slot.py` - Visual indicator for targeted slot
- `src/audio/osc_bridge.py` - Pitch/gate message sending (reuse MIDI path)

**Key considerations:**
- Capture key events only when keyboard mode active
- Prevent QWERTY keys from triggering other UI elements while in mode
- Track key up/down state to avoid repeated triggers from key repeat

---

## Future Enhancements

- Velocity sensitivity (e.g. C = soft, V = hard)
- Sustain pedal emulation (spacebar?)
- Chord memory / latch mode
- Visual on-screen keyboard display
- Multi-slot keyboard splits

---

## References

- Ableton Live computer MIDI keyboard
- Logic Pro Musical Typing
