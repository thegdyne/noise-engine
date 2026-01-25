# SuperCollider Unified Bus Specification

## Companion to BOID_UNIFIED_BUS_MIGRATION-GROUND.md

This document specifies the SuperCollider side of the unified 149-bus architecture. It MUST be implemented alongside the Python GROUND spec to ensure protocol compatibility.

---

## Overview

The Python GROUND spec defines a 149-target unified bus layout where boid contributions for columns 0–148 are sent via `/noise/boid/offsets`. This SC spec defines how SuperCollider allocates, receives, and applies those offsets.

**Key Contract:** Python sends `targetIndex` values 0–148. SC receives these and applies offsets to the corresponding unified buses.

---

## Bus Layout (149 Total)

SC MUST allocate **149 contiguous control buses** with the following layout:

| Index Range | Count | Category    | Parameters                                          |
|-------------|-------|-------------|-----------------------------------------------------|
| 0–39        | 40    | Gen Core    | 8 slots × 5 params (freq, cutoff, res, attack, decay) |
| 40–79       | 40    | Gen Custom  | 8 slots × 5 custom params (custom0–4)               |
| 80–107      | 28    | Mod Slots   | 4 slots × 7 params (P0–P6)                          |
| 108–131     | 24    | Channels    | 8 channels × 3 params (echoSend, verbSend, pan)     |
| 132–148     | 17    | FX          | Heat, Echo, Reverb, DualFilter (mix params excluded)|

### FX Parameter Detail (indices 132–148)

| Index | Effect      | Parameter   |
|-------|-------------|-------------|
| 132   | Heat        | drive       |
| 133   | Echo        | time        |
| 134   | Echo        | feedback    |
| 135   | Echo        | tone        |
| 136   | Echo        | wow         |
| 137   | Echo        | spring      |
| 138   | Echo        | verbSend    |
| 139   | Reverb      | size        |
| 140   | Reverb      | decay       |
| 141   | Reverb      | tone        |
| 142   | DualFilter  | drive       |
| 143   | DualFilter  | freq1       |
| 144   | DualFilter  | freq2       |
| 145   | DualFilter  | reso1       |
| 146   | DualFilter  | reso2       |
| 147   | DualFilter  | syncAmt     |
| 148   | DualFilter  | harmonics   |

**Note:** Mix parameters are excluded from boid modulation as they control wet/dry balance which should remain user-controlled.

---

## Required Changes to bus_unification.scd

### 1. Bus Allocation

**Current (WRONG):**
```supercollider
~unifiedBusCount = 71;
```

**Required:**
```supercollider
~unifiedBusCount = 149;
```

### 2. Boid Offsets Array

**Current (WRONG):**
```supercollider
~boidOffsets = Array.fill(71, { 0.0 });
```

**Required:**
```supercollider
~boidOffsets = Array.fill(149, { 0.0 });
```

This applies to ALL locations where the array is initialized:
- Initial setup
- On disable (`\disable` case)
- On setOffsets (`\setOffsets` case)

### 3. Target Metadata Registry

The `~targetMeta` dictionary MUST include entries for all 149 targets.

**New entries required for Gen Core (indices 0–39):**
```supercollider
8.do { |slotIdx|
    var slot = slotIdx + 1;
    var baseIdx = ~unifiedBusBase + (slotIdx * 5);

    ~targetMeta[("gen_%_freq").format(slot).asSymbol] = (
        busIndex: baseIdx,
        min: 20.0, max: 20000.0, default: 440.0
    );
    ~targetMeta[("gen_%_cutoff").format(slot).asSymbol] = (
        busIndex: baseIdx + 1,
        min: 20.0, max: 20000.0, default: 5000.0
    );
    ~targetMeta[("gen_%_res").format(slot).asSymbol] = (
        busIndex: baseIdx + 2,
        min: 0.0, max: 1.0, default: 0.5
    );
    ~targetMeta[("gen_%_attack").format(slot).asSymbol] = (
        busIndex: baseIdx + 3,
        min: 0.0001, max: 10.0, default: 0.01
    );
    ~targetMeta[("gen_%_decay").format(slot).asSymbol] = (
        busIndex: baseIdx + 4,
        min: 0.0001, max: 10.0, default: 0.5
    );
};
```

**New entries required for Gen Custom (indices 40–79):**
```supercollider
8.do { |slotIdx|
    var slot = slotIdx + 1;
    var baseIdx = ~unifiedBusBase + 40 + (slotIdx * 5);

    5.do { |pIdx|
        ~targetMeta[("gen_%_custom%").format(slot, pIdx).asSymbol] = (
            busIndex: baseIdx + pIdx,
            min: 0.0, max: 1.0, default: 0.5
        );
    };
};
```

**Shifted entries for Mod Slots (indices 80–107):**
```supercollider
4.do { |slotIdx|
    var slot = slotIdx + 1;
    7.do { |pIdx|
        var key = ("mod_%_p%").format(slot, pIdx).asSymbol;
        var busIdx = ~unifiedBusBase + 80 + (slotIdx * 7) + pIdx;  // +80 offset
        ~targetMeta[key] = (
            busIndex: busIdx,
            min: 0.0, max: 1.0, default: 0.5
        );
    };
};
```

**Shifted entries for Channels (indices 108–131):**
```supercollider
8.do { |chanIdx|
    var chan = chanIdx + 1;
    var baseIdx = ~unifiedBusBase + 108 + (chanIdx * 3);  // +108 offset

    ~targetMeta[("chan_%_echo").format(chan).asSymbol] = (
        busIndex: baseIdx, min: 0.0, max: 1.0, default: 0.0
    );
    ~targetMeta[("chan_%_verb").format(chan).asSymbol] = (
        busIndex: baseIdx + 1, min: 0.0, max: 1.0, default: 0.0
    );
    ~targetMeta[("chan_%_pan").format(chan).asSymbol] = (
        busIndex: baseIdx + 2, min: -1.0, max: 1.0, default: 0.0
    );
};
```

**Shifted entries for FX (indices 132–148):**
```supercollider
// FX targets at indices 132-148
var fxParams = [
    [\fx_heat_drive, 0.0, 1.0, 0.0],
    [\fx_echo_time, 0.01, 2.0, 0.3],
    [\fx_echo_feedback, 0.0, 0.95, 0.3],
    [\fx_echo_tone, 0.0, 1.0, 0.5],
    [\fx_echo_wow, 0.0, 1.0, 0.0],
    [\fx_echo_spring, 0.0, 1.0, 0.0],
    [\fx_echo_verbSend, 0.0, 1.0, 0.0],
    [\fx_reverb_size, 0.0, 1.0, 0.5],
    [\fx_reverb_decay, 0.0, 1.0, 0.5],
    [\fx_reverb_tone, 0.0, 1.0, 0.5],
    [\fx_dualFilter_drive, 0.0, 1.0, 0.0],
    [\fx_dualFilter_freq1, 20.0, 20000.0, 500.0],
    [\fx_dualFilter_freq2, 20.0, 20000.0, 2000.0],
    [\fx_dualFilter_reso1, 0.0, 1.0, 0.5],
    [\fx_dualFilter_reso2, 0.0, 1.0, 0.5],
    [\fx_dualFilter_syncAmt, 0.0, 1.0, 0.0],
    [\fx_dualFilter_harmonics, 0.0, 1.0, 0.5]
];

fxParams.do { |params, i|
    var key = params[0];
    var busIdx = ~unifiedBusBase + 132 + i;  // +132 offset
    ~targetMeta[key] = (
        busIndex: busIdx,
        min: params[1], max: params[2], default: params[3]
    );
};
```

---

## Required Changes to bus_unification_osc.scd

### 1. Validation Range

**Current (WRONG):**
```supercollider
~isValidUnifiedBusIndex = { |busIndex|
    var minBus = ~unifiedBusBase;
    var maxBus = ~unifiedBusBase + 70;  // WRONG: should be +148
    busIndex.isInteger && (busIndex >= minBus) && (busIndex <= maxBus);
};
```

**Required:**
```supercollider
~isValidUnifiedBusIndex = { |busIndex|
    var minBus = ~unifiedBusBase;
    var maxBus = ~unifiedBusBase + 148;  // 149 buses: 0-148
    busIndex.isInteger && (busIndex >= minBus) && (busIndex <= maxBus);
};
```

### 2. setOffsets Handler

**Current (WRONG):**
```supercollider
{ op == \setOffsets } {
    var newOffsets = Array.fill(71, { 0.0 });
    if(boidOp.offsets.notNil, {
        boidOp.offsets.keysValuesDo { |busIndex, offset|
            var idx = busIndex - ~unifiedBusBase;
            if((idx >= 0) && (idx < 71), {
                newOffsets[idx] = offset;
            });
        };
    });
    ~boidOffsets = newOffsets;
};
```

**Required:**
```supercollider
{ op == \setOffsets } {
    var newOffsets = Array.fill(149, { 0.0 });
    if(boidOp.offsets.notNil, {
        boidOp.offsets.keysValuesDo { |busIndex, offset|
            var idx = busIndex - ~unifiedBusBase;
            if((idx >= 0) && (idx < 149), {
                newOffsets[idx] = offset;
            });
        };
    });
    ~boidOffsets = newOffsets;
};
```

---

## Generator SynthDef Requirements

For boid modulation to affect generator parameters (indices 0–79), generator SynthDefs MUST read freq, cutoff, res, attack, and decay from unified buses rather than direct arguments.

### Current Pattern (parameters passed as args):
```supercollider
SynthDef(\generator, { |out, freq=440, cutoff=5000, res=0.5, attack=0.01, decay=0.5|
    // Uses args directly
});
```

### Required Pattern (parameters read from buses):
```supercollider
SynthDef(\generator, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus|
    var freq = In.kr(freqBus);
    var cutoff = In.kr(cutoffBus);
    var res = In.kr(resBus);
    var attack = In.kr(attackBus);
    var decay = In.kr(decayBus);
    // Uses bus values
});
```

**Implementation Note:** The current generators already use bus arguments for these parameters. The change required is ensuring the Python side writes base values to the correct unified bus indices (0–39 for core params).

---

## OSC Message Contract

### `/noise/boid/offsets`

**Direction:** Python → SC

**Payload:** Flat list of (targetIndex, offset) pairs
- `targetIndex`: int32 (OSC type 'i'), range 0–148
- `offset`: float32 (OSC type 'f'), finite value

**Example:**
```
/noise/boid/offsets ,ififif 0 0.25 5 -0.1 132 0.5
```

This sends:
- Target 0 (gen1_freq): +0.25 offset
- Target 5 (gen2_freq): -0.1 offset
- Target 132 (fx_heat_drive): +0.5 offset

### `/noise/boid/enable`

**Payload:** Single int (1=enable, 0=disable)

On disable, SC MUST clear all boid offsets.

### `/noise/boid/clear`

**Payload:** None or ignored

Clears all boid offsets without disabling.

---

## Apply Tick Behavior

The SC apply tick routine MUST:

1. Read boid offsets from `~boidOffsets` array (indices 0–148)
2. For each target with a non-zero offset, add the offset to the base value
3. Clamp the result to target's min/max range
4. Write to the target's unified bus

**Boid offset application:**
```supercollider
149.do { |idx|
    var offset = ~boidOffsets[idx];
    if(offset != 0.0, {
        var busIdx = ~unifiedBusBase + idx;
        var currentVal = Bus(\control, busIdx, 1).getSynchronous;
        var newVal = currentVal + offset;
        // Apply clamping based on target metadata
        Bus(\control, busIdx, 1).setSynchronous(newVal);
    });
};
```

---

## Validation Checklist

Before merging SC changes:

- [ ] `~unifiedBusCount = 149`
- [ ] `~boidOffsets` sized to 149 in all locations
- [ ] `~isValidUnifiedBusIndex` checks `<= base + 148`
- [ ] `setOffsets` handler uses array size 149 and check `< 149`
- [ ] `~targetMeta` has entries for all 149 targets with correct bus indices
- [ ] Gen core params at indices 0–39
- [ ] Gen custom params at indices 40–79
- [ ] Mod params at indices 80–107
- [ ] Channel params at indices 108–131
- [ ] FX params at indices 132–148

---

## Testing

### Verify Bus Allocation
```supercollider
~unifiedBuses.numChannels.postln;  // Should print: 149
~unifiedBusBase.postln;            // Note the actual base
```

### Verify Offset Storage
```supercollider
// After enabling boids in Python:
~boidOffsets.select { |v| v != 0 }.size.postln;  // Should be > 0
```

### Verify Apply Routine
```supercollider
~boidApplyRoutine.isPlaying.postln;  // Should be: true
```

### Verify Generator Modulation
```supercollider
// Read gen1 freq bus (index 0)
Bus(\control, ~unifiedBusBase, 1).get { |v| ("gen1_freq: " ++ v).postln };
```

---

## Spec Metadata

- **Companion To:** BOID_UNIFIED_BUS_MIGRATION-GROUND.md (Python spec)
- **Spec Version:** 1
- **Created:** 2025-01-25
- **Status:** DRAFT - Requires review before implementation

---

## Implementation Order

1. Update `bus_unification.scd` bus allocation and arrays
2. Update `bus_unification.scd` target metadata registry
3. Update `bus_unification_osc.scd` validation and handlers
4. Test with Python boid system
5. Verify end-to-end modulation

**Do not implement Python GROUND spec without also implementing this SC spec.**
