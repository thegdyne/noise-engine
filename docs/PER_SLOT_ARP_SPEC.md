# Per-Slot Arpeggiator Specification

---
status: draft
version: 1.0
date: 2025-01-30
builds-on: ARP v1.7 (arp_engine.py), Keyboard Overlay R1.2-R1.3
---

## What

Decouple the arpeggiator from the keyboard overlay so each generator slot (1–8) has its own independent ArpEngine instance. ARP+HOLD on a slot persists across keyboard hide/show — the generator keeps playing its held arp pattern until the user explicitly turns hold off.

## Why

Current behavior: one shared ArpEngine targets multiple slots simultaneously. Closing the keyboard tears everything down. This creates two problems:

1. **No persistence** — you can't set up an arp on slot 1, close the keyboard, and have it keep playing while you work on something else.
2. **No independence** — all targeted slots share the same pattern, rate, octaves, and hold state. You can't have slot 1 running UP at 1/16 while slot 3 runs DOWN at 1/4.

Per-slot arps enable a performance workflow: build up layered arp patterns across multiple generators, each with independent settings, while freely opening and closing the keyboard overlay.

---

## Architecture

### Current (v1.7)

```
KeyboardOverlay
  └── 1x ArpEngine (shared)
        ├── targets: Set[int] (multi-slot broadcast)
        ├── settings: ArpSettings (single)
        └── runtime: ArpRuntime (single)
```

### Proposed (v2.0)

```
KeyboardController
  └── ArpSlotManager
        ├── engines[0]: ArpEngine (slot 1)
        ├── engines[1]: ArpEngine (slot 2)
        ├── ...
        └── engines[7]: ArpEngine (slot 8)

KeyboardOverlay (UI only)
  └── shows/edits the ArpEngine for the currently focused slot
```

### Key Change

The ArpEngine moves from being owned by the overlay (UI) to being managed by the KeyboardController (logic). The overlay becomes a pure view/control surface that reads and writes the focused slot's engine state.

---

## Components

### ArpSlotManager (new)

Owns 8 ArpEngine instances. Lives in KeyboardController.

```python
class ArpSlotManager:
    """Manages per-slot ARP engines."""

    engines: dict[int, ArpEngine]   # slot 0-7 (OSC-indexed)

    def get_engine(self, slot: int) -> ArpEngine
    def teardown_slot(self, slot: int)
    def teardown_all(self)
    def get_active_holds(self) -> list[int]  # slots with ARP+HOLD running
```

**Lifecycle:**
- Created once at KeyboardController init
- Each engine is lazily initialized on first use (or eagerly — TBD)
- Engines persist for the lifetime of the application
- Individual engines can be torn down independently

### ArpEngine Changes

Each engine targets exactly **one slot** (not a set of slots). Remove `get_targets` callback. The engine always emits to its bound slot.

```python
class ArpEngine:
    def __init__(self, slot_id: int, send_note_on, send_note_off,
                 get_velocity, get_bpm, ...):
        self._slot_id = slot_id  # fixed, 0-indexed
```

Remove from ArpEngine:
- `get_targets` callback
- `notify_targets_changed()`
- `_handle_target_change()`
- `last_played_targets` tracking (always single slot)

### KeyboardOverlay Changes

The overlay becomes a **view** for whichever slot's ArpEngine is focused.

**Remove from overlay:**
- `self._arp_engine` (no longer owns an engine)
- ARP+HOLD persistence logic (`_should_preserve_arp_session_on_hide`)

**Add to overlay:**
- `set_arp_engine(engine: ArpEngine | None)` — bind to a slot's engine
- `sync_ui_from_engine()` — update all ARP controls from engine state

**Target slot selector** changes meaning:
- Currently: multi-select broadcast targets
- Proposed: single-select slot focus (radio buttons instead of checkboxes)
- Clicking a slot switches which ArpEngine the overlay controls
- Visual indicator for slots that have an active ARP+HOLD (e.g. pulsing border)

---

## Behaviors

### Opening the Keyboard (Cmd+K)

1. Auto-switch focused slot to MIDI mode (existing behavior)
2. Bind overlay to focused slot's ArpEngine
3. Sync overlay UI from engine state (ARP on/off, rate, pattern, octaves, hold)
4. If engine has ARP+HOLD active, show ARP controls and current state
5. If engine is idle, show ARP toggle OFF (don't reset a running engine on another slot)

### Playing Notes

1. Keys route to the **focused slot's** ArpEngine only
2. If ARP is off: legacy note-on/off directly to focused slot
3. If ARP is on: keys feed into focused slot's engine as before

### Switching Focus (Clicking Slot Buttons)

1. Release all physical keys from **previous** engine (key_release for each held note)
2. Bind overlay to **new** slot's engine
3. Sync UI from new engine's state
4. Previous engine continues running if ARP+HOLD is active (latched notes persist)
5. Auto-switch new slot to MIDI mode if not already

### Closing the Keyboard (Cmd+K / ESC)

1. Release all physical keys from focused engine
2. For **each slot's engine** (0–7):
   - If ARP+HOLD is active: **keep running** (notes sustain, timer continues)
   - Otherwise: teardown (note-off, stop timers, reset state)
3. Hide overlay

### Turning Off Hold

1. Engine exits hold mode
2. If no physical keys held: active set empties → note-off → engine goes idle
3. If keyboard is closed and hold was the only thing keeping it alive: engine tears down

### Pack Change While ARP+HOLD Active

1. Pack load resets all slots (generators change, ENV resets)
2. ArpSlotManager tears down **all** engines (generators changed, MIDI mode lost)
3. All-notes-off sent to all slots
4. If keyboard overlay is visible, re-apply MIDI mode to focused slot (existing behavior)

### Generator Change on Single Slot

1. If slot's engine has ARP+HOLD active, teardown that engine
2. Send all-notes-off to that slot
3. Other slots' engines unaffected

---

## UI Changes

### Target Row (Bottom of Overlay)

| Current | Proposed |
|---------|----------|
| Multi-select checkboxes (1–8) | Single-select radio group (1–8) |
| "Target:" label | "Slot:" label |
| Checked = receives notes | Selected = focused for editing |
| Disabled = not MIDI mode | Disabled = not MIDI mode |
| — | Active ARP+HOLD indicator (accent border/glow) |

### ARP Hold Indicator

Slots with an active ARP+HOLD (engine running while overlay closed) need a visual indicator. Options:

- **Slot button glow** — accent color border on the target row button
- **Generator grid badge** — small "ARP" badge on the slot in the main UI
- Both

The generator grid badge is important because the user needs to see which slots have running arps **when the keyboard is closed**.

### ARP Controls

No change to controls (Rate, Pattern, Oct, Hold). They simply read/write the focused slot's engine instead of a shared engine.

---

## State Diagram

```
Per-slot ArpEngine lifecycle:

    ┌──────────┐
    │  IDLE    │ ← engine created, no ARP activity
    └────┬─────┘
         │ toggle_arp(true)
    ┌────▼─────┐
    │ ARP ON   │ ← accepting keys, stepping
    └────┬─────┘
         │ toggle_hold(true) + keys latched
    ┌────▼─────┐
    │ ARP+HOLD │ ← latched notes, keyboard can close
    └────┬─────┘
         │ keyboard closes
    ┌────▼─────┐
    │ DETACHED │ ← engine runs independently, overlay gone
    └────┬─────┘
         │ keyboard reopens + slot refocused
    ┌────▼─────┐
    │ ARP+HOLD │ ← UI reconnects, user can modify or release
    └────┬─────┘
         │ toggle_hold(false) + no physical keys
    ┌────▼─────┐
    │ TEARDOWN │ → note-off, timers stopped, state reset
    └──────────┘
```

---

## Migration Path

### Phase 1: ArpSlotManager + Single-Slot Engine

1. Create `ArpSlotManager` class
2. Modify `ArpEngine` to target a single slot (remove multi-target)
3. Move engine ownership from overlay to controller
4. Overlay gets `set_arp_engine()` / `sync_ui_from_engine()`
5. Target row becomes single-select

**Test:** Keyboard works as before but with single-slot targeting. No persistence yet.

### Phase 2: ARP+HOLD Persistence

1. `_dismiss()` preserves engines with ARP+HOLD
2. `_show_overlay()` syncs UI from focused engine (may be mid-arp)
3. Focus switching releases keys from old engine, binds new engine
4. Pack change / generator change triggers targeted teardown

**Test:** Set up ARP+HOLD on slot 1, close keyboard, hear it continue. Reopen, see state. Turn off hold, it stops.

### Phase 3: Visual Indicators

1. ARP badge on generator grid slots
2. Accent border on target row buttons for active holds
3. Status in console log

**Test:** Visual confirmation of which slots have active arps.

---

## Files Affected

| File | Change |
|------|--------|
| `src/gui/arp_engine.py` | Remove multi-target, add `slot_id` binding |
| `src/gui/keyboard_overlay.py` | Remove engine ownership, add `set_arp_engine()`, single-select targets |
| `src/gui/controllers/keyboard_controller.py` | Add `ArpSlotManager`, engine lifecycle, focus switching |
| `src/gui/generator_grid.py` | ARP badge indicator on slots (Phase 3) |
| `src/gui/main_frame.py` | Wire teardown on pack change / generator change |

---

## Invariants

1. **One engine per slot** — slot 0 always maps to engines[0], never shared
2. **Monophonic per engine** — at most one ARP note sounding per slot at any time
3. **No stuck notes** — teardown always sends note-off before clearing state
4. **Overlay is stateless** — all ARP state lives in engines, overlay just reads/writes
5. **Focus is exclusive** — overlay controls exactly one engine at a time
6. **Hold survives hide** — ARP+HOLD engine keeps running when overlay is hidden
7. **Pack change kills all** — all engines torn down on pack/preset load
8. **Generator change kills one** — changing a slot's generator tears down only that slot's engine

---

## Open Questions

1. **Eager vs lazy engine creation** — Create all 8 at startup, or only when a slot first gets ARP enabled? Lazy saves memory but adds complexity.

2. **Multi-slot broadcast** — Should there be a way to play keys to multiple slots simultaneously (current behavior)? Could add a "LINK" mode that temporarily routes keys to multiple engines. Deferred for now — single-slot is the clean foundation.

3. **Preset save/load** — Should per-slot ARP state be saved in presets? Currently ARP is session-only. Saving hold patterns could be powerful but adds schema complexity. Recommend: defer to future version.

4. **BPM notification** — Currently overlay forwards BPM changes. With per-slot engines, the ArpSlotManager should forward BPM to all active engines, not just the focused one.
