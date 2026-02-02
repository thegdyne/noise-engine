# How to Calibrate a Generator Against Hardware (Forensic Calibration Loop)

**Status:** Reference doc for hardware-to-digital alignment using telemetry  
**Prerequisite:** [Telemetry User Guide](TELEMETRY_USER_GUIDE.md), [How to Create a Generator](HOWTO_CREATE_GENERATOR.md)

## Overview

The Forensic Calibration Loop is the process used to align a digital Noise Engine generator with a physical hardware synthesizer. It uses the telemetry system to capture 1,024-sample windows of audio from the SuperCollider bus, compares them against a mathematical "Ideal" model in real-time, and iteratively tunes DSP parameters until the digital output matches the hardware's measured characteristics.

This guide walks through the complete process using the B258 generator (modelled on a Buchla 258 oscillator) as the worked example.

```
Hardware Synth  -->  Audio Interface  -->  hw_profile_tap  -->  Telemetry
                                                                   |
                                                            Compare against
                                                                   |
Digital Generator  -->  Intermediate Bus  -->  Telemetry  -->  Ideal Model
```

## Part 1: The Telemetry Infrastructure

### Forensic Markers

The telemetry system reports several metrics per capture window. These are the ones that matter for calibration:

| Marker | What It Measures | Why It Matters |
|--------|-----------------|----------------|
| **Peak** | Absolute maximum voltage in the capture window | Sets the amplitude ceiling for comparison |
| **RMS (Stage 3)** | Average power of the signal after the Ideal alignment stage | Core loudness metric -- must match hardware |
| **Peak-to-RMS (Crest Factor)** | Ratio of Peak to RMS -- the "peakedness" of the wave | Reveals compression. Hardware typically ~1.68, over-compressed digital ~1.05 |
| **ERR (RMS Error)** | Standard deviation between actual signal and calculated ideal waveform | Measures waveform shape accuracy |

The crest factor is the single most revealing diagnostic. A hardware Buchla 258 produces "spiky" waveforms with prominent peaks and a crest factor around 1.68. A digital clone that clips or saturates too hard will squash those peaks, pushing the crest factor down toward 1.0 -- the telltale sign of digital compression.

### The Calibration Stage (`calGain`)

The telemetry tap includes a software-only gain stage called `calGain`. This scales the digital measurement without altering the actual audio output.

**Purpose:** Match the digital Peak to a known hardware baseline so that RMS and crest factor can be compared 1:1.

```python
# Set calGain to normalize digital peak to hardware baseline
# If hardware peak = 0.681 and digital peak = 0.45:
cal_gain = 0.681 / 0.45  # = 1.513

client.send_message("/noise/telem/tap/enable", [slot, rate, cal_gain])
```

Once peaks are matched via `calGain`, the RMS comparison becomes meaningful -- any difference in RMS at equal peak levels reveals a shape difference in the waveform.

## Part 2: Capturing the Hardware Baseline

### Step 1: Physical Setup

Connect the hardware synthesizer to an audio interface (e.g., MOTU M6) and route it into Noise Engine using the **Generic Hardware Profiler** generator (`hw_profile_tap`).

```
Hardware Synth  --[1/4" cable]-->  MOTU M6 Input  --[USB]-->  Computer
                                                                |
                                                     Noise Engine Slot N
                                                     (hw_profile_tap loaded)
```

### Step 2: Configure the Profiler

Load `hw_profile_tap` into a slot and set its parameters:

| Param | Label | Setting | Purpose |
|-------|-------|---------|---------|
| P1 | CHN | Input channel (0-5) | Which MOTU M6 input the hardware is on |
| P2 | LVL | Start at 0.25, adjust | Digital gain normalisation |
| P3 | REF | 0.0=Sine, 0.5=Square, 1.0=Saw | Reference waveform for Ideal overlay |
| P4 | SYM | 0.5 (centered) | Adjusts Ideal overlay DC bias to match hardware slope |
| P5 | SAT | 0.0 initially | Saturation drive for matching analog softening |

### Step 3: Capture Hardware DNA

Enable the INTERNAL telemetry tap and sweep through the hardware's waveforms one at a time. For each waveform (sine, saw, square), record the baseline metrics:

```python
client.send_message("/noise/telem/tap/enable", [slot, 10, 1.0])
```

**Example -- Buchla 258 Hardware Baseline:**

| Waveform | Peak | RMS | Crest Factor |
|----------|------|-----|--------------|
| Saw | 0.683 | 0.406 | 1.68 |
| Sine | 0.681 | 0.480 | 1.42 |
| Square | 0.690 | 0.650 | 1.06 |

These numbers become the **Gold Standard** targets for the digital generator.

## Part 3: The Four-Round Tuning Process

With hardware DNA captured, switch to the digital generator and run the Forensic Loop.

### Round 0: Identify the DNA Gap

Load the digital generator (e.g., `b258_osc`) into a slot and enable telemetry. Capture initial snapshots and compare against hardware.

**Example -- Initial Digital State:**

| Metric | Hardware Target | Digital (Initial) | Gap |
|--------|----------------|-------------------|-----|
| Saw Peak | 0.683 | 0.682 | OK |
| Saw RMS | 0.406 | 0.649 | Too loud |
| Crest Factor | 1.68 | 1.05 | **Severely compressed** |

A crest factor of 1.05 (against a target of 1.68) means the peaks are flattened against a saturation ceiling -- the waveform is "fat" where it should be "spiky". This is the DNA gap.

### Round 1: Reduce Drive

The primary cause of peak flattening is excessive saturation. In `b258_osc.scd`, the `tanh` drive stage was compressing the peaks.

**Adjustment:** Lower the `tanh` drive multiplier until the crest factor starts rising.

```supercollider
// BEFORE: Drive too high, squashes peaks
sig = (sig * 1.35).tanh;

// AFTER: Nearly linear, preserves peak shape
sig = (sig * 1.01).tanh;
```

**Result:** Crest factor moves from 1.05 toward 1.3, but RMS drops because less saturation means less energy.

### Round 2: Compensate with Makeup Gain

Lower drive means lower RMS. Restore the RMS level with a per-branch makeup scalar that boosts the signal without re-introducing saturation.

```supercollider
// BEFORE: Low makeup, RMS too quiet after drive reduction
sig = sig * 1.08;

// AFTER: Higher makeup, restores RMS while preserving crest factor
sig = sig * 1.32;
```

The key insight: makeup gain is applied **before** the tanh stage, so it increases overall level. But because the drive multiplier is now nearly linear (1.01x), the tanh barely activates -- the peaks pass through unscathed.

### Round 3: Phase Alignment

For sawtooth waveforms, the hardware may produce a ramp-up while SuperCollider's `LFSaw` produces a ramp-down (or vice versa). This phase inversion doesn't affect the sound but breaks the Ideal overlay comparison.

**Solution:** Use the **INV** (Invert) button in the telemetry UI to flip the phase of the ideal overlay for accurate error measurement.

```
Telemetry UI:  [INV] button toggles phase inversion on the Ideal overlay
               Use when ERR is high but the waveform looks visually correct (just flipped)
```

### Round 4: Gold Lock

The tuning concludes when the digital generator reaches **100% RMS Parity** with the hardware for the target waveform.

**Final Locked State (B258 Saw at CAL 1.000):**

| Metric | Hardware Target | Digital (Final) | Status |
|--------|----------------|-----------------|--------|
| Saw RMS | 0.406 | 0.405 | **LOCKED** |
| Crest Factor | 1.68 | 1.52 | Approaching target |
| ERR | -- | <0.01 | Minimal |

A crest factor of 1.52 vs 1.68 means there's still a small amount of digital compression, but RMS parity at 0.405/0.406 confirms the overall energy envelope matches the hardware. This is acceptable for a "Gold Lock" -- further refinement yields diminishing returns.

## Part 4: The Gold Lock Spec

Once calibration is complete, document the locked DSP values in the SynthDef source as a permanent reference. These values are the **Digital Twin Spec** and must not be changed without re-running the full calibration loop.

**Example -- B258 Gold Lock Values:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Makeup Scalar | `1.32` | Per-branch gain (sine/saw) |
| Drive Multiplier | `0.01` | Preserves linear crest factor |
| Global Level | `sig * 0.68` | Final output scaling |

```supercollider
// === GOLD LOCKED VALUES (from Forensic Calibration 2026-01-xx) ===
// Do not modify without re-running calibration loop
var makeupScalar = 1.32;
var driveMult = 0.01;

sig = (sig * makeupScalar);          // Makeup gain
sig = (sig * (1 + (sat * driveMult))).tanh;  // Near-linear drive
sig = sig * 0.68;                     // Global level
```

## Repeating the Loop for a New Generator

The process generalises to any hardware/digital pair:

### Checklist

- [ ] **Hardware baseline captured** -- Peak, RMS, and Crest Factor for each waveform
- [ ] **Profiler configured** -- `hw_profile_tap` loaded with correct CHN and REF settings
- [ ] **DNA gap identified** -- Initial digital metrics compared against hardware targets
- [ ] **Drive reduced** -- Saturation lowered until crest factor starts recovering
- [ ] **Makeup gain applied** -- RMS restored without re-introducing compression
- [ ] **Phase aligned** -- INV button used where needed for accurate overlay comparison
- [ ] **Gold Lock achieved** -- RMS within 0.01 of hardware target
- [ ] **Values documented** -- Locked DSP constants recorded in SynthDef source comments

### Template: Gold Lock Header

Add this to the top of any calibrated generator's `.scd` file:

```supercollider
/*
FORENSIC CALIBRATION RECORD
Hardware: [manufacturer] [model]
Interface: [audio interface model]
Date: [YYYY-MM-DD]

Gold Lock Targets:
  Sine  -- Peak: [x.xxx]  RMS: [x.xxx]  Crest: [x.xx]
  Saw   -- Peak: [x.xxx]  RMS: [x.xxx]  Crest: [x.xx]
  Square -- Peak: [x.xxx]  RMS: [x.xxx]  Crest: [x.xx]

Locked DSP Values:
  Makeup Scalar: [x.xx]
  Drive Multiplier: [x.xx]
  Global Level: [x.xx]
*/
```

## Key Files

| File | Purpose |
|------|---------|
| `packs/core/generators/hw_profile_tap.scd` | Generic Hardware Profiler SynthDef |
| `packs/core/generators/hw_profile_tap.json` | Profiler config (CHN, LVL, REF, SYM, SAT) |
| `packs/core/generators/b258_osc.scd` | B258 Dual Oscillator (calibrated) |
| `packs/core/generators/reference_sine.scd` | Pure sine reference for A/B testing |
| `supercollider/core/telemetry_tap.scd` | Telemetry infrastructure |
| `src/gui/telemetry_window.py` | Telemetry UI with INV button and Ideal overlay |

## Terminology Quick Reference

| Term | Meaning |
|------|---------|
| **Forensic Marker** | A telemetry metric used for calibration (Peak, RMS, Crest Factor, ERR) |
| **DNA Gap** | The measured difference between hardware and digital behaviour |
| **Gold Lock** | Calibration state where digital RMS matches hardware within 0.01 |
| **calGain** | Software-only gain in the telemetry tap for level-matching |
| **Crest Factor** | Peak ÷ RMS -- reveals waveform "peakedness" vs compression |
| **Makeup Scalar** | Post-drive gain that restores RMS without reintroducing saturation |
| **INV** | Phase inversion toggle in telemetry UI for overlay alignment |

---

**End of Guide**
