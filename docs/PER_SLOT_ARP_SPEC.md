# Per-Slot Arpeggiator Specification

---
status: approved
version: 1.2.1
date: 2025-01-30
builds-on: ARP v1.7 (arp_engine.py), Keyboard Overlay R1.2-R1.3
reviewed-by: AI1, AI2, AI3
---

## What

Decouple the arpeggiator from the keyboard overlay so each generator slot (1-8) has its own independent ArpEngine instance. ARP+HOLD on a slot persists across keyboard hide/show -- the generator keeps playing its held arp pattern until the user explicitly turns hold off.

## Why

Current behavior: one shared ArpEngine targets multiple slots simultaneously. Closing the keyboard tears everything down. This creates two problems:

1. **No persistence** -- you can't set up an arp on slot 1, close the keyboard, and have it keep playing while you work on something else.
2. **No independence** -- all targeted slots share the same pattern, rate, octaves, and hold state. You can't have slot 1 running UP at 1/16 while slot 3 runs DOWN at 1/4.

Per-slot arps enable a performance workflow: build up layered arp patterns across multiple generators, each with independent settings, while freely opening and closing the keyboard overlay.

---

## Architecture

### Current (v1.7)

```
KeyboardOverlay
  +-- 1x ArpEngine (shared)
        |-- targets: Set[int] (multi-slot broadcast)
        |-- settings: ArpSettings (single)
        +-- runtime: ArpRuntime (single)
```

### Proposed (v2.0)

```
KeyboardController
  +-- ArpSlotManager
        |-- engines[0..7]: ArpEngine (one per slot, always exists, never removed)
        +-- bpm_subscription (forwards to all engines)

KeyboardOverlay (UI only)
  +-- shows/edits the ArpEngine for the currently focused slot
```

### Key Changes

1. **Engine ownership moves** from overlay (UI) to controller (logic)
2. **One engine per slot** -- no multi-target broadcast
3. **Overlay becomes stateless** -- pure view/control surface
4. **BPM forwarding** -- ArpSlotManager subscribes to BPM changes and forwards to all 8 engines (safe to call on IDLE engines -- no-op)
5. **Engines are never removed** -- reset in-place only, array never mutated after init

### Initialization Order (Required)

1. KeyboardController creates ArpSlotManager (8 engines created eagerly)
2. KeyboardOverlay created (starts hidden, no engine bound)
3. First `set_arp_engine()` call happens on keyboard open, not at overlay init

**Rationale:** Prevents null pointer / AttributeError if overlay tries to bind before manager exists.

---

## Components

### ArpSlotManager (new)

Owns 8 ArpEngine instances. Lives in KeyboardController.

```python
class ArpSlotManager:
    engines: list[ArpEngine]   # Always 8, never None, never removed

    def get_engine(self, slot: int) -> ArpEngine
    def reset_slot(self, slot: int)
    def reset_all(self)
    def all_notes_off(self)
    def get_active_holds(self) -> list[int]
    def on_bpm_changed(self, bpm: float)
```

**Lifecycle:**
- Created once at KeyboardController init
- All 8 engines created eagerly at startup
- Engines start in IDLE state (no timers running)
- Engines persist for the lifetime of the application
- `reset_slot()` resets in-place -- never removes or nulls out `engines[slot]`

### reset_slot() Semantics

1. Cancel any pending scheduled callbacks (timer)
2. Send note-off for currently sounding note (if any)
3. Clear active set, latched set, physical-input tracking
4. Reset settings to defaults (ARP off, HOLD off)
5. Engine returns to IDLE state (reusable)
6. Engine object remains in `engines[slot]` -- never None

### ArpEngine Changes

Each engine targets exactly **one slot** (not a set of slots).

```python
class ArpEngine:
    def __init__(self, slot_id: int, send_note_on, send_note_off,
                 get_velocity, get_bpm, ...):
        self._slot_id = slot_id  # fixed, 0-indexed
```

**Remove from ArpEngine:**
- `get_targets` callback
- `notify_targets_changed()`
- `_handle_target_change()`
- `last_played_targets` tracking

**Add to ArpEngine:**
- `slot_id` property (read-only)
- `is_active` property (ARP on and has notes in active set)
- `has_hold` property (HOLD enabled with latched notes)
- `currently_sounding_note` property

### ArpEngine.teardown() Sequence

1. Cancel any pending scheduled callbacks (stop timer)
2. Send note-off for `currently_sounding_note` (if any)
3. Clear active set, latched set, physical-input tracking
4. Set ARP off, HOLD off
5. Engine returns to IDLE state (reusable)

### KeyboardOverlay Changes

**Remove:**
- `self._arp_engine` ownership
- ARP+HOLD persistence logic

**Add:**
- `set_arp_engine(engine)` with null guard
- `sync_ui_from_engine()` -- exhaustive UI sync
- `_physical_keys_held: set[int]`

**Target selector:** single-select radio group (1-8)

---

## Behaviors

### Opening the Keyboard (Cmd+K)

1. Auto-switch focused slot to MIDI mode
2. Get focused slot's engine from ArpSlotManager
3. Call `set_arp_engine(engine)`
4. `sync_ui_from_engine()` updates all controls
5. Clear `_physical_keys_held`

### Playing Notes

1. Keys route to the **focused slot's** ArpEngine only
2. If ARP off: direct note-on/off
3. If ARP on: keys feed into engine

### Switching Focus (Clicking Slot Buttons)

1. Capture previous engine reference
2. Release all physical keys from previous engine
3. Clear `_physical_keys_held`
4. Auto-switch new slot to MIDI mode
5. Get new slot's engine
6. Call `set_arp_engine(new_engine)`
7. Previous engine continues if ARP+HOLD active

### Closing the Keyboard (Cmd+K / ESC)

1. Release all physical keys from focused engine
2. Clear `_physical_keys_held`
3. For each slot engine: if `has_hold`, skip; otherwise `reset_slot()`
4. Call `set_arp_engine(None)`
5. Hide overlay

### Pack Change / Preset Load

1. ArpSlotManager `reset_all()`
2. All-notes-off to all slots
3. Pack/preset loads
4. If keyboard visible: re-enable MIDI, re-bind

### Generator Change on Single Slot

1. If engine active/has_hold: `reset_slot()`
2. All-notes-off to slot
3. Load new generator
4. If overlay visible and focused: re-enable MIDI, re-bind

---

## Invariants

1. One engine per slot, never shared
2. Engines always exist, never removed, reset in-place
3. Monophonic per engine (one note sounding)
4. No stuck notes (all paths to IDLE send note-off)
5. Overlay is stateless (engines hold all ARP state)
6. Focus is exclusive (one engine bound at a time, or None)
7. Physical keys are overlay state, not engine state
8. Hold survives hide
9. Hold toggle works regardless of overlay state
10. Generator change kills one engine
11. Pack change kills all engines
12. Reset before change (note-off reaches current generator)
13. Sync is synchronous
14. Reference capture before iteration on focus switch

---

## Migration Path

### Phase 1: ArpSlotManager + Single-Slot Engine
### Phase 2: ARP+HOLD Persistence
### Phase 3: Visual Indicators

---

## Changelog

### v1.2.1 (2025-01-30) -- APPROVED
- Added: Explicit prev_engine reference capture in focus switch
- Added: Invariant #14 (reference capture before iteration)
- Added: Sequence diagram for focus switch
- Status: approved

### v1.0 (2025-01-30)
- Initial draft
