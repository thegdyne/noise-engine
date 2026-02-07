# Clock Fabric - Timing System Architecture

**Single Source of Truth for all timing in Noise Engine**

---

## Core Principle

There is **one master timing source** in Noise Engine:

```
BPM control → Master Clock SynthDef → 13 pre-divided trigger channels → All consumers
```

Everything time-based **must consume these triggers**, not create independent divider chains.

---

## The Clock Fabric

**Location:** `supercollider/core/clock.scd`

**Architecture:**
- Single `\masterClock` SynthDef runs in dedicated `~clockGroup` (head of processing chain)
- Reads BPM from `~clockBus` (control-rate)
- Generates 13 audio-rate trigger streams via `Impulse.ar(baseRate * mult)`
- Outputs to `~clockTrigBus` (audio bus, 13 channels)

**Key invariant:** All 13 rates are **phase-aligned** and **derived from one BPM source**.

---

## Canonical Rate Mapping (SSOT)

**Do not duplicate this table.** Reference this document instead.

| idx | rate  | mult  | meaning                    | example (120 BPM)    |
|-----|-------|-------|----------------------------|----------------------|
| 0   | /32   | 1/32  | 8 bars                     | 15 seconds           |
| 1   | /16   | 1/16  | 4 bars                     | 8 seconds            |
| 2   | /12   | 1/12  | 3 bars                     | 6 seconds            |
| 3   | /8    | 1/8   | 2 bars                     | 4 seconds            |
| 4   | /4    | 1/4   | 1 bar                      | 2 seconds            |
| 5   | /2    | 1/2   | 2 beats                    | 1 second             |
| 6   | CLK   | 1     | 1 beat (quarter note)      | 500ms                |
| 7   | x2    | 2     | 1/2 beat (eighth note)     | 250ms                |
| 8   | x4    | 4     | 1/4 beat (16th note)       | 125ms                |
| 9   | x8    | 8     | 1/8 beat (32nd note)       | 62.5ms               |
| 10  | x12   | 12    | 1/12 beat (triplet 16th)   | 41.67ms              |
| 11  | x16   | 16    | 1/16 beat (64th note)      | 31.25ms              |
| 12  | x32   | 32    | 1/32 beat (128th note)     | 15.625ms             |

**Semantic zones:**
- **idx 0-5:** Bars and multi-beat divisions (slow, compositional time)
- **idx 6:** CLK = the beat (quarter note reference)
- **idx 7-12:** Subdivisions (fast, rhythmic detail)

**Conversion formula:**
```
freq_hz = (BPM / 60) * multiplier
```

**Python SSOT:** `src/config/__init__.py:208`
```python
CLOCK_RATES = ["/32", "/16", "/12", "/8", "/4", "/2", "CLK", "x2", "x4", "x8", "x12", "x16", "x32"]
CLOCK_RATE_INDEX = {rate: i for i, rate in enumerate(CLOCK_RATES)}
```

**SuperCollider SSOT:** `supercollider/core/buses.scd:16`
```supercollider
~clockRates = [1/32, 1/16, 1/12, 1/8, 1/4, 1/2, 1, 2, 4, 8, 12, 16, 32];
```

---

## Building Derived Clocks

When you need timing **variants** (swing, euclidean, ratchets, probabilistic gates), follow this pattern:

### 1. Pick a Base Tick

Choose an index from the fabric (0-12) as your "step clock":
```supercollider
var baseTick = Select.ar(rateIdx, In.ar(clockTrigBus, 13));
```

### 2. Build Pattern Logic

Apply your rhythmic transformation to the base tick:
- **Euclidean:** Use a counter + modulo to skip triggers
- **Swing:** Delay even-numbered triggers by a percentage
- **Ratchets:** Multiply a single trigger into N sub-triggers
- **Probability:** Gate the trigger with a random < threshold check

**Key:** Your pattern logic operates **on** the base tick, not **instead of** it.

### 3. Output Phase-Locked Stream

The result is another trigger stream (audio-rate bus) that:
- Resets phase on trigger edges from the base tick
- Stays synchronized to the master clock
- Can be consumed by downstream modules (envelopes, sequencers, LFOs)

### 4. Example Pattern

**Euclidean rhythm derived from x4:**
```supercollider
var baseTick = Select.ar(8, In.ar(~clockTrigBus.index, 13));  // x4
var counter = Stepper.kr(baseTick, 0, 0, 15, 1);
var euclidPattern = [1,0,0,1,0,1,0,0,1,0,1,0,0,1,0,0];  // 16-step euclidean
var euclidTrig = baseTick * Select.kr(counter, euclidPattern);
```

**This trigger stream is still phase-locked to the master clock's x4 division.**

---

## Consumer API Contract

Any clock consumer (generators, modulators, FX, sequencers) **must** follow this contract:

### Inputs Required:
- `clockTrigBus` — base index of the 13-channel trigger bus
- `clkIdx` or `rateIdx` — which channel to select (0-12)
- Optional: `resetBus` — global reset signal for pattern restart

### Pattern:
```supercollider
var allTrigs = In.ar(clockTrigBus, 13);
var selectedTrig = Select.ar(clkIdx.clip(0, 12), allTrigs);
var trig = A2K.kr(Trig1.ar(selectedTrig, ControlDur.ir * 2));
// Use trig to reset phase, advance sequencers, trigger envelopes, etc.
```

### Outputs:
- Consumer generates audio/control signals **synchronized** to the selected trigger
- No local BPM division logic (e.g., no `PulseDivider`, no `bpm/60/division`)
- Frequency calculations derive from `clockMults[idx]` only

### Exceptions:
- **Free-running modes** (user explicitly disables clock sync) may use independent frequency
- **Gate/presence detection** (e.g., SauceOfGrav) may use clock as a presence signal, not a division source

---

## Reset & Phase Policy

### What "Phase-Locked" Means:

1. **Phase alignment:** All derived clocks reset on trigger edges from the fabric
2. **Tempo stability:** BPM changes propagate instantly; no drift accumulation
3. **Synchronization:** Multiple consumers reading the same `clkIdx` trigger simultaneously

### Reset Signal:

**Global reset:** `~resetBus` (if implemented)
- Sent on transport start, bar boundaries, or user command
- All pattern counters (sequencers, euclidean steppers, etc.) reset to step 0
- Phase accumulators (`Phasor.kr`) reset to 0.0

**Bar reset:** Typically index 4 (/4 = 1 bar) serves as the "downbeat" reference

### Tempo Changes:

When BPM changes:
- Master clock immediately updates all 13 `Impulse.ar` frequencies
- Consumers using `Phasor.kr` increment rate scales with new BPM
- **No accumulated error** — phase resets keep everything aligned

---

## Anti-Patterns (❌ Don't Do This)

### ❌ **x32 + PulseDivider for divisions**
```supercollider
// BAD: Reinvents the clock, can desync, duplicates logic
var x32 = In.ar(clockTrigBus + 12);
var trig = A2K.kr(Trig1.ar(x32, ControlDur.ir * 2));
var divided = PulseDivider.kr(trig, 128);  // Trying to get /4 manually
```

**Why bad:**
- Master clock already provides /4 at index 4
- Creates parallel division chain that can drift
- Wastes CPU on redundant computation

**Do instead:**
```supercollider
// GOOD: Use pre-divided channel
var allTrigs = In.ar(clockTrigBus, 13);
var quarterNote = Select.ar(4, allTrigs);  // /4 directly from fabric
```

---

### ❌ **Free-running LFO when mode says "sync"**
```supercollider
// BAD: LFO drifts over time, ignores clock
var lfo = LFTri.kr(bpm / 60 * rateMultiplier);
```

**Why bad:**
- Not phase-locked to trigger edges
- Accumulates phase error on tempo changes
- Doesn't reset on pattern boundaries

**Do instead:**
```supercollider
// GOOD: Phase-locked Phasor with trigger reset
var trig = Select.ar(rateIdx, In.ar(clockTrigBus, 13));
var trigK = A2K.kr(Trig1.ar(trig, ControlDur.ir * 2));
var phase = Phasor.kr(trigK, freq * ControlDur.ir, 0, 1, 0);
var lfo = (phase * 2 - 1).sin;  // Phase resets on every trigger
```

---

### ❌ **Alternate BPM math inside modules**
```supercollider
// BAD: Creates independent tempo calculation
var myBPM = In.kr(bpmBus);
var myBaseRate = myBPM / 60;
var myFreq = myBaseRate * someMultiplier;
```

**Why bad:**
- Duplicates `BPM / 60 * mult` logic across multiple files
- Source of truth is the master clock, not individual modules
- Makes it unclear which modules are synced vs independent

**Do instead:**
```supercollider
// GOOD: Derive from fabric, calculate freq from selected rate
var clockMults = #[1/32, 1/16, 1/12, 1/8, 1/4, 1/2, 1, 2, 4, 8, 12, 16, 32];
var mult = Select.kr(rateIdx, clockMults);
var bpm = In.kr(bpmBus);
var freq = bpm / 60 * mult;  // Consistent with master clock
```

---

### ❌ **Hardcoded rate assumptions**
```supercollider
// BAD: Assumes x32 is always at index 12, breaks if rates change
var highResTick = In.ar(clockTrigBus + 12);
```

**Why bad:**
- Fragile if rate table reorders
- Unclear intent (why index 12?)

**Do instead:**
```supercollider
// GOOD: Use semantic index or bus-mapped parameter
var rateIdx = 12;  // x32, with comment explaining why
var allTrigs = In.ar(clockTrigBus, 13);
var tick = Select.ar(rateIdx, allTrigs);
```

---

## ✅ Do This Instead

### ✅ **Select from pre-divided channels**
```supercollider
var allTrigs = In.ar(clockTrigBus, 13);
var selectedTrig = Select.ar(rateIdx.clip(0, 12), allTrigs);
```

### ✅ **Reset phase on trigger edges**
```supercollider
var trigK = A2K.kr(Trig1.ar(selectedTrig, ControlDur.ir * 2));
var phase = Phasor.kr(trigK, freq * ControlDur.ir, 0, 1, 0);
```

### ✅ **Use clockMults array for frequency calculations**
```supercollider
var clockMults = #[1/32, 1/16, 1/12, 1/8, 1/4, 1/2, 1, 2, 4, 8, 12, 16, 32];
var mult = Select.kr(rateIdx, clockMults);
var freq = In.kr(bpmBus) / 60 * mult;
```

### ✅ **Gate computation when clock is disabled**
```supercollider
var clockOn = (rateIdx >= 0);  // -1 = off
var trig = Select.ar(rateIdx.clip(0, 12), allTrigs) * clockOn;
```

---

## Reference Implementations

### Good Examples:

**Generators (Envelope VCA):** `supercollider/core/helpers.scd:31-54`
- Reads all 13 channels: `In.ar(clockTrigBus, 13)`
- Selects via parameter: `Select.ar(clockRate, allTrigs)`
- Used by all generators via endstage

**Modulators (LFO):** `supercollider/core/mod_lfo.scd:161-182`
- Legacy rate mapping for backward compatibility
- Selects from pre-divided channels
- Phase-locks Phasor to trigger resets

**Modulators (ARSeq+):** `supercollider/core/mod_arseq_plus.scd:138-151`
- Same pattern as LFO
- Master trigger drives sequencer steps

**Master FX (Dual Filter):** `supercollider/effects/dual_filter.scd:108-130`
- Phase-locked triangle LFOs
- Gate computation when sync is off
- Correct triangle formula: `1 - (phase * 2 - 1).abs`

---

## Migration Path for Legacy Code

If you find code using the old patterns (x32 + PulseDivider):

1. **Identify the intended division:**
   - What was `ticksPerCycle`?
   - Map it to the canonical rate table

2. **Replace with fabric selection:**
   - Add `rateIdx` parameter (0-12)
   - Read all 13 channels
   - Select via `Select.ar(rateIdx, allTrigs)`

3. **Update OSC handlers:**
   - Add `/noise/{subsystem}/clockRate` path
   - Send index 0-12 from Python UI

4. **Test phase alignment:**
   - Verify trigger at same rate from different consumers fires simultaneously
   - Check tempo changes propagate without glitches

---

## Clock Variants & Future Extensions

### Possible Derived Clocks:

1. **Swing Clock:**
   - Base: x4 (16th notes)
   - Even-numbered triggers delayed by swing amount (0-50%)
   - Output: x4 with groove

2. **Euclidean Clock:**
   - Base: any rate
   - Pattern: distribute N hits over M steps
   - Output: rhythmically interesting trigger stream

3. **Ratchet Clock:**
   - Base: any rate
   - Trigger multiplier: 1 trigger → 2-4 sub-triggers
   - Output: stuttered/ratcheted timing

4. **Probability Gate:**
   - Base: any rate
   - Per-trigger random < threshold
   - Output: sparse, generative timing

5. **Clock Divider Chains:**
   - Base: fast rate (x8, x16)
   - Pattern: skip N triggers, emit 1
   - Output: custom odd divisions (e.g., /7, /11)

### Implementation Guideline:

All variants follow the pattern:
```
Fabric trigger → Pattern logic → Derived trigger stream
```

Never create alternate BPM sources or independent division math.

---

## Ownership & Maintenance

**Location in STATE.md:**
```markdown
Clock Fabric = 13 pre-divided trigger buses; all timing features derive from it.
```

**Decision in DECISIONS.md:**
```markdown
## Clock Timing Architecture
- Standardized on pre-divided trigger buses as timing SSOT
- Clock variants must derive from fabric, not from x32+divider chains
- Exception: Free-running modes and presence gates (e.g., SauceOfGrav)
```

**Files Modified:**
- `supercollider/core/clock.scd` — Master clock generation
- `supercollider/core/buses.scd` — Clock rate SSOT
- `src/config/__init__.py` — Python rate SSOT
- All consumers: generators, modulators, FX, sequencers

**Last Updated:** 2025-02-07
**Commit:** `782b746` (clock unification + regression fixes)
