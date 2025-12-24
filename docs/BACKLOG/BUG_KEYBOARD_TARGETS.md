# BUG: Keyboard Overlay Target Slots Greyed Out

**Priority:** P2 (Feature partially broken)  
**Component:** `src/gui/keyboard_overlay.py`, `src/gui/main_frame.py`  
**Status:** Investigating

---

## Symptom

When opening the keyboard overlay (CMD+K), the target slot buttons (1-8) are greyed out and cannot be selected, except for slot 1. This happens even when:
- All 8 slots have generators loaded
- All slots are set to MIDI envelope mode

## Expected Behavior

- Slots in MIDI mode should be enabled (clickable)
- Slots NOT in MIDI mode should be greyed out
- User can click enabled slots to add them as targets
- Number keys 1-8 should toggle targets

## Actual Behavior

- Only slot 1 is enabled
- Slots 2-8 are greyed out regardless of their envelope mode
- Cannot target multiple slots

## Root Cause (Suspected)

The `_is_slot_midi_mode` callback in `main_frame.py` checks:

```python
def _is_slot_midi_mode(self, slot_id: int) -> bool:
    """Check if slot is in MIDI envelope mode. Slot is 1-indexed (UI)."""
    if slot_id < 1 or slot_id > 8:
        return False
    slot = self.generator_grid.slots[slot_id]
    return slot.env_source == 2  # 2 = MIDI mode
```

Likely issues:
1. `slot.env_source` might be a method requiring `()` not a property
2. `slot.env_source` might return a string ("MIDI") not int (2)
3. `generator_grid.slots` indexing might be wrong for slots 2-8
4. The env_source value mapping might differ (0/1/2 vs different enum)

## Debug Steps

1. Check what `env_source` actually returns:
```python
# Add to _is_slot_midi_mode temporarily:
for i in range(1, 9):
    slot = self.generator_grid.slots[i]
    print(f"Slot {i}: env_source={slot.env_source}, type={type(slot.env_source)}")
```

2. Check generator_slot.py for env_source definition:
```bash
grep -A 10 "env_source" ~/repos/noise-engine/src/gui/generator_slot.py
```

3. Check if it's a method vs property:
```bash
grep -B 2 "def env_source\|env_source =" ~/repos/noise-engine/src/gui/generator_slot.py
```

## Files Involved

| File | Role |
|------|------|
| `src/gui/keyboard_overlay.py` | Calls `_is_slot_midi_mode(slot_id)` in `_update_slot_buttons()` |
| `src/gui/main_frame.py` | Implements `_is_slot_midi_mode()` callback |
| `src/gui/generator_slot.py` | Defines `env_source` property/attribute |

## Fix (Once Root Cause Confirmed)

Update `_is_slot_midi_mode` to correctly read the envelope source value from each slot.

---

*Created: 2024-12-24*
