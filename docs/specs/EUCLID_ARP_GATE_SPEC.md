# ARP Clock Unification + Euclidean Gate — Implementation Spec

---
status: spec
version: 2.0
date: 2025-02-08
builds-on: PER_SLOT_ARP_SPEC v2.0, CLOCK_FABRIC.md, arp_engine.py
size: Medium (2-3 days)
---

## What

Two tightly-coupled changes:

1. **Clock Unification** — Replace MotionManager's parallel Python clock (10ms QTimer + rate phase accumulators) with SC fabric tick broadcast via SendReply→OSC. ARP stepping becomes truly phase-locked to the master clock.

2. **Euclidean ARP Gate** — Add N/K/ROT gate to the ARP, applied in Python after receiving fabric ticks. Ships only the simple gate (no probability/ratchets/swing).

Phase 1 is the priority. Phase 2 builds on top.

---

## Problem: Parallel Clock

MotionManager currently maintains its own timing system that duplicates the SC clock fabric:

```
SC (authoritative):          Python (parallel duplicate):
masterClock SynthDef         MotionManager._on_clock_tick() [10ms QTimer]
  → Impulse.ar(bpm/60*mult)   → dt = now - last_tick_time
  → 13 audio-rate triggers     → tick_duration_beats = (bpm/60) * dt
  → clockTrigBus               → _rate_phases[i] += tick_duration_beats
                                → if phase >= beats_per_step → master_tick()
```

This violates the Clock Fabric decision (DECISIONS.md `[2025-02-07]`):
> *"Clock consumers must select from these channels, not create independent divider chains."*

**Consequences of the parallel clock:**
- Phase drift between ARP and SC envelope triggers on BPM changes
- Two independent BPM→division math paths that can diverge
- 10ms QTimer polling adds up to 10ms latency on ARP step delivery

---

## Phase 1: Clock Unification

### Architecture (After)

```
SC masterClock → Impulse.ar (13 rates) → clockTrigBus
                                              ↓
                                    clockTickBroadcast synth
                                    (SendReply on each rate trigger)
                                              ↓
                                    OSCdef relay → /noise/clock/tick [rateIdx]
                                              ↓
                                    Python OSC bridge → clock_tick_received signal
                                              ↓
                                    MotionManager._on_fabric_tick(fabric_idx)
                                              ↓
                                    ARP rate lookup → engine.master_tick()
```

SEQ engine stays on QTimer (needs continuous delta-beat accumulator, different timing model).

### Rate Mapping: ARP ↔ Fabric

| ARP idx | ARP label | Beats/step | Musical         | Fabric mult | Fabric idx | Notes           |
|---------|-----------|------------|-----------------|-------------|------------|-----------------|
| 0       | 1/32      | 0.125      | 32nd note       | x8          | 9          | Direct match    |
| 1       | 1/16      | 0.25       | 16th note       | x4          | 8          | Direct match    |
| 2       | 1/12      | 0.333      | Triplet 8th     | x12         | 10         | Fire every 4th  |
| 3       | 1/8       | 0.5        | 8th note        | x2          | 7          | Direct match    |
| 4       | 1/4       | 1.0        | Quarter note    | CLK         | 6          | Direct match    |
| 5       | 1/2       | 2.0        | Half note       | /2          | 5          | Direct match    |
| 6       | 1 bar     | 4.0        | Whole note      | /4          | 4          | Direct match    |

**The 1/12 case:** Fabric has no x3 rate. Use x12 (12/beat) and fire the ARP every 4th tick → 3/beat = triplet 8ths. This is a legitimate consumption pattern per CLOCK_FABRIC.md ("Clock Divider Chains: skip N triggers, emit 1").

### Step 1.1: SC — Add clock tick broadcast synth

**File:** `supercollider/core/clock.scd`
**Location:** After `~setupClock`, add `~setupClockBroadcast`

```supercollider
// Clock tick broadcast — notifies Python when fabric triggers fire
// Only broadcasts the 7 rates that ARP/SEQ consumers need (fabric indices 4-10)
~setupClockBroadcast = {
    SynthDef(\clockTickBroadcast, { |clockTrigBus|
        var allTrigs = In.ar(clockTrigBus, 13);

        // Broadcast fabric indices 4-10 (covers /4 through x12)
        // Each SendReply fires once per trigger edge
        [4, 5, 6, 7, 8, 9, 10].do { |idx|
            var trigK = A2K.kr(Trig1.ar(allTrigs[idx], ControlDur.ir * 2));
            SendReply.kr(trigK, '/clock/tick', [idx]);
        };
    }).add;

    "  [x] ClockTickBroadcast SynthDef ready".postln;
};
```

**Why indices 4-10 only:** Covers all 7 ARP rates. Indices 0-3 (/32 through /8) are very slow (2-16 seconds at 120 BPM) and aren't needed for ARP. Indices 11-12 (x16, x32) are very fast and not used. Can expand later if needed.

**Why a separate synth:** Keeps masterClock pure (just generates triggers), follows the existing separation pattern (masterClock vs masterPassthrough).

### Step 1.2: SC — Add OSCdef relay to Python

**File:** `supercollider/core/osc_handlers.scd`
**Location:** Near existing meter/telemetry forwarding OSCdefs

```supercollider
// Clock tick relay to Python (from clockTickBroadcast SendReply)
OSCdef(\clockTickForward, { |msg|
    if(~pythonAddr.notNil) {
        ~pythonAddr.sendMsg('/noise/clock/tick', msg[3].asInteger);
    };
}, '/clock/tick');
```

### Step 1.3: SC — Start the broadcast synth

**File:** `supercollider/core/clock.scd`
**Location:** Inside `~startClock`, after `~clockSynth` creation

```supercollider
~clockBroadcastSynth = Synth(\clockTickBroadcast, [
    \clockTrigBus, ~clockTrigBus.index
], ~clockGroup);

"  [x] Clock tick broadcast running".postln;
```

### Step 1.4: Python — Add OSC path constant

**File:** `src/config/__init__.py`
**Location:** In `OSC_PATHS` dict

```python
'clock_tick': '/noise/clock/tick',
```

### Step 1.5: Python — Add OSC bridge handler + signal

**File:** `src/audio/osc_bridge.py`

Add signal:
```python
clock_tick_received = pyqtSignal(int)  # fabric_idx (4-10)
```

Add handler:
```python
def _handle_clock_tick(self, address, *args):
    """Handle clock fabric tick from SC."""
    if self._shutdown or self._deleted:
        return
    if len(args) >= 1:
        fabric_idx = int(args[0])
        self.clock_tick_received.emit(fabric_idx)
```

Register in dispatcher (inside `_start_server()`):
```python
dispatcher.map(OSC_PATHS['clock_tick'], self._handle_clock_tick)
```

### Step 1.6: Python — Add rate mapping constant

**File:** `src/config/__init__.py`
**Location:** Near existing ARP constants or clock constants

```python
# ARP rate index → clock fabric index
# Maps each ARP rate to the fabric trigger channel it should consume
ARP_RATE_TO_FABRIC_IDX = {
    0: 9,   # 1/32 (32nd note)    → fabric x8
    1: 8,   # 1/16 (16th note)    → fabric x4
    2: 10,  # 1/12 (triplet 8th)  → fabric x12 (fire every 4th)
    3: 7,   # 1/8  (8th note)     → fabric x2
    4: 6,   # 1/4  (quarter note) → fabric CLK
    5: 5,   # 1/2  (half note)    → fabric /2
    6: 4,   # 1 bar (whole note)  → fabric /4
}

# Inverse: fabric index → list of ARP rate indices that consume it
FABRIC_IDX_TO_ARP_RATES = {}
for arp_idx, fab_idx in ARP_RATE_TO_FABRIC_IDX.items():
    FABRIC_IDX_TO_ARP_RATES.setdefault(fab_idx, []).append(arp_idx)

# Triplet 8th (ARP rate 2) uses x12 fabric, firing every 4th tick
ARP_TRIPLET_RATE_IDX = 2
ARP_TRIPLET_FABRIC_DIVISOR = 4  # x12 / 4 = 3 per beat = triplet 8th
```

### Step 1.7: Python — Rewire MotionManager

**File:** `src/gui/motion_manager.py`

**Remove:**
- `_rate_phases` list (line 104)
- Rate phase accumulation logic in `on_tick()` (lines 164-170)
- The `rates_crossed` variable and its usage in the ARP tick delivery (lines 165-170, 187-189)

**Add:**
- Triplet sub-counter: `_triplet_tick_count: int = 0`
- New method `on_fabric_tick(fabric_idx, tick_time_ms)` that replaces the rate-crossing detection

```python
def on_fabric_tick(self, fabric_idx: int):
    """Handle a clock fabric tick from SC (via OSC bridge).

    Maps fabric index to ARP rate index and fires master_tick()
    on all ARP-mode slots whose rate matches.
    """
    now_ms = time.monotonic() * 1000.0

    # Triplet handling: x12 fires 12/beat, ARP wants 3/beat → every 4th
    if fabric_idx == 10:  # x12
        self._triplet_tick_count += 1
        if self._triplet_tick_count % ARP_TRIPLET_FABRIC_DIVISOR != 0:
            return  # Skip — not a triplet 8th boundary yet
        # Fall through to deliver as ARP rate 2

    # Look up which ARP rates this fabric tick satisfies
    arp_rates = FABRIC_IDX_TO_ARP_RATES.get(fabric_idx, [])
    if not arp_rates:
        return

    for slot in self._slots:
        if slot['lock'].acquire(blocking=False):
            try:
                if slot['mode'] == MotionMode.ARP:
                    for arp_rate_idx in arp_rates:
                        slot['arp'].master_tick(arp_rate_idx, now_ms)
            finally:
                slot['lock'].release()
```

**Modify `on_tick()`:**
Remove the rate phase accumulator block. Keep only:
- Sync phase tracking (for SEQ bar alignment)
- SEQ tick delivery
- Mode handover logic

The QTimer stays running for SEQ, but no longer drives ARP timing.

### Step 1.8: Python — Wire OSC bridge to MotionManager

**File:** `src/gui/controllers/keyboard_controller.py` (or wherever MotionManager is wired)

Connect the OSC bridge signal to MotionManager:

```python
self.main.osc.clock_tick_received.connect(self._motion_manager.on_fabric_tick)
```

**Thread safety note:** `clock_tick_received` is a Qt signal emitted from `_handle_clock_tick` (OSC receiver thread). Qt signal/slot connections default to `Qt.AutoConnection`, which queues the call to the receiver's thread if different. Since MotionManager lives in the main thread, the slot will execute on the main thread. This matches the existing pattern (all OSC signals work this way).

### Step 1.9: Verify latency improvement

**Before (QTimer polling):**
- SC trigger fires → up to 10ms wait for QTimer poll → rate phase check → master_tick()
- Worst case: 10ms latency from trigger to ARP step

**After (SendReply→OSC):**
- SC trigger fires → A2K + Trig1 (~1.5ms at 64-sample block) → SendReply → OSC (~0.1ms) → Qt signal queue → on_fabric_tick()
- Worst case: ~3-5ms, plus inherent phase alignment with SC triggers

---

## Phase 2: Euclidean Gate

Builds directly on top of the fabric-driven ARP. All changes are Python-side only.

### Step 2.1: Add Euclidean hit function (pure math)

**File:** `src/gui/arp_engine.py`
**Location:** After rate configuration constants (after line ~78)

```python
def euclidean_hit(step: int, n: int, k: int, rotation: int = 0) -> bool:
    """Return True if this step is a 'hit' in a Euclidean rhythm.

    Uses the Bresenham/floor method (equivalent to Bjorklund but O(1) per step).
    n: total steps (1..64), k: fills (0..n), rotation: offset (0..n-1)
    """
    if k <= 0:
        return False
    if k >= n:
        return True
    i = (step + rotation) % n
    return (i * k) // n != (((i - 1) * k) // n) if i > 0 else (0 != (((n - 1) * k) // n))
```

### Step 2.2: Add Euclidean fields to ArpSettings + ArpRuntime

**File:** `src/gui/arp_engine.py`

ArpSettings (line ~163):
```python
    # Euclidean gate
    euclid_enabled: bool = False
    euclid_n: int = 16       # Total steps (1..64)
    euclid_k: int = 5        # Fills/hits (0..euclid_n)
    euclid_rot: int = 0      # Rotation (0..euclid_n-1)
```

ArpRuntime (line ~177):
```python
    euclid_step: int = 0     # Advances on every eligible tick
```

### Step 2.3: Gate `_execute_step()` via `_euclid_gate()`

**File:** `src/gui/arp_engine.py`

In `_handle_master_tick()` — wrap both MASTER and AUTO→MASTER `_execute_step()` calls:

```python
# MASTER path (line ~852):
if self._euclid_gate():
    self._execute_step(tick_time_ms)

# AUTO→MASTER promotion path (line ~867):
if self._euclid_gate():
    self._execute_step(tick_time_ms)
```

Add the gate method:
```python
def _euclid_gate(self) -> bool:
    """Check Euclidean gate. Returns True = fire, False = skip.
    Always advances euclid_step. ARP step only advances inside _execute_step.
    """
    if not self.settings.euclid_enabled:
        return True
    n = max(1, min(64, self.settings.euclid_n))
    k = max(0, min(n, self.settings.euclid_k))
    rot = max(0, min(n - 1, self.settings.euclid_rot))
    hit = euclidean_hit(self.runtime.euclid_step, n, k, rot)
    self.runtime.euclid_step += 1
    return hit
```

### Step 2.4: Add ArpEventType values + handlers + public setters

**File:** `src/gui/arp_engine.py`

New event types: `EUCLID_ENABLE`, `EUCLID_N`, `EUCLID_K`, `EUCLID_ROT`

Public setters: `set_euclid_enabled()`, `set_euclid_n()`, `set_euclid_k()`, `set_euclid_rot()`

Each posts to event queue (same pattern as `set_rate()`). Handlers update `self.settings.euclid_*`. Reset `euclid_step = 0` when N changes.

### Step 2.5: Add CMD+K UI controls

**File:** `src/gui/keyboard_overlay.py`
**Location:** `_create_arp_controls()` — after HOLD button (line ~476), before `addStretch()`

Add: `[EUC]` toggle, `N:` CycleButton (1-64), `K:` CycleButton (0-64), `R:` CycleButton (0-63)

### Step 2.6: Sync Euclid state in `sync_ui_from_engine()`

**File:** `src/gui/keyboard_overlay.py`
**Location:** After existing ARP control sync (line ~277)

```python
self._euc_toggle_btn.setChecked(settings.euclid_enabled)
self._euc_n_btn.set_index(settings.euclid_n - 1)
self._euc_k_btn.set_index(settings.euclid_k)
self._euc_rot_btn.set_index(settings.euclid_rot)
```

---

## What NOT to do

- **Do not keep `_rate_phases` in MotionManager** — that's the parallel clock being eliminated
- **Do not broadcast all 13 fabric rates** — only broadcast indices 4-10 (the 7 that ARP needs)
- **Do not change the SEQ tick model** — SEQ needs continuous delta-beat, stays on QTimer
- **Do not add new SC buses or parameters for Euclid** — it's pure Python gating
- **Do not advance ARP step counter on Euclid misses** — _execute_step() is skipped, so current_step_index stays put
- **Do not grey out clock rate buttons when Euclid is on** — rate and Euclid are independent
- **Do not add probability/ratchets/swing/gate-length** — ship only N/K/ROT + enable

---

## Files Changed

### Phase 1 (Clock Unification)

| File | Change |
|------|--------|
| `supercollider/core/clock.scd` | Add `\clockTickBroadcast` SynthDef + start in `~startClock` |
| `supercollider/core/osc_handlers.scd` | Add `\clockTickForward` OSCdef relay |
| `src/config/__init__.py` | Add `clock_tick` OSC path, `ARP_RATE_TO_FABRIC_IDX`, `FABRIC_IDX_TO_ARP_RATES` |
| `src/audio/osc_bridge.py` | Add `clock_tick_received` signal + handler |
| `src/gui/motion_manager.py` | Remove `_rate_phases`, add `on_fabric_tick()`, keep QTimer only for SEQ |
| `src/gui/controllers/keyboard_controller.py` | Wire `osc.clock_tick_received` → `motion_manager.on_fabric_tick` |

### Phase 2 (Euclidean Gate)

| File | Change |
|------|--------|
| `src/gui/arp_engine.py` | `euclidean_hit()`, ArpSettings fields, ArpRuntime.euclid_step, `_euclid_gate()`, event types, handlers, setters |
| `src/gui/keyboard_overlay.py` | EUC/N/K/R widgets in ARP controls, event handlers, sync_ui_from_engine |

---

## Testing

### Phase 1
1. Start app, connect to SC, set ARP on a slot → verify ARP ticks arrive from fabric (no QTimer rate phases)
2. Change BPM mid-arp → verify immediate rate change with no drift
3. Run two ARP slots at same rate → verify they step simultaneously (phase-locked)
4. Test all 7 ARP rates including 1/12 triplet → verify correct timing
5. SEQ continues to work normally (still on QTimer)
6. Disconnect SC → ARP stops (no fabric ticks); reconnect → ARP resumes
7. ARP fallback timer still works when no fabric ticks received (AUTO mode)

### Phase 2
1. Enable EUC → ARP becomes sparser
2. Change N/K/ROT → pattern changes immediately
3. K=0 → silence; K=N → all hits (same as EUC off)
4. Switch slots → Euclid settings preserved per-slot
5. Close/reopen keyboard with HOLD → Euclid state restored
6. UP pattern with Euclid: verify steps are SKIPPED (gaps in sequence), not condensed

---

## Edge Cases

### ARP fallback timer (AUTO mode)
The ARP engine has a fallback QTimer for when master ticks aren't arriving (ClockMode.AUTO). After unification, fallback still works: if SC disconnects or fabric ticks stop, ARP demotes from MASTER to AUTO and uses its own timer. This is the existing safety mechanism and should NOT be removed.

### BPM change during triplet sub-counting
The triplet counter (`_triplet_tick_count`) counts x12 ticks and fires every 4th. On BPM change, x12 tick rate changes instantly. The counter doesn't need to reset — it will naturally sync to the new rate within 4 ticks.

### Multiple ARP rates across slots
Different slots can use different ARP rates. Each fabric tick (index 4-10) triggers all slots whose ARP rate maps to that fabric index. This is already how MotionManager works (iterates all slots per tick), just with a fabric tick instead of a phase crossing.

---

## Future: SEQ Unification

The SEQ engine also has parallel timing (accumulator in `tick(tick_duration_beats)`). Unifying it would require changing from continuous delta-beat to trigger-driven stepping. This is a separate, larger task — noted here for awareness but not in scope.
