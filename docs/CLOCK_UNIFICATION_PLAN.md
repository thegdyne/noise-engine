# Clock Timing Unification Plan

## Overview

Unify clock divider/multiplier system across noise-engine to use a single master clock with consistent rate sets and phase-locked timing. Expose clock values through auxiliary buses for modulation use cases.

## Current Issues

1. **Modulators don't use master clock divisions** - read x32 only, re-implement division with PulseDivider
2. **Inconsistent rate sets** - Generators: 13 rates, Modulators: 12 rates (missing /12, x12)
3. **No per-slot modulator rate selection** - all hardcoded to x32 (generators have per-slot)
4. **Master FX not phase-locked** - uses free-running LFO scaled by BPM (drifts over time)
5. **Clock rate not in unified bus** - discrete parameter, can't be modulated

## Solution Architecture

**Two-Phase Approach:**

### Phase 1: Core Unification (Fix Inconsistencies)
- Modulators use master clock's pre-divided rates (like generators)
- Add per-slot clock rate selection for modulators
- Standardize to 13 rates everywhere
- Phase-lock Master FX dual filter sweeps

### Phase 2: Clock Value Buses (Optional Enhancement)
- Add 13 control-rate buses with phase-locked triangle LFOs
- Enable clock-synced modulation sources
- Support advanced rhythmic effects

**Design Decision:** Keep clock rate as **discrete parameter** (0-12 index), add continuous clock value buses for modulation needs.

---

## Phase 1: Core Unification

### 1.1 Standardize Rate Set (13 rates everywhere)

**Python:** `src/config/__init__.py`
```python
# Line ~208 - Already correct
CLOCK_RATES = ["/32", "/16", "/12", "/8", "/4", "/2", "CLK", "x2", "x4", "x8", "x12", "x16", "x32"]

# Update modulator rates to match (currently 12 rates, missing /12 and x12)
MOD_CLOCK_RATES = CLOCK_RATES  # Remove separate array, use same SSOT

# Remove MOD_CLOCK_TICKS_PER_CYCLE (no longer needed after PulseDivider removal)
```

**SuperCollider:** `supercollider/core/buses.scd`
```supercollider
# Line 16 - Already correct, no changes needed
~clockRates = [1/32, 1/16, 1/12, 1/8, 1/4, 1/2, 1, 2, 4, 8, 12, 16, 32];
```

### 1.2 Modulators: Use Master Clock Pre-Divided Rates

**Pattern to apply across all modulator SynthDefs:**

**Files to modify:**
- `supercollider/core/mod_lfo.scd`
- `supercollider/core/mod_arseq_plus.scd`
- `supercollider/core/mod_sauce_of_grav.scd`

**Before (current pattern):**
```supercollider
SynthDef(\modLFO, { |..., clockIndex=12, ...|
    var clk = In.ar(clockTrigBus + clockIndex);  // Always x32
    var trig = A2K.kr(Trig1.ar(clk, ControlDur.ir * 2));
    var ticksPerCycle = Select.kr(rateIndex, [2048, 1024, 512, ...]);
    var resetTrig = PulseDivider.kr(trig, ticksPerCycle);  // Manual division
```

**After (use master clock divisions):**
```supercollider
SynthDef(\modLFO, { |..., rateIndex=6, ...|
    var allTrigs = In.ar(clockTrigBus, 13);  // Read all 13 rates
    var clockRateIdx = rateIndex.clip(0, 12).round;
    var clk = Select.ar(clockRateIdx, allTrigs);  // Select pre-divided rate
    var trig = A2K.kr(Trig1.ar(clk, ControlDur.ir * 2));
    var resetTrig = trig;  // Direct use, no PulseDivider needed
```

**Key changes:**
1. Add `rateIndex` parameter (0-12, default 6 = CLK for backward compat)
2. Read all 13 clock channels with `In.ar(clockTrigBus, 13)`
3. Select rate with `Select.ar(rateIndex, allTrigs)` (same pattern as generators)
4. Remove `PulseDivider` logic entirely
5. Remove `ticksPerCycle` arrays

### 1.3 Add Per-Slot Modulator Rate Selection

**Storage:** `supercollider/core/mod_slots.scd`
```supercollider
// In ~setupModSlots, add rate storage (like ~genParams)
~modRateParams = Array.fill(4, { Bus.control(s, 1).set(6) });  // Default CLK

// In ~startModSlot, pass rateIndex from storage:
~modNodes[idx] = Synth(\modLFO, [
    // ... existing params ...
    \rateIndex, ~modRateParams[idx].asMap,  // Read from bus
]);
```

**OSC Handler:** `supercollider/core/osc_handlers.scd`
```supercollider
OSCdef(\modClockRate, { |msg|
    var slot = msg[1].asInteger;
    var rateIndex = msg[2].asInteger.clip(0, 12);
    var idx = slot - 1;

    if((slot >= 1) && (slot <= 4)) {
        ~modRateParams[idx].set(rateIndex);
        "Mod slot % clock rate: %".format(slot, ~clockRates[rateIndex]).postln;
    };
}, '/noise/mod/clockRate');
```

**Python OSC Path:** `src/config/__init__.py`
```python
OSC_PATHS = {
    # ... existing ...
    'mod_clock_rate': '/noise/mod/clockRate',  # [slot, rateIndex]
}
```

**Python UI:** `src/gui/modulation/mod_slot_widget.py`
```python
# Add rate selector widget (copy pattern from generator_slot.py)
self.rate_selector = QtWidgets.QComboBox()
self.rate_selector.addItems(CLOCK_RATES)
self.rate_selector.setCurrentIndex(6)  # CLK default

def _on_rate_changed(self, index):
    self.main.osc.client.send_message(
        OSC_PATHS['mod_clock_rate'],
        [self.slot_id, index]
    )
```

### 1.4 Master FX Dual Filter: Phase-Lock Sweeps

**File:** `supercollider/effects/dual_filter.scd`

**Before (free-running LFO):**
```supercollider
tempoHz = In.kr(bpmBus) / 60;
lfo1 = LFTri.kr(sync1Rate * tempoHz).range(0, 1);  // Drifts over time
```

**After (phase-locked to triggers):**
```supercollider
// Map rate multiplier to clock index
var rateToIndex = { |mult|
    case
    { mult <= 0 } { -1 }        // Free/off
    { mult == (1/32) } { 0 }
    { mult == (1/16) } { 1 }
    { mult == (1/12) } { 2 }
    { mult == (1/8) } { 3 }
    { mult == (1/4) } { 4 }
    { mult == (1/2) } { 5 }
    { mult == 1 } { 6 }
    { mult == 2 } { 7 }
    { mult == 4 } { 8 }
    { mult == 8 } { 9 }
    { mult == 12 } { 10 }
    { mult == 16 } { 11 }
    { mult == 32 } { 12 }
    { 6 };  // Default to CLK
};

var idx1 = rateToIndex.(sync1Rate);
var bpm = In.kr(bpmBus);
var baseRate = bpm / 60;

var lfo1 = Select.kr(idx1 >= 0, [
    DC.kr(1),  // Free mode: no modulation
    {
        var allTrigs = In.ar(~clockTrigBus.index, 13);
        var trig1 = Select.ar(idx1, allTrigs);
        var trigK1 = A2K.kr(Trig1.ar(trig1, ControlDur.ir * 2));
        var freq1 = baseRate * sync1Rate;
        var phase1 = Phasor.kr(trigK1, freq1 * ControlDur.ir, 0, 1, 0);

        // Triangle wave from phase
        var tri = Select.kr(phase1 < 0.5, [
            1 - ((phase1 - 0.5) * 2),  // Falling edge
            phase1 * 2                  // Rising edge
        ]);
        tri.range(0, 1)
    }.value
]);
```

**Benefits:**
- Phase resets on clock boundaries (no drift)
- Synchronized to musical grid
- Same phase-lock pattern as modulators

---

## Phase 2: Clock Value Buses (Optional)

### 2.1 Add Clock Value SynthDef

**File:** `supercollider/core/clock.scd`

Add after `~setupClock`:

```supercollider
~setupClockValues = {
    "Setting up clock value buses...".postln;

    // Allocate 13 control buses for phase-locked LFO values
    ~clockValueBus = Bus.control(s, 13);

    SynthDef(\masterClockValues, { |bpmBus, clockTrigBus, outBus|
        var bpm, baseRate, values;

        bpm = In.kr(bpmBus);
        baseRate = bpm / 60;

        // Generate 13 phase-locked triangle LFOs
        values = 13.collect { |i|
            var mult = ~clockRates[i];
            var trig = In.ar(clockTrigBus + i);
            var trigK = A2K.kr(Trig1.ar(trig, ControlDur.ir * 2));
            var freq = baseRate * mult;
            var phase = Phasor.kr(trigK, freq * ControlDur.ir, 0, 1, 0);

            // Triangle wave: ramp up then down
            var tri = Select.kr(phase < 0.5, [
                1 - ((phase - 0.5) * 2),  // Falling
                phase * 2                  // Rising
            ]);

            tri * 2 - 1  // Bipolar -1 to +1
        };

        Out.kr(outBus, values);
    }).add;

    "  [x] Clock value buses ready (13 rates)".postln;
};

~startClockValues = {
    ~clockValueSynth = Synth(\masterClockValues, [
        \bpmBus, ~clockBus.index,
        \clockTrigBus, ~clockTrigBus.index,
        \outBus, ~clockValueBus.index
    ], ~clockGroup, \addAfter);

    "  [x] Clock values running".postln;
};
```

**File:** `supercollider/init.scd`

Add after clock setup:
```supercollider
~setupClockValues.();
// ... later in boot sequence after server ready ...
~startClockValues.();
```

### 2.2 Usage in Generators (Optional)

**Example custom oscillator sync:**
```supercollider
// Custom param controls rate selection (0-1 → 0-12)
var rateIdx = In.kr(customBus0).linlin(0, 1, 0, 12).round.clip(0, 12);
var clockPhase = Select.kr(rateIdx, In.kr(~clockValueBus.index, 13));

// Use phase to modulate frequency, pulse width, etc.
var osc = Pulse.ar(freq, 0.5 + (clockPhase * 0.3));  // PWM from clock
```

### 2.3 Expose as Cross-Mod Sources (Optional)

**File:** `src/gui/modulation/mod_matrix.py`

Add 13 clock sources to mod matrix:
```python
# After existing mod sources (0-23)
CLOCK_VALUE_SOURCES = {
    24: "CLK /32",
    25: "CLK /16",
    26: "CLK /12",
    27: "CLK /8",
    28: "CLK /4",
    29: "CLK /2",
    30: "CLK",
    31: "CLK x2",
    32: "CLK x4",
    33: "CLK x8",
    34: "CLK x12",
    35: "CLK x16",
    36: "CLK x32",
}
```

**SuperCollider integration:** Route ~clockValueBus to unified bus targets via extended mod system.

---

## Implementation Order

### Stage 1: Core Fixes (Low Risk)
1. ✓ Update Python config - standardize rate arrays
2. ✓ Modify mod_lfo.scd - remove PulseDivider, use master clock
3. ✓ Modify mod_arseq_plus.scd - same pattern
4. ✓ Modify mod_sauce_of_grav.scd - same pattern
5. ✓ Add per-slot rate storage in mod_slots.scd
6. ✓ Add OSC handler for `/noise/mod/clockRate`
7. ✓ Add UI rate selector to mod panels
8. ✓ Test: verify phase alignment with generators

### Stage 2: Master FX (Medium Risk)
1. ✓ Modify dual_filter.scd - phase-locked sweeps
2. ✓ Test: verify no drift over 10+ minute session
3. ✓ Test: verify no clicks when changing rates

### Stage 3: Clock Values (Optional, Medium Risk)
1. ✓ Add ~clockValueBus to clock.scd
2. ✓ Create masterClockValues SynthDef
3. ✓ Start synth in init.scd
4. ✓ Test: verify smooth -1 to +1 outputs
5. ✓ Optionally expose as cross-mod sources

---

## Critical Files to Modify

### SuperCollider (9 files)
1. **supercollider/core/mod_lfo.scd** - Remove PulseDivider, add rateIndex param
2. **supercollider/core/mod_arseq_plus.scd** - Same pattern
3. **supercollider/core/mod_sauce_of_grav.scd** - Same pattern
4. **supercollider/core/mod_slots.scd** - Add rate storage, pass rateIndex to synths
5. **supercollider/core/osc_handlers.scd** - Add `/noise/mod/clockRate` handler
6. **supercollider/effects/dual_filter.scd** - Phase-lock LFO sweeps
7. **supercollider/core/clock.scd** - Add clock value buses (Phase 2)
8. **supercollider/core/buses.scd** - Allocate ~clockValueBus (Phase 2)
9. **supercollider/init.scd** - Start clock values (Phase 2)

### Python (4 files)
1. **src/config/__init__.py** - Unify CLOCK_RATES and MOD_CLOCK_RATES
2. **src/gui/modulation/mod_slot_widget.py** - Add rate selector UI
3. **src/gui/modulation/mod_panel.py** - Layout integration
4. **src/osc/osc_handler.py** - Route mod clock rate messages

### Documentation (3 files)
1. **docs/DECISIONS.md** - Document clock unification decision
2. **CLAUDE.md** - Update modulator patterns
3. **STATE.md** - Update clock system status

---

## Verification

### Functional Tests
1. **Modulators use master clock:**
   - Set mod rate to /4, generator ENV rate to /4
   - Both should trigger simultaneously (phase aligned)

2. **Per-slot modulator rates:**
   - Mod1 = /16, Mod2 = x4
   - Verify different trigger frequencies

3. **Master FX phase lock:**
   - Set dual filter sync1 = CLK
   - Verify sweep resets on beat, no drift over 10 minutes

4. **Clock value buses (Phase 2):**
   - Read ~clockValueBus channels
   - Verify smooth triangle waves, -1 to +1 range
   - Verify phase resets on triggers

### Performance Tests
1. CPU usage increase < 1% (Phase 1)
2. CPU usage increase < 2% (Phase 2 with clock values)
3. No bus allocation errors
4. No memory leaks over 30-minute session

### Edge Cases
1. Rapid rate changes (< 100ms apart) - no clicks or glitches
2. BPM changes during modulation - smooth transition
3. All 4 mod slots at x32 simultaneously - no CPU spikes

---

## Trade-Off Summary

### Why Discrete Clock Rate (Not in Unified Bus)

**Pros:**
- Clear semantics (musical divisions)
- No ambiguity (what is rate=5.7?)
- Matches existing generator pattern
- Easy to understand and debug

**Cons:**
- Can't modulate smoothly
- Not visible in mod matrix

**Decision:** Keep discrete, add clock value buses for continuous modulation needs.

### Why Phase-Locked (Not Free-Running)

**Pros:**
- Synchronized to musical grid
- No drift accumulation
- Predictable timing relationships

**Cons:**
- Less organic than free-running
- Can't create polyrhythms vs master clock

**Decision:** Phase-lock by default, keep FREE mode option for modulators.

### Why Auxiliary Buses (Not Unified Bus Integration)

**Pros:**
- No discrete parameter handling in apply tick
- Clean separation of concerns
- Backward compatible
- Optional (can skip Phase 2)

**Cons:**
- Clock rate still not in mod matrix
- Additional bus allocation (+13)

**Decision:** Two-phase approach - fix core issues first, add enhancement later.

---

## Success Criteria

✓ All modulators can select different clock rates independently
✓ Modulator triggers phase-align with generator envelopes at same rate
✓ Master FX dual filter sweeps stay phase-locked over 10+ minutes
✓ No audio clicks or glitches during rate changes
✓ Clock value buses (Phase 2) output smooth -1 to +1 bipolar signals
✓ CPU increase < 2% total
✓ No breaking changes to existing user sessions

---

## Future Enhancements (Out of Scope)

- Swing/groove offset for even-numbered triggers
- Per-slot polyrhythm mode (independent clocks)
- Custom clock divisions (e.g., /7, x3, x5)
- Visual timeline showing active clock rates
- MIDI clock sync (external clock source)
- Modulatable clock rate via unified bus (discrete handling)
