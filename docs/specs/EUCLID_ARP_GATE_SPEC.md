# Euclidean ARP Gate — Implementation Spec

---
status: spec
version: 1.0
date: 2025-02-08
builds-on: PER_SLOT_ARP_SPEC v2.0, arp_engine.py, keyboard_overlay.py
size: Small (<1 day)
---

## What

Add a Euclidean rhythm gate to the per-slot arpeggiator. When enabled, the ARP skips steps according to a Euclidean pattern (N steps, K fills, rotation), creating rhythmically interesting sparse patterns from the existing ARP clock.

## Architecture Assessment

### Critical finding: ARP is Python-based, not SC-based

The original proposal assumed ARP stepping happens in SuperCollider via `clockTrigBus`. **This is not the case.** The actual architecture:

```
MotionManager (Python, 10ms QTimer)
  └── rate phase accumulators (7 rates)
       └── master_tick(rate_idx, tick_time_ms)
            └── ArpEngine._handle_master_tick()
                 └── _execute_step()     ← plays the note
                      └── OSC note_on/off → SuperCollider
```

SC's `clockTrigBus` (13 audio-rate triggers) is used only by the **generator envelope system** (`~envVCA` helper), not by the ARP. The ARP lives entirely in Python.

### Correct approach: Python-side Euclidean gate

The Euclidean gate belongs in `ArpEngine._handle_master_tick()`, gating whether `_execute_step()` fires. This:

- Uses the existing phase-locked clock (MotionManager's BPM-synced ticks) — **no new timers**
- Does not advance the ARP step counter on misses — **pattern stays phase-coherent**
- Adds only 4 parameters per engine (enable, N, K, rot) — **no new interactions**
- Requires zero SuperCollider changes — **no SC modifications**
- Requires zero new OSC paths — **parameters are per-engine Python state**

### Why not SC-side

Moving the Euclidean gate to SC would require either:
1. Moving ARP stepping to SC (massive architectural change, violates PER_SLOT_ARP_SPEC), or
2. Adding a SC-side gate that feeds back into Python timing (round-trip latency, complexity)

Neither is justified for what is fundamentally a "should I play this step?" boolean decision.

---

## Implementation Steps

### Step 1: Add Euclidean hit function (pure math)

**File:** `src/gui/arp_engine.py`
**Location:** After the rate configuration constants (after line ~78)

```python
def euclidean_hit(step: int, n: int, k: int, rotation: int = 0) -> bool:
    """Return True if this step is a 'hit' in a Euclidean rhythm.

    Uses the Bresenham/floor method (equivalent to Bjorklund but O(1) per step).
    n: total steps (1..64)
    k: number of fills/hits (0..n)
    rotation: pattern rotation (0..n-1)
    """
    if k <= 0:
        return False
    if k >= n:
        return True
    i = (step + rotation) % n
    # Hit when floor(i*k/n) != floor((i-1)*k/n), i.e., threshold crossing
    return (i * k) // n != (((i - 1) * k) // n) if i > 0 else (0 != (((n - 1) * k) // n))
```

**Note:** This is the same math as the original SC proposal (`floor(i*k/n)` threshold crossing), just in Python. O(1) per step, no arrays, no Bjorklund recursion.

### Step 2: Add Euclidean settings to ArpSettings

**File:** `src/gui/arp_engine.py`
**Location:** `ArpSettings` dataclass (line ~163)

Add four fields:

```python
@dataclass
class ArpSettings:
    """User-configurable ARP settings."""
    enabled: bool = False
    rate_index: int = ARP_DEFAULT_RATE_INDEX
    pattern: ArpPattern = ARP_DEFAULT_PATTERN
    octaves: int = ARP_DEFAULT_OCTAVES
    hold: bool = False
    # Euclidean gate
    euclid_enabled: bool = False
    euclid_n: int = 16       # Total steps (1..64)
    euclid_k: int = 5        # Fills/hits (0..euclid_n)
    euclid_rot: int = 0      # Rotation (0..euclid_n-1)
```

### Step 3: Add Euclidean step counter to ArpRuntime

**File:** `src/gui/arp_engine.py`
**Location:** `ArpRuntime` dataclass (line ~177)

Add one field:

```python
    # Euclidean gate step counter (advances on every eligible tick, independent of ARP step)
    euclid_step: int = 0
```

### Step 4: Gate `_execute_step()` in `_handle_master_tick()`

**File:** `src/gui/arp_engine.py`
**Location:** `_handle_master_tick()` method (line ~839)

The key change: when the rate matches and we would normally call `_execute_step()`, first check the Euclidean gate. If the gate says "miss", **do not call `_execute_step()`** (which means the ARP step counter does NOT advance — pattern stays coherent).

**Current code** (lines 851-853):
```python
        if self.runtime.clock_mode == ClockMode.MASTER:
            if rate_index == self.settings.rate_index:
                self._execute_step(tick_time_ms)
```

**Replace with:**
```python
        if self.runtime.clock_mode == ClockMode.MASTER:
            if rate_index == self.settings.rate_index:
                if self._euclid_gate():
                    self._execute_step(tick_time_ms)
```

Apply the same pattern to the AUTO→MASTER promotion path (lines 855-867). The `_execute_step(tick_time_ms)` call on line 867 also needs the gate:

```python
                if self._euclid_gate():
                    self._execute_step(tick_time_ms)
```

### Step 5: Implement `_euclid_gate()` method

**File:** `src/gui/arp_engine.py`
**Location:** Add as a new private method near `_execute_step()` (around line ~960)

```python
    def _euclid_gate(self) -> bool:
        """Check Euclidean gate and advance euclid step counter.

        Returns True if this step should fire (hit), False if skip (miss).
        Always advances the euclid step counter — the ARP step counter
        only advances when this returns True (inside _execute_step).
        """
        if not self.settings.euclid_enabled:
            return True  # Bypass — all steps fire

        n = max(1, min(64, self.settings.euclid_n))
        k = max(0, min(n, self.settings.euclid_k))
        rot = max(0, min(n - 1, self.settings.euclid_rot))

        hit = euclidean_hit(self.runtime.euclid_step, n, k, rot)
        self.runtime.euclid_step += 1
        return hit
```

### Step 6: Reset euclid_step on teardown

**File:** `src/gui/arp_engine.py`
**Location:** `teardown()` method (line ~930)

The existing `teardown()` already resets `self.runtime = ArpRuntime()` which creates a fresh runtime with `euclid_step = 0`. **No change needed** — it's handled by the dataclass default.

Verify this is true by checking that `teardown()` does `self.runtime = ArpRuntime()` (line ~950).

### Step 7: Add public setters for Euclidean params

**File:** `src/gui/arp_engine.py`
**Location:** Near the existing `set_rate()`, `set_pattern()`, `set_octaves()` methods

Add methods that the UI will call. These should go through the event queue for thread safety, following the same pattern as `set_rate()`:

```python
    def set_euclid_enabled(self, enabled: bool):
        """Toggle Euclidean gate."""
        self._post_event(ArpEventType.EUCLID_ENABLE, {"enabled": enabled})

    def set_euclid_n(self, n: int):
        """Set Euclidean total steps (1..64)."""
        self._post_event(ArpEventType.EUCLID_N, {"n": n})

    def set_euclid_k(self, k: int):
        """Set Euclidean fills (0..N)."""
        self._post_event(ArpEventType.EUCLID_K, {"k": k})

    def set_euclid_rot(self, rot: int):
        """Set Euclidean rotation (0..N-1)."""
        self._post_event(ArpEventType.EUCLID_ROT, {"rot": rot})
```

Add corresponding `ArpEventType` enum values and handlers in `_process_event()`:

```python
class ArpEventType(Enum):
    # ... existing ...
    EUCLID_ENABLE = auto()
    EUCLID_N = auto()
    EUCLID_K = auto()
    EUCLID_ROT = auto()
```

Each handler simply updates `self.settings.euclid_*` and optionally resets `self.runtime.euclid_step = 0` when N changes (to avoid stale counter positions).

### Step 8: Add CMD+K UI controls

**File:** `src/gui/keyboard_overlay.py`
**Location:** `_create_arp_controls()` method (line ~414)

Add Euclidean controls to the existing ARP controls row. Insert after the HOLD button (line ~476):

```python
        layout.addSpacing(12)

        # Euclidean gate controls
        self._euc_toggle_btn = QPushButton("EUC")
        self._euc_toggle_btn.setCheckable(True)
        self._euc_toggle_btn.setFixedSize(40, 24)
        self._euc_toggle_btn.setFont(QFont(FONT_FAMILY, 9))
        self._euc_toggle_btn.setToolTip("Euclidean rhythm gate")
        self._euc_toggle_btn.clicked.connect(self._on_euc_toggle)
        layout.addWidget(self._euc_toggle_btn)

        euc_n_label = QLabel("N:")
        euc_n_label.setFont(QFont(FONT_FAMILY, 9))
        layout.addWidget(euc_n_label)

        self._euc_n_btn = CycleButton(
            [str(i) for i in range(1, 65)], 15  # default index 15 = N=16
        )
        self._euc_n_btn.setFixedSize(36, 24)
        self._euc_n_btn.setFont(QFont(FONT_FAMILY, 9))
        self._euc_n_btn.setToolTip("Total steps (1-64)")
        self._euc_n_btn.index_changed.connect(self._on_euc_n_changed)
        layout.addWidget(self._euc_n_btn)

        euc_k_label = QLabel("K:")
        euc_k_label.setFont(QFont(FONT_FAMILY, 9))
        layout.addWidget(euc_k_label)

        self._euc_k_btn = CycleButton(
            [str(i) for i in range(0, 65)], 5  # default index 5 = K=5
        )
        self._euc_k_btn.setFixedSize(36, 24)
        self._euc_k_btn.setFont(QFont(FONT_FAMILY, 9))
        self._euc_k_btn.setToolTip("Fills/hits (0-N)")
        self._euc_k_btn.index_changed.connect(self._on_euc_k_changed)
        layout.addWidget(self._euc_k_btn)

        euc_rot_label = QLabel("R:")
        euc_rot_label.setFont(QFont(FONT_FAMILY, 9))
        layout.addWidget(euc_rot_label)

        self._euc_rot_btn = CycleButton(
            [str(i) for i in range(0, 64)], 0  # default = 0
        )
        self._euc_rot_btn.setFixedSize(36, 24)
        self._euc_rot_btn.setFont(QFont(FONT_FAMILY, 9))
        self._euc_rot_btn.setToolTip("Rotation (0 to N-1)")
        self._euc_rot_btn.index_changed.connect(self._on_euc_rot_changed)
        layout.addWidget(self._euc_rot_btn)
```

**Important:** The `layout.addStretch()` at line 478 should remain at the end (after the Euclid controls).

### Step 9: Add overlay event handlers

**File:** `src/gui/keyboard_overlay.py`
**Location:** Near the existing `_on_rate_changed()`, `_on_pattern_changed()` methods

```python
    def _on_euc_toggle(self, checked):
        if self._arp_engine:
            self._arp_engine.set_euclid_enabled(checked)

    def _on_euc_n_changed(self, index):
        if self._arp_engine:
            n = index + 1  # index 0 = N=1, index 15 = N=16, etc.
            self._arp_engine.set_euclid_n(n)

    def _on_euc_k_changed(self, index):
        if self._arp_engine:
            self._arp_engine.set_euclid_k(index)  # index 0 = K=0

    def _on_euc_rot_changed(self, index):
        if self._arp_engine:
            self._arp_engine.set_euclid_rot(index)  # index 0 = rot=0
```

### Step 10: Add Euclidean state to `sync_ui_from_engine()`

**File:** `src/gui/keyboard_overlay.py`
**Location:** `sync_ui_from_engine()` method (line ~249)

After the existing ARP control syncing (line ~277), add:

```python
        # Euclidean gate controls
        self._euc_toggle_btn.setChecked(settings.euclid_enabled)
        self._euc_n_btn.set_index(settings.euclid_n - 1)  # N=1 → index 0
        self._euc_k_btn.set_index(settings.euclid_k)
        self._euc_rot_btn.set_index(settings.euclid_rot)
```

---

## What NOT to do

- **No SuperCollider changes** — ARP is Python-side, Euclid gate belongs with it
- **No new OSC paths** — Euclidean parameters are per-engine Python state, not sent to SC
- **No new timers** — uses existing MotionManager clock ticks
- **No probability/ratchets/swing/gate-length** — ship only N/K/ROT + enable
- **No changes to generator SynthDefs or helpers.scd** — ARP sends note_on/note_off, generators don't know about ARP at all
- **Do not grey out clock rate buttons** — Euclid ON means "ticks are sparser", clock rate stays independent
- **Do not advance ARP step counter on Euclid misses** — this happens naturally because `_execute_step()` is skipped (it contains the `current_step_index += 1` logic inside `_select_next_note()`)

## Files Changed

| File | Change |
|------|--------|
| `src/gui/arp_engine.py` | `euclidean_hit()` function, `ArpSettings` fields, `ArpRuntime.euclid_step`, `_euclid_gate()` method, `_handle_master_tick()` gating, event types + handlers, public setters |
| `src/gui/keyboard_overlay.py` | `_create_arp_controls()` adds EUC/N/K/R widgets, event handlers, `sync_ui_from_engine()` syncs Euclid state |

## Testing

1. Open CMD+K, enable ARP with a chord held
2. Enable EUC — pattern should become sparser
3. Change N/K/ROT — pattern changes immediately
4. Verify step counter does NOT advance on misses (UP pattern should skip positions, not condense)
5. Switch slots — Euclid settings preserved per-slot (part of ArpSettings)
6. Close/reopen keyboard with HOLD — Euclid settings restored from engine state
7. Test edge cases: K=0 (silence), K=N (all hits, same as EUC off), N=1/K=1

## Preset Integration

Euclidean settings are part of `ArpSettings` which is per-engine in-memory state. If/when ARP state is added to preset save/load, the four Euclid fields should be included. No action needed now — presets don't currently save ARP state.
