# Per-Slot Arpeggiator Specification

---
status: implemented
version: 2.0
date: 2025-01-30
builds-on: ARP v1.7 (arp_engine.py), Keyboard Overlay R1.2-R1.3
---

## What

Decouple the arpeggiator from the keyboard overlay so each generator slot (1-8) has its own independent ArpEngine instance. ARP+HOLD on a slot persists across keyboard hide/show -- the generator keeps playing its held arp pattern until the user explicitly turns hold off.

## Why

Previous behavior: one shared ArpEngine targeted multiple slots simultaneously. Closing the keyboard tore everything down. Two problems:

1. **No persistence** -- you can't set up an arp on slot 1, close the keyboard, and have it keep playing while you work on something else.
2. **No independence** -- all targeted slots shared the same pattern, rate, octaves, and hold state. You can't have slot 1 running UP at 1/16 while slot 3 runs DOWN at 1/4.

Per-slot arps enable a performance workflow: build up layered arp patterns across multiple generators, each with independent settings, while freely opening and closing the keyboard overlay.

---

## Architecture

```
KeyboardController
  +-- ArpSlotManager
        |-- engines[0..7]: ArpEngine (one per slot, always exists, never removed)
        +-- on_bpm_changed() (forwards to all engines)

KeyboardOverlay (UI only — pure view)
  +-- set_arp_engine(engine) binds one engine at a time
  +-- sync_ui_from_engine() exhaustive UI sync on bind
  +-- _physical_keys_held: dict[qt_key, midi_note] (overlay state, not engine state)
```

### Key Principles

1. **Engine ownership lives in controller** (logic), not overlay (UI)
2. **One engine per slot** -- no multi-target broadcast
3. **Overlay is a pure view** -- no engine ownership, no persistence logic
4. **All 8 slots always clickable** -- clicking any slot auto-switches it to MIDI mode
5. **BPM forwarding** -- ArpSlotManager forwards BPM changes to all 8 engines
6. **Engines are never removed** -- reset in-place only, array never mutated after init

### Initialization Order

1. KeyboardController creates ArpSlotManager (8 engines created eagerly)
2. KeyboardOverlay created lazily on first Cmd+K (starts hidden, no engine bound)
3. First `set_arp_engine()` call happens on keyboard open, not at overlay init

---

## Components

### ArpSlotManager

Owns 8 ArpEngine instances. Lives in KeyboardController.

```python
class ArpSlotManager:
    engines: list[ArpEngine]   # Always 8, never None, never removed

    def get_engine(slot: int) -> ArpEngine
    def reset_slot(slot: int)       # Teardown in-place, engine object remains
    def reset_all()                 # Teardown all 8
    def all_notes_off()             # Panic: reset all + send all-notes-off
    def get_active_holds() -> list[int]  # Slots with ARP+HOLD active
    def on_bpm_changed(bpm: float)  # Forward to all engines
```

**Lifecycle:**
- Created once at KeyboardController init
- All 8 engines created eagerly at startup
- Engines start in IDLE state (no timers running)
- Engines persist for the lifetime of the application
- `reset_slot()` calls `teardown()` -- engine object stays in array

### ArpEngine (Per-Slot v2.0)

Each engine targets exactly **one slot** (fixed at construction).

```python
class ArpEngine:
    def __init__(self, slot_id: int, send_note_on, send_note_off,
                 get_velocity, get_bpm):
        self._slot_id = slot_id  # fixed, 0-indexed, read-only

    # Properties
    slot_id: int                       # read-only
    is_active: bool                    # ARP enabled and has notes
    has_hold: bool                     # HOLD enabled with latched notes
    currently_sounding_note: int|None  # Note playing right now

    # Public API
    key_press(note)
    key_release(note)
    toggle_arp(enabled)
    toggle_hold(enabled)
    set_rate(rate_index)
    set_pattern(pattern)
    set_octaves(octaves)
    notify_bpm_changed(bpm)
    teardown()
    get_settings() -> ArpSettings
```

### KeyboardOverlay (Pure View)

No engine ownership. Binds/unbinds via `set_arp_engine()`.

```python
class KeyboardOverlay:
    # Engine binding
    set_arp_engine(engine: ArpEngine|None)
    sync_ui_from_engine()               # Exhaustive UI sync
    release_physical_keys_from_engine() # Release held keys before unbind
    get_velocity() -> int               # Used by engines via callback

    # Constructor callbacks
    on_slot_focus_changed_fn(slot: int)  # Notify controller of target change
```

**Target selector:** Single-select exclusive radio group (1-8). All buttons always enabled. Clicking any slot notifies the controller, which auto-switches to MIDI mode and binds the new engine.

### KeyboardController

Owns ArpSlotManager. Handles all logic: focus switching, MIDI mode, dismiss/preserve.

```python
class KeyboardController:
    _arp_manager: ArpSlotManager
    _focused_slot: int  # 1-indexed

    # Public
    arp_manager: property               # For MainFrame wiring
    _toggle_keyboard_mode()             # Cmd+K handler
    _ensure_focused_slot_midi()         # Auto-switch ENV to MIDI

    # Internal
    _switch_focus_to_slot(new_slot_ui)  # Focus change with ref capture
    _on_keyboard_dismiss()              # Teardown/preserve per hold state
    _on_overlay_slot_focus_changed(slot) # Callback from overlay
```

---

## Behaviors

### Opening the Keyboard (Cmd+K)

1. Auto-switch focused slot to MIDI mode
2. Get focused slot's engine from ArpSlotManager
3. Call `set_arp_engine(engine)`
4. `sync_ui_from_engine()` restores all controls from engine state
5. Physical keys start empty

If the slot already has ARP+HOLD running, reopening the keyboard shows its current state (ARP on, HOLD on, pattern/rate/octaves as configured).

### Playing Notes

1. Physical key press/release tracked in overlay (`_physical_keys_held`)
2. Keys route to the **bound engine** only
3. If ARP off: direct note-on/off to target slot via OSC
4. If ARP on: keys feed into engine's active set

### Switching Focus (Clicking Slot Buttons or Number Keys 1-8)

1. **Capture** previous engine reference (Invariant #14)
2. **Release** all physical keys from previous engine
3. **Clear** `_physical_keys_held`
4. **Auto-switch** new slot to MIDI mode
5. **Bind** new slot's engine via `set_arp_engine(new_engine)`
6. **Sync** UI from new engine's state
7. Previous engine **continues** if ARP+HOLD active (no teardown)

### Closing the Keyboard (Cmd+K / ESC / CLOSE)

1. Release all physical keys from focused engine
2. Clear `_physical_keys_held`
3. Hide overlay
4. For each of 8 engines: if `has_hold` → **preserve** (keeps playing); otherwise → `reset_slot()`
5. Call `set_arp_engine(None)` to unbind

### Pack Change / Preset Load

1. `ArpSlotManager.reset_all()` — kills all 8 engines
2. Pack/preset loads normally
3. If keyboard visible: re-enable MIDI on focused slot, re-bind engine

### Generator Change on Single Slot

1. `reset_slot(slot)` — kills that engine
2. `all_notes_off(slot)` via OSC
3. Generator loads normally
4. If overlay visible and this is the focused slot: re-enable MIDI, re-bind engine

---

## Invariants

1. **One engine per slot**, never shared
2. **Engines always exist**, never removed, reset in-place
3. **Monophonic** per engine (at most one note sounding)
4. **No stuck notes** (all paths to IDLE send note-off)
5. **Overlay is stateless** (engines hold all ARP state)
6. **Focus is exclusive** (one engine bound at a time, or None)
7. **Physical keys are overlay state**, not engine state
8. **Hold survives hide** (closing keyboard preserves ARP+HOLD engines)
9. **All slots clickable** (auto-MIDI on target change)
10. **Generator change kills one** engine
11. **Pack change kills all** engines
12. **Reset before change** (note-off reaches current generator before new one loads)
13. **Sync is synchronous** (no async gaps between unbind and rebind)
14. **Reference capture before iteration** on focus switch

---

## Performance Workflow Example

1. Open keyboard (Cmd+K) — slot 1 focused
2. Enable ARP, set UP 1/16, enable HOLD
3. Play chord — slot 1 arps UP at 1/16
4. Click slot 3 — auto-switches to MIDI, fresh engine (ARP off)
5. Enable ARP, set DOWN 1/4, enable HOLD
6. Play different chord — slot 3 arps DOWN at 1/4
7. Close keyboard — both slot 1 and slot 3 keep playing
8. Work on mixing, effects, whatever
9. Reopen keyboard — slot 1 focused, UI shows UP 1/16 HOLD
10. Turn off HOLD — slot 1 stops, slot 3 continues

---

## Reuse Pattern for Future Features

This architecture establishes a **per-slot engine + pure view overlay** pattern that can be reused for other per-slot features (e.g. step sequencer):

```
Controller (logic owner)
  +-- SlotManager
        +-- engines[0..7]: Engine (one per slot, eager, never removed)

Overlay (pure view)
  +-- set_engine(engine) / sync_ui_from_engine()
  +-- on_slot_focus_changed callback to controller
```

**Key decisions to carry forward:**

| Decision | Rationale |
|----------|-----------|
| Controller owns engines, not overlay | Engines outlive overlay visibility |
| Eager creation (all 8 at init) | No null checks, no lazy-init races |
| Reset in-place, never remove | Array index = slot ID, always valid |
| Pure view overlay | Same overlay binds to any engine |
| Auto-MIDI on target click | No friction when switching slots |
| Reference capture before mutation | Prevents iterator invalidation |
| Physical input is overlay state | Engine doesn't know about keyboard |

---

## Changelog

### v2.0 (2025-01-30) -- IMPLEMENTED
- Implemented and tested in production
- All 8 target slots always clickable (auto-MIDI on click)
- Number keys 1-8 switch target unconditionally
- Added performance workflow example
- Added reuse pattern section for future features
- Status: implemented

### v1.2.1 (2025-01-30)
- Added: Explicit prev_engine reference capture in focus switch
- Added: Invariant #14 (reference capture before iteration)
- Status: approved

### v1.0 (2025-01-30)
- Initial draft
