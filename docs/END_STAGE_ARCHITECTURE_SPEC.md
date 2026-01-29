# END_STAGE_ARCHITECTURE_SPEC.md — v0.8 (FINAL)

*Decoupling Generator DSP from Output Processing*

---

## Status

|         |                   |
| ------- | ----------------- |
| Version | v0.8              |
| Status  | **FINAL**         |
| Date    | 2025-01-29        |
| Author  | Gareth + Claude   |
| AI1     | P0 Clear ✓        |
| AI2     | P0 Clear ✓        |
| AI3     | P0 Clear ✓        |

---

## 1. Goal

Separate Noise Engine's audio architecture into two distinct layers:

1. **Generator** — Pure sound source (creative DSP only)
2. **End-Stage** — Shared output processing (filter, envelope, routing)

**Why:**
- Reduce generator complexity from ~90 lines to ~30 lines
- Single source of truth for output chain (modify once, all generators benefit)
- Faster idea-to-reality cycle (less boilerplate = more creativity)
- Enable future end-stage variants (percussion, sample playback, FX routing)
- Simplify Forge/Imaginarium pack generation (smaller contract surface)
- Massive reduction in LLM boilerplate errors during pack generation

---

## 2. Current Architecture

Each generator is a monolithic SynthDef containing everything:

```
┌─────────────────────────────────────────────────────────┐
│ Generator SynthDef                                      │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Bus Arguments (15+)                                 │ │
│ │ freqBus, cutoffBus, resBus, attackBus, decayBus,   │ │
│ │ filterTypeBus, envSourceBus, clockRateBus, ...     │ │
│ │ customBus0, customBus1, customBus2, customBus3,    │ │
│ │ customBus4, portamentoBus, midiTrigBus, ...        │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Bus Reads (~15 lines)                               │ │
│ │ freq = In.kr(freqBus);                              │ │
│ │ filterFreq = In.kr(cutoffBus);                      │ │
│ │ rq = In.kr(resBus);                                 │ │
│ │ ... etc                                             │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Creative DSP (20-50 lines) ← THE ACTUAL SOUND      │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Output Chain (~10 lines)                            │ │
│ │ sig = LeakDC.ar(sig);                               │ │
│ │ sig = ~multiFilter.(sig, filterType, freq, rq);    │ │
│ │ sig = ~envVCA.(sig, envSource, clockRate, ...);    │ │
│ │ sig = Limiter.ar(sig, 0.95);                        │ │
│ │ sig = ~ensure2ch.(sig);                             │ │
│ │ Out.ar(out, sig);                                   │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Problems:**
- 300+ SynthDefs with identical boilerplate
- Changing output chain = editing every SynthDef
- Large contract surface for pack generation
- Mental overhead when designing new sounds

---

## 3. Proposed Architecture

Split into two synths per slot, connected via intermediate bus:

```
┌───────────────────────────┐      ┌─────────────────────────────────┐
│ Generator SynthDef        │      │ End-Stage SynthDef              │
│                           │      │                                 │
│ Args:                     │      │ Args:                           │
│   out (intermediate)      │      │   inBus (intermediate)          │
│   freqBus                 │      │   outBus (to mixer)             │
│   customBus0 (contiguous) │      │   cutoffBus, resBus             │
│                           │      │   attackBus, decayBus           │
│ ┌───────────────────────┐ │      │   filterTypeBus, envSourceBus   │
│ │ Creative DSP ONLY     │ │      │   clockRateIndexBus             │
│ │ (20-50 lines)         │ │      │   clockTrigBus, midiTrigBus     │
│ └───────────────────────┘ │      │   slotIndex, ampBus, mute       │
│                           │      │                                 │
│ sig = NumChannels.ar(sig,2)│     │ sig = In.ar(inBus, 2);          │
│ ReplaceOut.ar(out, sig);  │ ──▶  │ sig = ~multiFilter.(...)        │
│                           │ bus  │ sig = ~envVCA.(...)             │
└───────────────────────────┘      │ sig = ~ensure2ch.(sig);         │
                                   │ Out.ar(outBus, sig);            │
                                   └─────────────────────────────────┘
```

**Signal flow per slot:**

```
[Generator] → intermediate_bus[slot] → [End-Stage] → channel_bus[slot] → [Mixer]
```

---

## 4. Technical Invariants (Non-Negotiable)

### 4.1 The ReplaceOut Law

Generators **MUST** write to the intermediate bus using `ReplaceOut.ar(out, sig)`, never `Out.ar`.

**Why:** `Out.ar` sums signals; `ReplaceOut.ar` overwrites. If two generators accidentally exist in a slot (during swap, or a bug), summing doubles the volume. ReplaceOut means "last writer wins" — much safer.

**Verification test:** "Load two generators by accident → intermediate bus should NOT get louder." If it does, someone used `Out.ar` instead of `ReplaceOut.ar`.

### 4.2 The Always-Writer Invariant

Every slot must **always** have a node writing to the intermediate bus to avoid stale audio hanging around.

**Solution:** When a slot is empty, keep `\ne_gen_silence` running:
```supercollider
SynthDef(\ne_gen_silence, { |outBus|
    ReplaceOut.ar(outBus, Silent.ar(2))
}).add;
```

### 4.3 The Stereo Register

- Intermediate bus is **always 2 channels**
- End-stage always does `In.ar(inBus, 2)`
- Generators must normalize output to stereo: `sig = NumChannels.ar(sig, 2)`

### 4.4 Group Determinism

```
GeneratorGroup (Head) → EndStageGroup (Tail)
```

This ensures the generator executes before the end-stage reads the bus.

### 4.5 OSC Bundle Atomicity

Generator swaps **MUST** use OSC bundles, never sequential messages.

**Why:** Individual UDP packets can arrive out-of-order or span multiple server calculation blocks, causing audio dropout or momentary double-volume.

```python
# WRONG - sequential messages, race condition
sc.send_synth_msg(new_gen)
sc.send_free_msg(old_gen)

# CORRECT - atomic bundle, same calc block
sc.send_bundle([new_gen_msg, free_old_msg])
```

### 4.6 Absolute Trigger Indices

End-stage receives **pre-calculated absolute** trigger bus indices, not base + offset.

**Why:** Passing a shared base plus slotIndex creates "double offset" risk if helper logic also offsets.

```python
# WRONG - relies on helper to calculate offset
clockTrigBus=CLOCK_BASE, slotIndex=slot

# CORRECT - pre-calculated, no ambiguity
clockTrigBus=CLOCK_BASE + (slot * 13), slotIndex=slot  # slotIndex for debug only
```

### 4.7 Raw Integer Indices

All bus arguments **MUST** be raw integer indices, not Bus objects or handles.

**Why:** `In.kr(customBus0, 5)` requires the literal memory address. Objects cause silent failures.

```python
# WRONG - may be Bus object
customBus0=custom_bus[slot]

# CORRECT - explicit extraction
customBus0=custom_bus[slot].index
```

### 4.8 Latency Budget

Bus-based patching introduces **~1 audio block** delay:

| Block Size | Sample Rate | Latency |
|------------|-------------|---------|
| 64 samples | 48 kHz | ~1.33 ms |
| 64 samples | 44.1 kHz | ~1.45 ms |
| 128 samples | 48 kHz | ~2.67 ms |

**Acceptable** for Noise Engine textures. **Not suitable** for sample-accurate phase alignment or tight drums.

---

## 5. The Three Pillars (Implementation Protocol)

These are the **mandatory safety protocols** for production-ready implementation. Violating any pillar causes audio corruption, crosstalk, or system instability.

### Pillar 1: Absolute Index Trigger Law

**Problem:** Passing `clockTrigBus` as a base + `slotIndex` as a modifier causes double-offsetting if the `~envVCA` helper also offsets internally.

**Protocol:**

| Layer | Responsibility |
|-------|----------------|
| Python | Calculate final absolute index: `finalClockIdx = CLOCK_BASE + (slot * 13)` |
| SuperCollider | Receive single index, read immediately, **zero internal math** |
| slotIndex | Display/debug only, **never for address calculation** |

```python
# Python calculates, SC receives final value
clock_trig_idx = CLOCK_TRIG_BASE + (slot * 13)
midi_trig_idx = MIDI_TRIG_BASE + slot

# End-stage receives absolute indices
endstage = Synth("ne_endstage_standard",
    clockTrigBus=clock_trig_idx,  # ABSOLUTE - no further math
    midiTrigBus=midi_trig_idx,    # ABSOLUTE - no further math
    slotIndex=slot,               # DEBUG ONLY
    ...
)
```

**~envVCA Contract:** Must NOT offset by slotIndex. Reads directly from passed indices.

### Pillar 2: Atomic Swap Bundling

**Problem:** Sequential OSC messages (`/s_new` then `/n_free`) over UDP can arrive out-of-order or span multiple server cycles, causing audio gaps or doubled volume.

**Protocol:**

1. Allocate fresh Node ID for new generator
2. Create `/s_new` message (target: genGroup, action: addToTail)
3. Create `/n_free` message for current generator/silence
4. Pack both into single OSC Bundle with `timetag=0` (immediate execution)

```python
def swap_generator(slot, synthdef_name, params):
    s = slots[slot]

    # 1. Allocate new node ID
    new_node_id = server.next_node_id()

    # 2. Prepare messages (don't send yet)
    new_msg = OscMessage("/s_new", [
        synthdef_name, new_node_id, 1, s.gen_group_id,  # addToTail
        "out", s.inter_bus_idx,
        "freqBus", s.freq_bus_idx,
        "customBus0", s.custom_bus_idx
    ])

    free_msg = OscMessage("/n_free", [s.current_node_id])

    # 3. Send as ATOMIC BUNDLE (timetag=0 = execute immediately)
    bundle = OscBundle(timetag=0, contents=[new_msg, free_msg])
    server.send(bundle)

    # 4. Update local state
    s.current_node_id = new_node_id
```

**Outcome:** Transition happens within single audio block. User hears seamless change.

### Pillar 3: Raw Integer Boundary

**Problem:** Python libraries wrap SC entities in objects. Passing objects to OSC may serialize incorrectly or use memory addresses instead of bus indices.

**Protocol:**

| Storage | Rule |
|---------|------|
| SlotInfra | Store `int` primitives, **never Bus objects** |
| Allocation | Extract `.index` immediately at allocation time |
| OSC calls | Pass raw integers only |

```python
class SlotInfra:
    def __init__(self, slot, server):
        # WRONG: Stores object (serialization risk)
        # self.inter_bus = server.alloc_audio_bus(2)

        # CORRECT: Extract index immediately
        self.inter_bus_idx = server.alloc_audio_bus(2).index
        self.custom_bus_idx = server.alloc_control_bus(5).index
        self.freq_bus_idx = server.alloc_control_bus(1).index
        # ... all buses stored as int
```

**Verification:** `isinstance(bus_arg, int)` must be True for all OSC arguments.

### Pillar Summary

| Pillar | What | Why | Verification |
|--------|------|-----|--------------|
| 1. Absolute Indices | Python calculates final bus index | Prevents double-offset crosstalk | `~envVCA` does zero slotIndex math |
| 2. Atomic Bundles | new+free in single OSC bundle | Prevents swap dropout | `timetag=0`, both messages in one packet |
| 3. Raw Integers | Store `.index` not objects | Prevents serialization failures | `isinstance(arg, int) == True` |

---

## 6. End-Stage SynthDef Specification

### 6.1 Standard End-Stage (`ne_endstage_standard`)

```supercollider
SynthDef(\ne_endstage_standard, { |inBus, outBus,
    cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envSourceBus, clockRateIndexBus,
    clockTrigBus, midiTrigBus, slotIndex, ampBus, mute=0|

    var sig, filterFreq, rq, attack, decay, filterType, envSource, clockRateIndex, amp;

    // Input from generator (intermediate register)
    sig = In.ar(inBus, 2);

    // Bus reads with SAFETY CLAMPS
    filterFreq = In.kr(cutoffBus).clip(20, 20000);
    rq = In.kr(resBus).clip(0.05, 1.0);
    attack = In.kr(attackBus).clip(0.001, 10);
    decay = In.kr(decayBus).clip(0.001, 30);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRateIndex = In.kr(clockRateIndexBus).clip(0, 12);  // index into clock rate table
    amp = In.kr(ampBus).clip(0, 2);  // allow boost up to 2x

    // Processing chain (SSOT)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRateIndex, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);

    // Mute with click-free fade
    sig = sig * (1 - Lag.kr(mute.clip(0, 1), 0.01));

    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);

    Out.ar(outBus, sig);
}).add;
```

**Key design notes:**
- Uses explicit `ampBus` argument (cannot reference `~params[\amplitude]` inside SynthDef)
- All bus reads have **safety clamps** to prevent runaway values
- `clockRateIndexBus` is an **index** (0-12) into the clock rate table, not Hz
- `ampBus` allows up to 2x boost (0-2 range)
- `mute` parameter with `Lag.kr` for click-free transitions
- **Defined once** in `supercollider/core/endstage.scd`
- **Instantiated 8 times** (one per slot) at server boot — persistent infrastructure

### 6.2 Silence Generator (`ne_gen_silence`)

```supercollider
SynthDef(\ne_gen_silence, { |outBus|
    ReplaceOut.ar(outBus, Silent.ar(2))
}).add;
```

Keeps the intermediate bus zeroed when no generator is loaded. Prevents stale audio.

### 6.3 Future End-Stage Variants

| Variant | Use Case | Differences |
|---------|----------|-------------|
| `ne_endstage_standard` | General purpose | Full chain as above |
| `ne_endstage_minimal` | Percussion, samples | No filter, fast envelope only |
| `ne_endstage_dual_filter` | Complex routing | Serial/parallel filter options |
| `ne_endstage_fx_send` | FX integration | Post-env sends to FX buses |

Variants are **additive** — start with `standard`, add others as needed.

---

## 7. Lightweight Generator Specification

### 7.1 Generator Contract (Gold Standard)

**Canonical allocation:** Noise Engine allocates custom buses contiguously per slot (5 control channels). `customBus0` is the base index; use `In.kr(customBus0, 5)`.

```supercollider
SynthDef(\forge_{pack}_{name}, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);  // Read 5 contiguous custom params

    freq = In.kr(freqBus);

    // === CREATIVE DSP HERE ===
    // This is the ONLY part that varies between generators
    // No filter chain, no envelope, no ensure2ch
    // Just: make a sound

    sig = SinOsc.ar(freq) * p[0];  // Example using first param

    // === MANDATORY TAIL (P0 CRITICAL) ===
    // Force to exactly 2 channels using NumChannels UGen
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
```

**Why NumChannels.ar:**
- `sig.size` is language-side and causes BinaryOpFailure during SynthDef compilation
- `sig ! 2` on stereo creates nested array `[[L,R],[L,R]]` = 4 channels
- `NumChannels.ar(sig, 2)` is a proper UGen that handles mono→stereo and N→2 truncation

### 7.2 Generator Contract Rules

| Rule | Requirement |
|------|-------------|
| Arguments | `out, freqBus, customBus0` (canonical, contiguous) |
| Stereo output | **MUST** use `NumChannels.ar(sig, 2)` — no language-side conditionals |
| ReplaceOut | **MUST** use `ReplaceOut.ar(out, sig)`, never `Out.ar` |
| No filter calls | Do NOT use `~multiFilter` |
| No envelope calls | Do NOT use `~envVCA` |
| No stereo enforcement | Do NOT use `~ensure2ch` |
| Internal safety OK | `LeakDC`, `Limiter` allowed if needed for DSP stability |

### 7.3 What Generators CAN Do

- Internal filters for sound design (e.g., waveshaper followed by internal LP)
- Internal modulation and feedback
- Multiple oscillators, FM, AM, ring mod
- Noise sources, impulses, physical models
- Stereo processing (panning, width, delays)
- Safety limiting if the DSP can blow up

### 7.4 What Generators CANNOT Do

- Apply the user-controlled filter (that's end-stage)
- Apply the envelope/VCA (that's end-stage)
- Output to the mixer directly (must go through end-stage)

---

## 8. Server Topology

### 8.1 Bus Allocation

```
Existing buses (unchanged):
  - freqBus[0-7]
  - cutoffBus[0-7]
  - resBus[0-7]
  - ... etc

New buses:
  - intermediateBus[0-7]  (stereo, 8 buses = 16 channels)
```

### 8.2 Group Structure

```
Server
└── masterGroup
    └── slotGroup[0-7]
        ├── generatorGroup    (generators run first)
        │   └── [generator synth OR ne_gen_silence]
        └── endstageGroup     (end-stages run second)
            └── [endstage synth]
```

**Critical:** Generator must complete before end-stage reads from intermediate bus. Group ordering ensures this.

### 8.3 Synth Lifecycle

**At server boot:**
```python
for slot in range(8):
    # Allocate intermediate bus (stereo audio)
    intermediate_bus[slot] = server.alloc_bus(2)

    # Allocate contiguous custom param buses (5 control channels)
    # P0: MUST be contiguous block, extract raw integer index
    custom_bus_obj[slot] = server.alloc_control_bus(5)
    custom_bus_idx[slot] = custom_bus_obj[slot].index  # RAW INTEGER

    # Calculate absolute trigger base for this slot
    # P0: End-stage receives pre-calculated absolute index, no internal offsetting
    clock_trig_base[slot] = CLOCK_TRIG_BUS_BASE + (slot * 13)
    midi_trig_idx[slot] = MIDI_TRIG_BUS_BASE + slot

    # Boot silence generator (always-writer invariant)
    silence_synth[slot] = Synth("ne_gen_silence",
        outBus=intermediate_bus[slot].index,  # RAW INTEGER
        target=generator_group[slot],
        add_action="addToTail"
    )

    # Boot end-stage (persistent infrastructure)
    endstage_synth[slot] = Synth("ne_endstage_standard",
        inBus=intermediate_bus[slot].index,   # RAW INTEGER
        outBus=channel_bus[slot].index,       # RAW INTEGER
        cutoffBus=cutoff_bus[slot].index,
        resBus=res_bus[slot].index,
        attackBus=attack_bus[slot].index,
        decayBus=decay_bus[slot].index,
        filterTypeBus=filter_type_bus[slot].index,
        envSourceBus=env_source_bus[slot].index,
        clockRateIndexBus=clock_rate_index_bus[slot].index,
        clockTrigBus=clock_trig_base[slot],   # ABSOLUTE INDEX (no slotIndex offset)
        midiTrigBus=midi_trig_idx[slot],      # ABSOLUTE INDEX
        slotIndex=slot,                        # For display/debug only
        ampBus=amp_bus[slot].index,
        target=endstage_group[slot]
    )
```

**When loading a generator (OSC Bundle - P0 CRITICAL):**
```python
def load_generator(slot, synthdef_name):
    s = slots[slot]

    # 1. Prepare messages (don't send yet)
    new_gen_msg = sc.prepare_synth_msg(
        synthdef_name,
        out=s.intermediate_bus_idx,      # RAW INTEGER
        freqBus=s.freq_bus_idx,          # RAW INTEGER
        customBus0=s.custom_bus_idx,     # RAW INTEGER (base of 5ch block)
        target=s.generator_group,
        action="addToTail"
    )

    free_old_msg = sc.prepare_free_msg(s.current_gen_node_id)

    # 2. Send as ATOMIC BUNDLE (same server calc block)
    # P0: Prevents audio dropout from out-of-order UDP packets
    sc.send_bundle([new_gen_msg, free_old_msg])

    # 3. Update local state
    s.current_gen_node_id = new_gen_msg.node_id
```

**When clearing a slot (OSC Bundle):**
```python
def clear_generator(slot):
    s = slots[slot]

    # 1. Prepare messages
    new_silence_msg = sc.prepare_synth_msg(
        "ne_gen_silence",
        outBus=s.intermediate_bus_idx,
        target=s.generator_group,
        action="addToTail"
    )

    free_old_msg = sc.prepare_free_msg(s.current_gen_node_id)

    # 2. Send as ATOMIC BUNDLE
    sc.send_bundle([new_silence_msg, free_old_msg])

    # 3. Update local state
    s.current_gen_node_id = new_silence_msg.node_id
```

**End-stage never changes** — it's persistent infrastructure.

### 8.4 Raw Index Enforcement

All bus arguments to SynthDefs **MUST** be raw integer indices:

```python
# WRONG - may pass Bus object or handle
customBus0=custom_bus[slot]

# CORRECT - explicit integer extraction
customBus0=custom_bus[slot].index
```

The `In.kr(customBus0, 5)` UGen requires the literal memory address. Bus objects or handles will cause silent failures or crosstalk.

---

## 9. FX Send Integration (Future)

### 9.1 Extended End-Stage with FX Sends

```supercollider
SynthDef(\ne_endstage_fx, { |inBus, outBus,
    cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envSourceBus, clockRateIndexBus,
    clockTrigBus, midiTrigBus, slotIndex, ampBus, mute=0,
    fx1OutBus, fx2OutBus, fx1SendBus, fx2SendBus|  // FX routing

    var sig, filterFreq, rq, attack, decay, filterType, envSource, clockRateIndex, amp;
    var fx1Send, fx2Send;

    sig = In.ar(inBus, 2);

    // Bus reads with safety clamps
    filterFreq = In.kr(cutoffBus).clip(20, 20000);
    rq = In.kr(resBus).clip(0.05, 1.0);
    attack = In.kr(attackBus).clip(0.001, 10);
    decay = In.kr(decayBus).clip(0.001, 30);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRateIndex = In.kr(clockRateIndexBus).clip(0, 12);
    amp = In.kr(ampBus).clip(0, 2);  // Allow boost up to 2x

    // FX send levels
    fx1Send = In.kr(fx1SendBus).clip(0, 1);
    fx2Send = In.kr(fx2SendBus).clip(0, 1);

    // Processing chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRateIndex, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);

    // Post-envelope FX sends
    Out.ar(fx1OutBus, sig * fx1Send);
    Out.ar(fx2OutBus, sig * fx2Send);

    // Mute with click-free fade
    sig = sig * (1 - Lag.kr(mute.clip(0, 1), 0.01));

    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);

    Out.ar(outBus, sig);
}).add;
```

### 9.2 FX Send Signal Flow

```
[Generator] → intermediate → [End-Stage] ─┬─▶ [Mixer] (dry)
                                          ├─▶ [FX1 Bus] → [FX1] → [FX Return 1]
                                          └─▶ [FX2 Bus] → [FX2] → [FX Return 2]
```

**Send point options:**
- Pre-filter (raw generator output)
- Post-filter (shaped tone)
- Post-envelope (full dynamics) ← most common, shown above

---

## 10. Migration Strategy

### 10.1 Order of Work

1. **Land SC infrastructure** (`supercollider/core/endstage.scd`)
   - `\ne_endstage_standard` SynthDef
   - `\ne_gen_silence` SynthDef

2. **Land Python BusManager/SlotInfra**
   - Allocate intermediate buses (2ch per slot)
   - Allocate contiguous custom param buses (5ch per slot) — **P0 CRITICAL**
   - Build per-slot groups: `slotGroup → genGroup (head) → endGroup (tail)`
   - Boot end-stage in `endGroup`
   - Boot silence gen in `genGroup` with `addToTail`

3. **Update Python parameter routing** — **P0 CRITICAL**
   - Route end-stage parameters to end-stage synth node (not generator):
     - cutoff, res, attack, decay, filterType, envSource, clockRateIndex, amp
   - Route generator parameters to generator synth node:
     - freq, customBus0 (P1-P5)

4. **Implement generator swap logic**
   - Create new generator in `genGroup` with `addToTail`
   - Call `server.sync()` before freeing old generator
   - ReplaceOut ensures no amplitude spike during overlap

5. **Convert one pack manually** for validation (harga)

6. **Run converter in dry-run**, triage flagged list, iterate heuristics

7. **Apply conversion pack-by-pack** with A/B listening tests

### 10.2 Phase 1: Infrastructure

1. Create `supercollider/core/endstage.scd` with `ne_endstage_standard` + `ne_gen_silence`
2. Allocate intermediate buses in Python (`BusManager`) — 2ch audio per slot
3. Allocate contiguous custom param buses (`BusManager`) — 5ch control per slot **P0**
4. Create group structure for ordering (`SlotAudioInfra`)
5. Boot end-stage synths at startup (persistent) — include all bus args especially `ampBus` **P0**
6. Boot silence gens at startup with `addToTail` (swapped out when real generator loads)
7. **Update parameter dispatch** to route end-stage params to end-stage node **P0**
8. Test with ONE manually converted generator

### 10.3 Phase 2: Conversion Tool

Create `tools/convert_to_lightweight.py`:

```python
"""
Surgical script to strip boilerplate from existing packs.

Usage:
    python tools/convert_to_lightweight.py packs/harga/          # dry-run
    python tools/convert_to_lightweight.py packs/harga/ --apply  # write changes

Output: JSON report listing changed/ok/flagged files + reasons
"""

def convert_generator(scd_path, apply=False):
    """
    Strip boilerplate from existing generator SynthDef.

    Four transforms:

    1. ARGUMENT STRIP
       - Remove: cutoffBus, resBus, attackBus, decayBus, filterTypeBus,
                 envSourceBus, clockRateBus/clockRateIndexBus, clockTrigBus,
                 midiTrigBus, slotIndex, portamentoBus
       - Keep: out, freqBus, customBus0

    2. BOILERPLATE PURGE
       - Remove In.kr reads for end-stage buses
       - Keep: freq = In.kr(freqBus), custom param reads

    3. TAIL RECONSTRUCTION
       - Remove: ~multiFilter, ~envVCA, ~ensure2ch, LeakDC, Limiter, Out.ar
       - Append mandatory tail:
           sig = NumChannels.ar(sig, 2);
           ReplaceOut.ar(out, sig);

    4. VALIDATION HEURISTIC
       - Compute line reduction percentage
       - If < 40%, FLAG FOR MANUAL REVIEW
         (likely non-standard formatting or missing boilerplate match)
    """
    pass
```

**Behavior:**
- Default: **dry-run** (shows what would change)
- `--apply`: writes changes and creates `.bak` backup
- Output: JSON report with `{changed: [], ok: [], flagged: []}`

**Flagging criteria:**
- Line reduction < 40% → probably non-standard, needs human eyes
- Missing expected patterns → might already be converted or unusual
- Parse errors → definitely needs manual review

### 10.4 Phase 3: Pack Conversion

Convert existing packs in order of preference:
1. **harga** (your favourite, good test case)
2. **wicker**
3. **avebury**
4. ... remaining packs

**Verification per pack:**
- A/B test against original (should sound identical)
- All 8 generators load without error
- Filter/envelope controls still work
- P1-P5 still work

### 10.5 Phase 4: Update Forge Spec

Revise `CQD_FORGE_SPEC.md`:
- Simpler generator contract (7 args instead of 15+)
- No output chain requirements
- Smaller validation surface
- Update `forge_template.scd`

---

## 11. Forge/Imaginarium Impact

### 11.1 Before (Current)

Generator contract for Claude:
```
- 15+ bus arguments to get right
- 10+ bus reads to include
- Output chain order to remember
- Helper functions to call correctly
- ~90 lines per generator
```

### 11.2 After (Lightweight)

Generator contract for Claude:
```
- 3 bus arguments (out, freqBus, customBus0)
- 2 bus reads (freq + 5 custom via contiguous read)
- Just make a sound
- ~30 lines per generator
```

**Validation simplifies:**
- No need to check for `~multiFilter`, `~envVCA`, `~ensure2ch`
- No output chain order verification
- Just: "does it compile and make audio?"

### 11.3 Updated GENERATOR_PACK_SESSION.md

Contract section shrinks from:
```supercollider
SynthDef(\forge_{pack}_{name}, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|
    // ... 15 lines of bus reads ...
    // ... creative DSP ...
    // MANDATORY output chain (this order):
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
```

To:
```supercollider
SynthDef(\forge_{pack}_{name}, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);

    freq = In.kr(freqBus);

    // === YOUR SOUND HERE ===

    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
```

---

## 12. Open Questions

| Question | Options | Resolution |
|----------|---------|------------|
| Portamento handling | End-stage vs generator | **TBD** - some generators might want internal control |
| LeakDC placement | End-stage only vs allow in generator | **End-stage** handles it; generator can add if needed for feedback stability |
| Intermediate bus count | Stereo (2ch) vs flexible | **RESOLVED: Always 2ch** - generators use `NumChannels.ar(sig, 2)` |
| End-stage selection | Per-slot vs per-generator vs global | **TBD** - per-slot most flexible, start with global |
| Bypass mode | Silent vs pass-through | **RESOLVED: Silence gen** - `ne_gen_silence` writes zeros when empty |

---

## 13. Success Criteria

- [ ] End-stage SynthDef defined and working
- [ ] 8 end-stage instances boot correctly
- [ ] At least one pack converted to lightweight format
- [ ] Converted pack sounds identical to original
- [ ] Filter/envelope controls work via end-stage
- [ ] Forge spec updated for lightweight generators
- [ ] New pack generated using lightweight contract
- [ ] CPU usage same or lower than before

---

## 14. Risks

| Risk | Mitigation |
|------|------------|
| 1-block latency between generator and end-stage | Acceptable for texture synth; not doing sample-accurate drums |
| Generators that use filterFreq internally for modulation | Audit existing packs; provide freq as separate bus if needed |
| Group ordering bugs cause silence | Comprehensive boot sequence testing |
| End-stage changes break existing packs | Version end-stages; maintain backward compatibility |

---

## 15. References

- `CQD_FORGE_SPEC.md` — Current pack generation contract
- `CQD_FORGE_DELIVERY.md` — Phased delivery plan
- `GENERATOR_SPEC.md` — Existing generator contract (to be superseded)
- `supercollider/core/helpers.scd` — `~multiFilter`, `~envVCA`, `~ensure2ch` definitions

---

## 16. One-Line Ruleset

> **Generators: `NumChannels.ar(sig, 2)` → `ReplaceOut.ar`. Swaps: OSC bundle (new+free atomic). Buses: raw integer indices. Triggers: absolute pre-calculated. Always-writer: silence gen when empty.**

---

**v0.8 — FINAL**

*Added Three Pillars (§5): Absolute Index Trigger Law, Atomic Swap Bundling, Raw Integer Boundary. These are the mandatory safety protocols for production implementation. Violating any pillar causes audio corruption.*
