# Architecture: Generators (SuperCollider + Python UI)

This document defines the **generator contract**: how **SuperCollider generator SynthDefs**, **JSON metadata**, and the **Python UI** fit together.

The intended workflow is **manual-first**:
1) copy an existing generator (`.scd` + `.json`)  
2) edit DSP + params  
3) add to `GENERATOR_CYCLE`  
4) done

---

## 1. Repository Layout

### SuperCollider
- `supercollider/generators/*.scd`  
  Individual generator SynthDefs (one file per generator type).
- `supercollider/generators/*.json`  
  Metadata the Python UI loads (labels/ranges/curves/defaults + trim, etc.).
- `supercollider/core/helpers.scd`  
  Shared helper functions used by generators:
  - `~ensure2ch.(sig)`
  - `~multiFilter.(sig, filterType, filterFreq, rq)`
  - `~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex)`
  - `~stereoSpread.(sig, rate, width)`
  - `~startGenerator.(slotID, genType)` (wires buses into the SynthDef)

### Python
- `src/config/__init__.py`
  - Loads generator JSON into `_GENERATOR_CONFIGS`
  - Defines `GENERATOR_CYCLE` (ordering of types in the UI)
  - Defines standard parameter list (e.g. `GENERATOR_PARAMS`)
  - Defines `MAX_CUSTOM_PARAMS = 5`
- `src/gui/main_frame.py`
  - On generator change sends:
    - `start_generator` (slot + SynthDef name)
    - `midi_retrig` (slot + 0/1 from JSON)
    - `gen_trim` (slot + `output_trim_db` from JSON)

---

## 2. Core Design: What a “Generator” Is

A generator is a **single SynthDef** that:
1. reads **mapped** control values from buses (Hz, seconds, 0–1, etc.)
2. produces an audio signal `sig`
3. applies the shared “post-chain” (stereo safety + filter + envelope VCA)
4. outputs to `out` with `Out.ar(out, sig)`

The UI always provides:
- Standard sliders: `FRQ, CUT, RES, ATK, DEC`
- Custom sliders: `P1–P5` (up to 5)

---

## 3. The Hard SynthDef Contract

Every generator SynthDef **must** accept this argument signature because `~startGenerator` sets these keys.

### 3.1 Mandatory args

```supercollider
SynthDef(\yourSynthDefName, { |out,
    freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4|
    ...
}).add;
```

### 3.2 Mandatory bus reads (mapped units)

Read each bus once, reuse variables:

```supercollider
var freq       = In.kr(freqBus);
var filterFreq = In.kr(cutoffBus);
var rq         = In.kr(resBus);
var attack     = In.kr(attackBus);
var decay      = In.kr(decayBus);
var filterType = In.kr(filterTypeBus);
var envSource  = In.kr(envSourceBus);
var clockRate  = In.kr(clockRateBus);
var amp        = In.kr(~params[\amplitude]);

var p1 = In.kr(customBus0);
var p2 = In.kr(customBus1);
var p3 = In.kr(customBus2);
var p4 = In.kr(customBus3);
var p5 = In.kr(customBus4);
```

### 3.3 Mandatory post-chain order (SSOT)

After your DSP assigns `sig`, the **canonical** post-chain is:

```supercollider
sig = ~ensure2ch.(sig);      // FIRST: enforce 2ch before any bus write
sig = ~multiFilter.(sig, filterType, filterFreq, rq);
sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
Out.ar(out, sig);
```

#### Stereo spread placement
`~stereoSpread.(sig, rate, width)` is commonly used to widen a **mono** generator.

Because `~stereoSpread` uses `Pan2.ar`, **do not call it after `~ensure2ch`** unless you *intentionally* want >2 channels (you don’t). Recommended pattern:

```supercollider
// DSP stage (optional)
sig = ~stereoSpread.(sig, 0.3, 0.2);  // only if sig is mono

// Post-chain (canonical)
sig = ~ensure2ch.(sig);
sig = ~multiFilter.(sig, filterType, filterFreq, rq);
sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
Out.ar(out, sig);
```

---

## 4. Critical Gotcha: Trigger Buses Are AUDIO Rate

This is the one that bites (e.g. SH-101 / TB-303 work).

### 4.1 What the buses actually are
- `clockTrigBus` is an **audio-rate multi-channel** bus containing **13 trigger streams** (one per clock rate)
- `midiTrigBus` is an **audio-rate multi-channel** bus containing **8 trigger streams** (one per slot / MIDI channel)
- Selection must be done with `Select.ar(...)` on the audio-rate arrays

### 4.2 Wrong vs correct
```supercollider
// WRONG: triggers are NOT control-rate and not a single bus with offsets
// envTrig = In.kr(clockTrigBus + clockRate);
```

```supercollider
// CORRECT: select from 13-channel audio trigger bus
var allClockTrigs = In.ar(clockTrigBus, 13);
var clockTrig     = Select.ar(clockRate.round, allClockTrigs);

// CORRECT: select from 8-channel audio MIDI trigger bus
var allMidiTrigs = In.ar(midiTrigBus, 8);
var midiTrig     = Select.ar(slotIndex, allMidiTrigs);
```

### 4.3 How `~envVCA` already does it
`~envVCA` in `helpers.scd` is the SSOT and reads triggers with `In.ar(...)` and selects with `Select.ar(...)`.  
If you need custom envelopes, follow the same pattern (see next section).

---

## 5. Bus Model: Mapped Values (Not Normalized)

Control buses carry **mapped “real-world” values**:
- `freq` in Hz (or “frequency-like” units if the generator repurposes it)
- `cutoff` in Hz
- `attack/decay` in seconds
- `resonance` as RQ-like 0–1 domain
- `P1–P5` in the unit/range defined in the generator JSON

Python does the mapping (lin/exp/steps/invert), then writes **mapped values** to the buses.

**Rule:** do not “double-map” inside SC.  
If the JSON says `curve: "exp"` and Python already maps to Hz/seconds, SC should use the bus value as-is.

---

## 6. Generators With Custom Envelopes

Some generators need an *internal* envelope for things like:
- filter cutoff modulation (e.g. acid / 808-style)
- exciter shaping in physical models (karplus/modal)
- LPG-ish behavior

This is OK, but follow these rules:

### 6.1 Rules of the road
- **Triggers must be audio-rate** (`In.ar`, `Select.ar`) exactly like `~envVCA`
- Use `EnvGen.ar` for the custom envelope (not `.kr`)
- You have two safe options:
  1) **Keep `~envVCA` for amplitude** and use your custom envelope for timbre only  
  2) **Handle amplitude yourself** (multiply by `amp`) and skip `~envVCA` *only if* you fully replicate the envSource behavior and gating

### 6.2 Example: filter envelope (timbre), plus shared amp VCA

```supercollider
// Choose trigger source: 0=OFF, 1=CLK, 2=MIDI (same semantics as ~envVCA)
var trig = Select.ar(envSource, [
    DC.ar(0),
    Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
    Select.ar(slotIndex, In.ar(midiTrigBus, 8))
]);

// Note: for acid/808-style generators you often want the filter envelope to be
// independent from the amplitude envelope, so use a custom param instead of `decay`:
var filtDecay = In.kr(customBus3);  // P4 = filter envelope decay (example mapping)
var filtEnv = EnvGen.ar(Env.perc(0.001, filtDecay), trig);  // timbre envelope
// ... use filtEnv to modulate filter cutoff / wavefold / etc ...

// Then still apply shared amplitude VCA
sig = ~ensure2ch.(sig);
sig = ~multiFilter.(sig, filterType, filterFreq, rq);
sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
Out.ar(out, sig);
```

---

## 7. `~params[\amplitude]` (what it is and how to use it)

Generators typically do:

```supercollider
var amp = In.kr(~params[\amplitude]);
```

`~params[\amplitude]` is the **global per-slot amplitude scalar** (a control-rate bus stored in the `~params` dictionary).  
It is applied inside `~envVCA` (and sometimes multiplied for generator-specific gain staging).

**Guideline**
- If you bypass `~envVCA`, you *must* multiply by `amp` yourself:
  ```supercollider
  sig = sig * amp;
  ```
- If you keep `~envVCA`, pass `amp` to it (optionally scaled for a generator’s internal headroom).

---

## 8. Generator Metadata (.json) Contract

Each generator has a paired `*.json` describing UI + behavior.

### 8.1 Minimal schema

```json
{
  "name": "Human Name",
  "synthdef": "supercolliderSynthDefSymbol",
  "output_trim_db": -6.0,
  "midi_retrig": false,
  "pitch_target": null,
  "reference": null,
  "custom_params": []
}
```

### 8.2 `custom_params` (P1–P5)

Up to **5** entries. Each entry defines how Python maps slider → bus.

```json
{
  "key": "delay_time",
  "label": "DLY",
  "tooltip": "Delay Time",
  "default": 0.30,
  "min": 0.005,
  "max": 1.0,
  "curve": "exp",
  "unit": "s",
  "invert": false,
  "steps": null
}
```

**Field rules**
- `label`: keep short (3–4 chars recommended)
- `curve`: `"lin"` or `"exp"` (plus optional `steps`)
- `exp` requires `min > 0`
- `default` must be inside `[min, max]`
- `steps` implies quantized mapping

---

## 9. `pitch_target` semantics

`pitch_target` tells the system **where “pitch” should be applied** for this generator type.

- `null` (or missing): pitch controls the standard `frequency` bus
- `0..4`: pitch targets **custom param index** `P1..P5` (0=P1, 4=P5)

This is used for generators where “pitch” is conceptually something else (e.g. delay-time-as-pitch).

---

## 10. `midi_retrig` behavior (Karplus / Modal)

`midi_retrig` exists for **struck/plucked** models (e.g. Karplus, Modal) where MIDI mode needs **continuous retriggering while a key is held**, not just a single impulse.

- Python sends `midi_retrig` to SC when the generator type changes.
- In these generators, the MIDI trigger bus is treated as a **continuous retrigger stream** while a key is held (commonly ~30 Hz), so the exciter can be refreshed.

Concrete example (pattern used in `karplus_strong.scd`):
- in MIDI mode (`envSource=2`), use `midiTrigBus` as exciter trigger
- otherwise, use an internal retrig rate (from a custom param)

---

## 11. Output Normalization: `output_trim_db` (where it applies)

Generators vary wildly in perceived loudness. The system supports a per-generator trim:

- `output_trim_db` is stored in generator JSON
- Python sends it to SC via `gen_trim` when the generator type changes
- SC applies it as a **per-slot generator trim stage** (in dB) so generator types can be loudness-matched without touching the user’s strip gain/fader

**Rule:** keep this as SSOT — don’t bake loudness trims into the `.scd` unless you’re doing safety limiting.

---

## 12. Safety: When LeakDC / Limiter are REQUIRED

For generators with any of the following:
- feedback (`LocalIn`/`LocalOut`, delay chaos, resonant loops)
- hard nonlinearities (fold/clip) + high gain
- unstable filters / self-osc domains

…treat safety as **mandatory**, not optional.

Recommended minimal safety block (place *before* the post-chain):

```supercollider
sig = LeakDC.ar(sig);
sig = Limiter.ar(sig, 0.98);
```

This prevents NaNs/Infs and “silent after blowup” states that are painful to debug.

---

## 13. Adding a New Generator (10–20 min workflow)

1. Copy a close-ish `.scd` into `supercollider/generators/<new>.scd`
2. Copy its `.json` into `supercollider/generators/<new>.json`
3. Edit JSON:
   - `name`, `synthdef`, `output_trim_db`, `custom_params`, optional `pitch_target`, `midi_retrig`
4. Edit SC:
   - rename SynthDef symbol to match JSON `synthdef`
   - keep the contract (args + bus reads)
   - implement DSP into `sig`
   - keep canonical post-chain order
5. Add generator **name** to `GENERATOR_CYCLE` in `src/config/__init__.py`

---

## Appendix A: Canonical SynthDef Skeleton

```supercollider
SynthDef(\TEMPLATE, { |out,
    freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4|

    var freq       = In.kr(freqBus);
    var filterFreq = In.kr(cutoffBus);
    var rq         = In.kr(resBus);
    var attack     = In.kr(attackBus);
    var decay      = In.kr(decayBus);
    var filterType = In.kr(filterTypeBus);
    var envSource  = In.kr(envSourceBus);
    var clockRate  = In.kr(clockRateBus);
    var amp        = In.kr(~params[\amplitude]);

    var p1 = In.kr(customBus0);
    var p2 = In.kr(customBus1);
    var p3 = In.kr(customBus2);
    var p4 = In.kr(customBus3);
    var p5 = In.kr(customBus4);

    var sig;

    // ---- DSP ----
    // sig = ...

    // ---- Safety (REQUIRED for feedback/chaos generators) ----
    // sig = LeakDC.ar(sig);
    // sig = Limiter.ar(sig, 0.98);

    // ---- Optional width (mono-only) ----
    // sig = ~stereoSpread.(sig, 0.3, 0.2);

    // ---- Post-chain (SSOT, canonical order) ----
    sig = ~ensure2ch.(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);

    Out.ar(out, sig);
}).add;

"  ✓ TEMPLATE loaded".postln;
```
