# ARP Start Sync (Per-Slot) — Implementation Spec

---
status: spec
version: 1.1
date: 2025-02-08
builds-on: EUCLID_ARP_GATE_SPEC v3.1, CLOCK_FABRIC.md, MotionManager.on_fabric_tick(), ArpEngine master_tick()
size: Small-Medium (1-2 days)
---

## Invariant

**ARP Start Sync must be a pure gate on ARP step emission only.**
It must not change any generator timing or any other slot's state.

---

## What

Add a **per-slot ARP "Start Sync"** feature:

* User can **arm** an ARP slot while playing/holding keys.
* The ARP **does not emit or advance** until the next occurrence of a **selected fabric tick** (`start_ref_idx`) for that slot.
* On the selected tick, ARP starts **phase-clean** (step 0, euclid step 0) and plays its first step on that tick time.

This is **not a new clock**. It is a per-slot choice of **which existing fabric tick counts as "start now"**.

---

## Core Principle

**One clock fabric.**
Per slot, ARP chooses:

1. **Step clock**: existing ARP rate (already unified via fabric ticks + 1/12 fallback)
2. **Start reference**: a fabric index (4-9) used only to decide when to begin

---

## Phase 0 — Fabric tick availability (keep OSC traffic low)

Default policy: **do not expand tick broadcast to 0..12**.

Start references are intended to be musically meaningful and low-rate:
- `/4` (bar), `/2`, `CLK`, `x2`, `x4`, `x8` -> indices **4-9** (already broadcast)

These are sufficient for "start on bar/beat/subdivision".

If we later need `/8` (idx 3) or other indices as start references, expand the broadcast set minimally (add only what's needed). Avoid high-rate indices (e.g. `x32`) because they significantly increase SC->Python OSC message rate.

Therefore:
- Keep broadcast set **[4,5,6,7,8,9]** for v1.0
- Only extend by explicit request / measured need

No SC changes required for this phase.

---

## Phase 1 — Engine: Per-slot Start Sync gate

### Behavior (authoritative)

When **start sync is armed**:

* ARP accepts keys / HOLD behavior normally (note pool updates)
* ARP produces **no note output**
* ARP does **not advance** step index
* ARP ignores:
  * `master_tick()` events
  * fallback timer fires (covers 1/12 triplet AUTO path)

When the selected **start reference tick** arrives:

* If slot is in ARP mode and start sync is armed:
  * If no notes are held: **remain armed** (do not disarm, no step executed)
  * If notes are held:
    * Disarm
    * Reset phase: `current_step_index = 0`, `euclid_step = 0`
    * Attempt to play **exactly one** step on that tick time (respects Euclid gate)
    * Subsequent ticks proceed normally

The "no notes = stay armed" rule prevents "armed-start consumes itself but nothing plays".

---

### Step 1.1: ArpSettings field

**File:** `src/gui/arp_engine.py`

Add to `ArpSettings`:

```python
start_ref_idx: int = 4  # fabric index for start sync (default /4 = bar)
```

### Step 1.2: ArpRuntime field

Add to `ArpRuntime`:

```python
start_sync_armed: bool = False
```

---

### Step 1.3: New event types + public API

Add to `ArpEventType`:

```python
START_SYNC_SET = auto()
START_REF_SET = auto()
START_REF_TICK = auto()
```

Add public methods to `ArpEngine`:

```python
def set_start_sync(self, enabled: bool):
    """Arm or disarm start sync."""
    self.post_event(ArpEvent(ArpEventType.START_SYNC_SET, {"enabled": bool(enabled)}))

def set_start_ref(self, fabric_idx: int):
    """Set the fabric index used as start reference."""
    self.post_event(ArpEvent(ArpEventType.START_REF_SET, {"fabric_idx": int(fabric_idx)}))

def start_ref_tick(self, tick_time_ms: float):
    """Called by MotionManager when the slot's start_ref_idx fabric tick fires."""
    self.post_event(ArpEvent(ArpEventType.START_REF_TICK, {"tick_time_ms": float(tick_time_ms)}))
```

---

### Step 1.4: Event handlers

Register all three in `_dispatch_event` handlers dict.

#### A) `_handle_start_sync_set`

```python
def _handle_start_sync_set(self, event: ArpEvent):
    en = bool(event.data.get("enabled", False))
    self.runtime.start_sync_armed = en
    if en:
        self.runtime.current_step_index = 0
        self.runtime.euclid_step = 0
        self._stop_fallback()
```

Uses `_stop_fallback()` (not direct field access) — this bumps fallback_generation and stops the timer cleanly.

#### B) `_handle_start_ref_set`

```python
def _handle_start_ref_set(self, event: ArpEvent):
    idx = int(event.data.get("fabric_idx", 4))
    self.settings.start_ref_idx = max(0, min(12, idx))
```

#### C) `_handle_start_ref_tick`

```python
def _handle_start_ref_tick(self, event: ArpEvent):
    if not self.runtime.start_sync_armed:
        return

    tick_time_ms = float(event.data.get("tick_time_ms", 0.0))
    if tick_time_ms <= 0:
        return

    # If no notes available, stay armed and do nothing
    if not self._has_playable_notes():
        return

    # Disarm and reset phase (defensive)
    self.runtime.start_sync_armed = False
    self.runtime.current_step_index = 0
    self.runtime.euclid_step = 0

    # Fire exactly one step on this tick (still respects euclid)
    if self._euclid_gate():
        self._execute_step(tick_time_ms)
```

### Playability check (uses existing note-set selection)

The engine's existing `_get_active_set()` returns `physical_held` or `latched` depending on hold mode. Reuse it:

```python
def _has_playable_notes(self) -> bool:
    return len(self._get_active_set()) > 0
```

This matches what `_execute_step()` uses indirectly via `_get_expanded_list()`.

---

### Step 1.5: Gate tick handlers while armed

In `_handle_master_tick` (top, before any rate matching):

```python
if self.runtime.start_sync_armed:
    return
```

In `_handle_fallback_fire` (top, after generation check):

```python
if self.runtime.start_sync_armed:
    return
```

**Invariant:** while armed, nothing can produce steps.

---

### Teardown

`start_sync_armed` resets naturally on teardown because `_handle_teardown` replaces runtime with a fresh `ArpRuntime()` instance. No explicit reset needed.

---

## Phase 2 — MotionManager: per-slot start reference routing

### Step 2.1: Deliver start ref ticks

**File:** `src/gui/motion_manager.py`

`start_ref_idx` lives in `ArpSettings` (Option B — all ARP state consolidated in the engine). MotionManager reads it at dispatch time.

Update `on_fabric_tick()`:

```python
def on_fabric_tick(self, fabric_idx: int):
    """Handle clock fabric tick from SC. Route to matching ARP slots."""
    now_ms = time.monotonic() * 1000.0

    for slot in self._slots:
        if slot['lock'].acquire(blocking=False):
            try:
                if slot['mode'] == MotionMode.ARP:
                    # Start ref tick (before master_tick — downbeat can both start and step)
                    ref_idx = slot['arp'].settings.start_ref_idx
                    if fabric_idx == ref_idx:
                        slot['arp'].start_ref_tick(now_ms)

                    # Normal ARP rate tick
                    arp_rate = FABRIC_IDX_TO_ARP_RATE.get(fabric_idx)
                    if arp_rate is not None:
                        slot['arp'].master_tick(arp_rate, now_ms)
            finally:
                slot['lock'].release()
```

**Key changes from current code:**
- Removed the early return when `arp_rate is None` — must still check `start_ref_idx` for every fabric tick
- `start_ref_tick` fires before `master_tick` so the downbeat tick can both disarm and allow immediate continuation
- `settings.start_ref_idx` is a plain int read — safe without additional locking (written only by engine event loop on same Qt thread)

---

## Phase 3 — UI: per-slot controls in CMD+K

### Step 3.1: KeyboardOverlay additions

**File:** `src/gui/keyboard_overlay.py`

Add UI widget declarations in `__init__`:

```python
# Start sync UI elements
self._arp_arm_btn: QPushButton = None
self._arp_ref_btn = None  # CycleButton
```

Add widgets in `_create_arp_controls()`, after Euclidean controls, before `addStretch()`:

```python
layout.addSpacing(12)

# ARM toggle
self._arp_arm_btn = QPushButton("ARM")
self._arp_arm_btn.setCheckable(True)
self._arp_arm_btn.setFixedSize(44, 24)
self._arp_arm_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
self._arp_arm_btn.setToolTip("Arm start sync (waits for REF tick)")
self._arp_arm_btn.clicked.connect(self._on_arm_changed)
layout.addWidget(self._arp_arm_btn)

layout.addSpacing(4)

# REF selector (fabric rate labels for indices 4-9)
ref_label = QLabel("REF:")
ref_label.setFont(QFont(FONT_FAMILY, 9))
layout.addWidget(ref_label)

ref_labels = ["/4", "/2", "CLK", "x2", "x4", "x8"]  # indices 4-9
self._arp_ref_btn = CycleButton(ref_labels, 0)  # Default /4 (index 0 = fabric 4)
self._arp_ref_btn.setFixedSize(44, 24)
self._arp_ref_btn.setFont(QFont(FONT_FAMILY, 9))
self._arp_ref_btn.setToolTip("Start sync reference rate")
self._arp_ref_btn.index_changed.connect(self._on_ref_changed)
layout.addWidget(self._arp_ref_btn)
```

### Step 3.2: Handlers

```python
def _on_arm_changed(self):
    """Handle ARM toggle."""
    if self._arp_engine is None:
        self._arp_arm_btn.setChecked(False)
        return
    self._arp_engine.set_start_sync(self._arp_arm_btn.isChecked())

def _on_ref_changed(self, index: int):
    """Handle REF rate change."""
    if self._arp_engine is None:
        return
    # CycleButton index 0-5 maps to fabric index 4-9
    fabric_idx = index + 4
    self._arp_engine.set_start_ref(fabric_idx)
```

### Step 3.3: Sync UI from engine

In `sync_ui_from_engine()`, add after Euclidean controls sync:

```python
# Start sync controls
self._arp_arm_btn.setChecked(engine.runtime.start_sync_armed)
ref_ui_idx = max(0, min(5, settings.start_ref_idx - 4))
self._arp_ref_btn.set_index(ref_ui_idx)
```

### ARM auto-disarm UI sync

When `start_sync_armed` becomes false due to `START_REF_TICK`, the overlay must reflect this.

The overlay already has `_grid_refresh_timer` (50ms) for SEQ playhead updates. When ARP is active and the overlay is visible, piggyback on this existing timer to poll `engine.runtime.start_sync_armed` and update the ARM button:

```python
# In _refresh_step_grid() or a similar periodic callback:
if self._arp_engine is not None and self._arp_arm_btn is not None:
    armed = self._arp_engine.runtime.start_sync_armed
    if self._arp_arm_btn.isChecked() != armed:
        self._arp_arm_btn.setChecked(armed)
```

Do not add new timers solely for this feature.

---

## Do NOT

* Do not create a second timer/clock
* Do not tie "bar start" to generator 1
* Do not advance ARP while armed
* Do not add probability/ratchets/swing here
* Do not add global state: start ref must be per-slot
* Do not expand SC broadcast set beyond [4-9] without measured need

---

## Testing

1. **Basic start sync**
   * Set slot ARP rate = 1/16, REF = /4
   * ARM, hold notes
   * Confirm no notes until next /4 tick
   * On tick: first note plays and continues at 1/16

2. **Euclid alignment**
   * Enable EUC N=16 K=5
   * ARM with REF=/4
   * Confirm first fired step corresponds to Euclid step 0 (repeatable start)

3. **1/12 fallback**
   * Set rate = 1/12, ARM with REF=/4
   * Confirm no output while armed (fallback suppressed)
   * On /4 tick: start, then continue via fallback timer

4. **No notes = stay armed**
   * ARM, REF=/4, no notes held
   * At /4 tick: remains armed, no output
   * Add notes later: starts on next REF tick

5. **Per-slot independence**
   * Slot 1 REF=/4, Slot 5 REF=x2
   * ARM both, hold notes
   * Confirm each starts on its own boundary

6. **ARP off while armed**
   * ARM, then toggle ARP off
   * Teardown replaces runtime: armed state gone (clean slate)
   * Toggle ARP back on: not armed (fresh runtime)

---

## Files Changed

### Python

* `src/gui/arp_engine.py` — start sync gate: events, settings, runtime, handlers, `_has_playable_notes()`
* `src/gui/motion_manager.py` — deliver `start_ref_tick` before `master_tick` in `on_fabric_tick()`
* `src/gui/keyboard_overlay.py` — ARM + REF controls, handlers, sync, auto-disarm poll
