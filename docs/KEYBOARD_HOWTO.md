# Keyboard Mode

Play Noise Engine with your QWERTY keyboard — no MIDI controller needed.

---

## Quick Start

1. **Set a slot to MIDI mode** — Click ENV until it shows "MIDI"
2. **Open keyboard** — Press `Cmd+K` (Mac) or `Ctrl+K` (Win/Linux)
3. **Play!** — Use the home row keys as a piano

---

## Opening & Closing

| Action | Shortcut |
|--------|----------|
| Open/Close | `Cmd+K` / `Ctrl+K` |
| Close | `ESC` or click CLOSE button |

The overlay stays open while you tweak other controls. Click anywhere on the main window — the keyboard keeps capturing your keypresses.

---

## Key Layout (Logic-style)

```
     W   E       T   Y   U       O   P
    C#  D#      F#  G#  A#      C#  D#
  ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
  │ A │ S │ D │ F │ G │ H │ J │ K │ L │ ; │
  │ C │ D │ E │ F │ G │ A │ B │ C │ D │ E │
  └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
```

**Bottom row** = White keys (natural notes)  
**Top row** = Black keys (sharps/flats)

---

## Octave Control

| Key | Action |
|-----|--------|
| `Z` | Octave down |
| `X` | Octave up |

Range: Octave 0–7 (displayed in header)

**Held notes shift pitch** — If you're holding a note and press Z/X, the pitch changes smoothly without retriggering.

---

## Velocity

Three fixed velocity levels (click to select):

| Button | Velocity | Use |
|--------|----------|-----|
| 64 | Soft | Gentle, ambient |
| **100** | Medium | Default, balanced |
| 127 | Hard | Punchy, aggressive |

---

## Target Slots

By default, notes go to the first MIDI-mode slot. 

**Multi-slot playing:**
- Click slot buttons 1–8 to toggle targets
- Or press number keys `1`–`8` to toggle
- Multiple slots can be active — play the same note on several generators

**Visual indicators:**
- **Filled dot** = slot will receive notes
- **Greyed out** = slot not in MIDI mode (won't sound)

---

## Tips

### No sound?
1. Check at least one slot has ENV set to "MIDI"
2. Check that slot isn't muted
3. Check master fader is up

### Polyphonic playing
Hold multiple keys — all notes sound simultaneously. Great for chords.

### Quick patch auditioning
Open keyboard, play a few notes, tweak the generator's CUT/RES/ATK/DEC while playing. The overlay doesn't steal focus from sliders.

### Different clock rates
Even with MIDI triggering, the ATK/DEC parameters shape the note. Try very short decay for percussive hits.

---

## Limitations (v1)

- No sustain pedal
- No pitch bend or mod wheel
- Fixed velocity (no pressure sensitivity)
- No recording to sequencer

---

*See also: [KEYBOARD_MODE_SPEC.md](KEYBOARD_MODE_SPEC.md) for technical details*
