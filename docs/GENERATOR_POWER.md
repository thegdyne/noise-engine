# Generator Lock & Power Off - Design Document

**Status:** Planning  
**Created:** 2025-12-14

---

## Overview

Two controls for each generator slot that protect generator selection and allow quick power cycling while preserving full state.

---

## UI Location

Top right of each generator slot:

```
┌─────────────────────────────────────┐
│  [Anvil ▼]                  🔒  ⏻  │
│                                     │
│  FRQ ════════════════════════       │
│  CUT ════════════════════════       │
│  ...                                │
└─────────────────────────────────────┘
```

---

## Lock (🔒)

**Purpose:** Prevent accidental generator changes while allowing parameter tweaks.

**Behaviour:**
- Toggle on/off
- When locked: generator dropdown disabled
- When locked: everything else enabled (params, channel strip, trigger mode)

**Visual:**
- 🔒 icon highlighted/filled when active
- Generator dropdown visually disabled (greyed)

---

## Power Off (⏻)

**Purpose:** Quickly silence a slot while preserving full state for instant recall.

**Behaviour:**

| Action | Result |
|--------|--------|
| Press ⏻ (running) | Stop audio, store state, dim slot, auto-lock, disable params |
| Press ⏻ (powered off) | Restore audio, restore state, restore previous lock state |

**What gets stored:**
- Generator type
- All 5 params (FRQ, CUT, RES, ATK, DEC)
- Trigger mode (OFF/CLK/MIDI)
- CLK division (if applicable)
- Channel strip state (vol, pan, mute, solo, gain)
- Previous lock state (was_locked)

**Visual (powered off):**
- Slot dimmed/greyed
- All params disabled
- Generator dropdown disabled (auto-locked)
- Only ⏻ button fully active
- ⏻ icon indicates powered off state (different colour/fill)

---

## State Summary

| State | 🔒 | ⏻ | Generator dropdown | Params | Audio |
|-------|----|----|-------------------|--------|-------|
| Normal | Off | Off | Enabled | Enabled | Playing |
| Locked | On | Off | Disabled | Enabled | Playing |
| Powered off | Auto | On | Disabled | Disabled | Silent |

---

## Storage (SSOT)

All state stored centrally, not in individual generator configs:

```python
# In central config or generator_manager.py

# Lock state per slot
locked_slots = {1: False, 2: True, 3: False, ...}

# Powered off slots with preserved state
powered_off_slots = {
    3: {
        "generator": "Anvil",
        "params": {
            "frq": 0.5,
            "cut": 0.7,
            "res": 0.3,
            "atk": 0.1,
            "dec": 0.4
        },
        "trigger": {
            "mode": "CLK",
            "division": "/4"
        },
        "channel_strip": {
            "volume": 0.8,
            "pan": 0.0,
            "mute": False,
            "solo": False,
            "gain": 0
        },
        "was_locked": False
    }
}
```

---

## Signal Flow

```
┌─────────────────────────────────────────────────────┐
│                    🔒 Lock Toggle                    │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Generator Dropdown                      │
│                                                      │
│  Locked: Disabled                                   │
│  Unlocked: Enabled                                  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                  ⏻ Power Toggle                     │
└─────────────────────┬───────────────────────────────┘
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
     ┌─────────────┐     ┌─────────────┐
     │  Power Off  │     │  Power On   │
     ├─────────────┤     ├─────────────┤
     │ Store state │     │ Restore     │
     │ Stop audio  │     │ state       │
     │ Auto-lock   │     │ Start audio │
     │ Dim slot    │     │ Restore     │
     │ Disable     │     │ lock state  │
     │ params      │     │ Enable      │
     └─────────────┘     └─────────────┘
```

---

## Implementation Notes

**Files to modify:**
- `src/config/__init__.py` - Add locked_slots, powered_off_slots dicts
- `src/gui/generator_slot.py` - Add 🔒 and ⏻ buttons, state handling
- `src/gui/theme.py` - Add powered_off/dimmed visual state
- `src/audio/osc_bridge.py` - Handle generator stop/start on power toggle

**Key considerations:**
- Theme handles all visual states (normal, locked, powered off)
- State stored centrally for SSOT compliance
- Power off sends stop message to SC, power on re-initialises generator

---

## Edge Cases

**Empty slot:**
- Lock button disabled (nothing to lock)
- Power button disabled (nothing to power off)

**Powered off slot + preset load:**
- Powered off slots remain powered off
- New preset data stored but not activated until power on

**Multiple slots powered off:**
- Each slot independent
- No limit on how many can be powered off

---

## Future Enhancements

- Keyboard shortcut to power off selected slot
- "Power off all" / "Power on all" commands
- Visual indication in mixer panel for powered off channels
- Preset option: "preserve powered off states on load"
