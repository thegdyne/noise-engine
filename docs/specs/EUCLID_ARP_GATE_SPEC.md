# ARP Clock Unification + Euclidean Gate — Implementation Spec

---
status: spec
version: 3.0
date: 2025-02-08
builds-on: PER_SLOT_ARP_SPEC v2.0, CLOCK_FABRIC.md, arp_engine.py
size: Medium (2-3 days)
---

## What

Two changes, done in order:

1. **Clock Unification** — Replace MotionManager's parallel Python clock with SC fabric tick broadcast. ARP stepping becomes phase-locked to the master clock.

2. **Euclidean ARP Gate** — Add N/K/ROT gate to the ARP. User picks a fast base rate (1/16, 1/8), Euclid thins it. Ship only the simple gate.

---

## Problem: Parallel Clock

MotionManager runs its own 10ms QTimer with rate phase accumulators — a parallel clock that duplicates the SC fabric. This violates the Clock Fabric decision.

```
SC (authoritative):              Python (parallel duplicate):
masterClock → 13 trigger buses   QTimer → phase accumulators → master_tick()
```

**Fix:** SC broadcasts fabric ticks to Python via SendReply→OSC. MotionManager consumes them instead of maintaining its own phase math.

---

## Phase 1: Clock Unification

### Architecture (After)

```
SC masterClock → clockTrigBus → clockTickBroadcast (SendReply)
                                       ↓
                              OSCdef relay → /noise/clock/tick [fabricIdx]
                                       ↓
                              Python OSC bridge → clock_tick_received signal
                                       ↓
                              MotionManager.on_fabric_tick(fabric_idx)
                                       ↓
                              ARP rate lookup → engine.master_tick()
```

SEQ stays on QTimer (needs continuous delta-beat accumulator — different timing model).

### Rate Mapping

6 direct matches. 1/12 (triplet) stays on the existing fallback timer — no special handling.

| ARP idx | ARP label | Fabric idx | Fabric label | Direct match? |
|---------|-----------|------------|--------------|---------------|
| 0       | 1/32      | 9          | x8           | Yes           |
| 1       | 1/16      | 8          | x4           | Yes           |
| 2       | 1/12      | —          | —            | No (fallback) |
| 3       | 1/8       | 7          | x2           | Yes           |
| 4       | 1/4       | 6          | CLK          | Yes           |
| 5       | 1/2       | 5          | /2           | Yes           |
| 6       | 1 bar     | 4          | /4           | Yes           |

**Why this works for 1/12:** The ARP engine already has ClockMode.AUTO with a BPM-synced fallback timer. When no matching fabric tick arrives, the engine stays in AUTO. Already works today, zero extra code.

### Step 1.1: SC — Clock tick broadcast synth

**File:** `supercollider/core/clock.scd`
**After `~setupClock`, add:**

```supercollider
~setupClockBroadcast = {
    SynthDef(\clockTickBroadcast, { |clockTrigBus|
        var allTrigs = In.ar(clockTrigBus, 13);
        // Broadcast fabric indices 4-9 (covers /4 through x8)
        [4, 5, 6, 7, 8, 9].do { |idx|
            var trigK = A2K.kr(Trig1.ar(allTrigs[idx], ControlDur.ir * 2));
            SendReply.kr(trigK, '/clock/tick', [idx]);
        };
    }).add;
    "  [x] ClockTickBroadcast SynthDef ready".postln;
};
```

### Step 1.2: SC — OSCdef relay

**File:** `supercollider/core/osc_handlers.scd`

```supercollider
OSCdef(\clockTickForward, { |msg|
    if(~pythonAddr.notNil) {
        ~pythonAddr.sendMsg('/noise/clock/tick', msg[3].asInteger);
    };
}, '/clock/tick');
```

### Step 1.3: SC — Start broadcast in `~startClock`

**File:** `supercollider/core/clock.scd`
**Inside `~startClock`, after `~clockSynth`:**

```supercollider
~clockBroadcastSynth = Synth(\clockTickBroadcast, [
    \clockTrigBus, ~clockTrigBus.index
], ~clockGroup);
"  [x] Clock tick broadcast running".postln;
```

### Step 1.4: Python — OSC path

**File:** `src/config/__init__.py` — add to `OSC_PATHS`:

```python
'clock_tick': '/noise/clock/tick',
```

### Step 1.5: Python — OSC bridge signal + handler

**File:** `src/audio/osc_bridge.py`

Signal:
```python
clock_tick_received = pyqtSignal(int)  # fabric_idx
```

Handler:
```python
def _handle_clock_tick(self, address, *args):
    if self._shutdown or self._deleted:
        return
    if len(args) >= 1:
        self.clock_tick_received.emit(int(args[0]))
```

Register in `_start_server()`:
```python
dispatcher.map(OSC_PATHS['clock_tick'], self._handle_clock_tick)
```

### Step 1.6: Python — Rate mapping

**File:** `src/config/__init__.py`

```python
# ARP rate → fabric index (direct matches only, 1/12 excluded)
ARP_RATE_TO_FABRIC_IDX = {
    0: 9,   # 1/32 → x8
    1: 8,   # 1/16 → x4
    3: 7,   # 1/8  → x2
    4: 6,   # 1/4  → CLK
    5: 5,   # 1/2  → /2
    6: 4,   # 1 bar → /4
}
# Note: ARP rate 2 (1/12 triplet) has no fabric match — uses fallback timer

# Inverse: fabric index → ARP rate index
FABRIC_IDX_TO_ARP_RATE = {v: k for k, v in ARP_RATE_TO_FABRIC_IDX.items()}
```

### Step 1.7: Python — Rewire MotionManager

**File:** `src/gui/motion_manager.py`

**Remove:**
- `_rate_phases` list (line ~104)
- Rate phase accumulation + `rates_crossed` logic in `on_tick()` (lines ~164-170, ~187-189)

**Add new method:**

```python
def on_fabric_tick(self, fabric_idx: int):
    """Handle clock fabric tick from SC. Route to matching ARP slots."""
    arp_rate = FABRIC_IDX_TO_ARP_RATE.get(fabric_idx)
    if arp_rate is None:
        return

    now_ms = time.monotonic() * 1000.0

    for slot in self._slots:
        if slot['lock'].acquire(blocking=False):
            try:
                if slot['mode'] == MotionMode.ARP:
                    slot['arp'].master_tick(arp_rate, now_ms)
            finally:
                slot['lock'].release()
```

**Keep in `on_tick()`:**
- Sync phase tracking (SEQ bar alignment)
- SEQ tick delivery
- Mode handover logic

QTimer stays running for SEQ. No longer drives ARP.

### Step 1.8: Python — Wire it up

**File:** `src/gui/controllers/keyboard_controller.py`

```python
self.main.osc.clock_tick_received.connect(self._motion_manager.on_fabric_tick)
```

---

## Phase 2: Euclidean Gate

Pure Python. No SC changes. Works on top of whatever clock drives the ARP (fabric ticks or fallback timer — doesn't matter).

**Musical model:** User picks a fast ARP rate (e.g., 1/16 = 16 ticks/bar). Euclid N/K/ROT decides which ticks fire. ARP only advances on hits.

### Step 2.1: Euclidean hit function

**File:** `src/gui/arp_engine.py` — after rate constants (~line 78)

```python
def euclidean_hit(step: int, n: int, k: int, rotation: int = 0) -> bool:
    """True if step is a hit in Euclidean rhythm E(k,n).
    O(1) per step. Bresenham/floor method."""
    if k <= 0:
        return False
    if k >= n:
        return True
    i = (step + rotation) % n
    return (i * k) // n != (((i - 1) * k) // n) if i > 0 else (0 != (((n - 1) * k) // n))
```

### Step 2.2: Settings + runtime fields

**File:** `src/gui/arp_engine.py`

ArpSettings — add:
```python
    euclid_enabled: bool = False
    euclid_n: int = 16
    euclid_k: int = 16   # Default = all hits (same as off)
    euclid_rot: int = 0
```

ArpRuntime — add:
```python
    euclid_step: int = 0
```

### Step 2.3: Gate in `_handle_master_tick()`

**File:** `src/gui/arp_engine.py`

Wrap both `_execute_step()` calls (MASTER path ~line 852, AUTO→MASTER promotion ~line 867):

```python
if self._euclid_gate():
    self._execute_step(tick_time_ms)
```

New method:
```python
def _euclid_gate(self) -> bool:
    """Returns True = fire note, False = skip. Always advances euclid_step."""
    if not self.settings.euclid_enabled:
        return True
    n = max(1, min(64, self.settings.euclid_n))
    k = max(0, min(n, self.settings.euclid_k))
    rot = max(0, min(n - 1, self.settings.euclid_rot))
    hit = euclidean_hit(self.runtime.euclid_step, n, k, rot)
    self.runtime.euclid_step += 1
    return hit
```

### Step 2.4: Event types + setters

**File:** `src/gui/arp_engine.py`

Add `EUCLID_ENABLE`, `EUCLID_N`, `EUCLID_K`, `EUCLID_ROT` to ArpEventType.

Add `set_euclid_enabled()`, `set_euclid_n()`, `set_euclid_k()`, `set_euclid_rot()` — same event queue pattern as `set_rate()`.

Reset `euclid_step = 0` when N changes.

### Step 2.5: CMD+K UI

**File:** `src/gui/keyboard_overlay.py`
**In `_create_arp_controls()`, after HOLD button, before `addStretch()`:**

Add: `[EUC]` toggle + `N:` CycleButton (1-64) + `K:` CycleButton (0-64) + `R:` CycleButton (0-63)

Wire: `_on_euc_toggle()`, `_on_euc_n_changed()`, `_on_euc_k_changed()`, `_on_euc_rot_changed()`

### Step 2.6: Sync in `sync_ui_from_engine()`

**File:** `src/gui/keyboard_overlay.py` — after existing ARP sync (~line 277):

```python
self._euc_toggle_btn.setChecked(settings.euclid_enabled)
self._euc_n_btn.set_index(settings.euclid_n - 1)
self._euc_k_btn.set_index(settings.euclid_k)
self._euc_rot_btn.set_index(settings.euclid_rot)
```

---

## Do NOT

- Keep `_rate_phases` in MotionManager (that's the parallel clock)
- Add special handling for 1/12 triplet (fallback timer handles it)
- Change the SEQ tick model (stays on QTimer)
- Add SC buses or params for Euclid (pure Python gating)
- Add probability, ratchets, swing, or gate length
- Advance ARP step counter on Euclid misses

---

## Files Changed

### Phase 1

| File | Change |
|------|--------|
| `supercollider/core/clock.scd` | `\clockTickBroadcast` SynthDef + start |
| `supercollider/core/osc_handlers.scd` | `\clockTickForward` OSCdef |
| `src/config/__init__.py` | `clock_tick` path, `ARP_RATE_TO_FABRIC_IDX`, `FABRIC_IDX_TO_ARP_RATE` |
| `src/audio/osc_bridge.py` | `clock_tick_received` signal + handler |
| `src/gui/motion_manager.py` | Remove `_rate_phases`, add `on_fabric_tick()` |
| `src/gui/controllers/keyboard_controller.py` | Wire signal |

### Phase 2

| File | Change |
|------|--------|
| `src/gui/arp_engine.py` | `euclidean_hit()`, settings, runtime, `_euclid_gate()`, event types, setters |
| `src/gui/keyboard_overlay.py` | EUC/N/K/R controls, handlers, sync |

---

## Testing

### Phase 1
1. ARP on a slot → ticks come from fabric, not QTimer
2. Change BPM mid-arp → immediate, no drift
3. Two ARP slots at same rate → step simultaneously
4. 1/12 rate → still works via fallback timer (no regression)
5. SEQ still works (QTimer unchanged)
6. Disconnect SC → ARP falls back to AUTO timer

### Phase 2
1. Set ARP to 1/16, enable EUC, N=16, K=11 → 11 hits per bar
2. Change K → density changes immediately
3. Change ROT → pattern shifts
4. K=0 → silence, K=N → all hits
5. Switch slots → Euclid preserved per-slot
6. HOLD + close/reopen keyboard → state restored
