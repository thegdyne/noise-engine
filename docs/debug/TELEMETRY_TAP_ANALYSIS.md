# Telemetry Tap Point Analysis

**Date:** 2025-02-06
**Branch:** claude/debug-telemetry-validation-xmP4t (from new_258)
**Status:** Investigation only — no code changes

---

## 1. Tap Point Trace

### Signal Chain (actual, per slot)

```
[Generator]
    │ ReplaceOut.ar
    ▼
~intermediateBus[idx]          ◄── TAP 0: Pre-Analog
    │ In.ar (read)
    ▼
[ne_analog_stage]              TAPE / TUBE / FOLD / CLEAN
    │ ReplaceOut.ar
    ▼
~enhancedBus[idx]              ◄── TAP 1: Post-Analog
    │ In.ar (read)
    ▼
[ne_endstage_standard]         LeakDC → Filter → Envelope/VCA → Limiter
    │ Out.ar
    ▼
~genBus[idx]                   ◄── TAP 2: Post-Endstage
    │ In.ar (read)
    ▼
[channelStrip]                 Vol / Pan / EQ / FX sends
    │ Out.ar
    ▼
~drySumBus → Master
```

### Bus Resolution (telemetry_tap.scd:132-138)

```
~telemetry.busForSource = { |idx, sourceId|
    case
        { sourceId == 0 } { ~intermediateBus[idx].index }   // Pre-Analog
        { sourceId == 1 } { ~enhancedBus[idx].index }        // Post-Analog
        { sourceId == 2 } { ~genBus[idx].index }             // Post-Endstage
        { ~intermediateBus[idx].index };                     // default fallback
};
```

### Node Execution Order

```
clockGroup
  └── masterClock

genGroup
  └── slotGroup[idx]
        ├── genSubGroup[idx]       ← Generator writes to intermediateBus
        ├── analogSubGroup[idx]    ← Analog stage: reads intermediateBus, writes enhancedBus
        └── endstageSubGroup[idx]  ← End-stage: reads enhancedBus, writes genBus

stripGroup
  └── channelStrip[idx]            ← Reads genBus, writes drySumBus

fxGroup
  └── FX synths (tape echo, reverb)

[Telemetry synths]                 ← Placed ~fxGroup, \addAfter
  ├── forge_internal_telem_tap     ← Data tap (RMS, freq, params)
  └── forge_telemetry_wave_capture ← Waveform buffer capture
```

Telemetry synths execute AFTER all signal-writing nodes have completed.
All three buses contain their final values by the time the tap reads them.

### Full Code Path: UI → OSC → Bus

```
TelemetryWidget._on_source_changed(index)     [telemetry_widget.py:806-808]
  → TelemetryController.set_source(source_id)  [telemetry_controller.py:638-655]
    → osc.send('telem_source', [slot+1, source_id])
      → /noise/telem/source OSC message
        → OSCdef(\telemSource)                  [telemetry_tap.scd:207-260]
          → ~telemetry.sourceIds[idx] = sourceId
          → tapBus = ~telemetry.busForSource(idx, sourceId)
          → Free + respawn forge_internal_telem_tap with \inBus = tapBus
          → Free + respawn forge_telemetry_wave_capture with \inBus = tapBus
```

---

## 2. Tap Point Analysis

```
Tap Point Analysis
==================
pre-analog:    bus=~intermediateBus[idx], location=post-generator/pre-analog-stage, correct=YES
post-analog:   bus=~enhancedBus[idx],     location=post-analog-stage/pre-endstage,  correct=YES
post-endstage: bus=~genBus[idx],          location=post-endstage/pre-channel-strip,  correct=YES

Issue found: NO (bus wiring is correct)
```

**The bus mapping is correct.** Each tap point reads from the intended location
in the signal chain. No bus is written to by an unexpected node, and no signal
bleeds between buses.

---

## 3. Root Cause Analysis: What IS Causing 48% THD?

The tap points are wired correctly, so the 48% THD observed on b258_dna at
morph=0 has a **different root cause**. There are two candidates:

### Candidate A: Analog Stage Coloring (MOST LIKELY)

If the telemetry is set to **Post-Analog** (source 1 = `~enhancedBus`), the
analog stage (`ne_analog_stage`) sits between the generator and this tap point.

Even with `type=0` (CLEAN selected), the analog stage always runs:
- `LeakDC.ar(sig)` — DC blocking (endstage.scd:148)
- `.softclip` — soft saturation (endstage.scd:148)

And if `enable > 0` with type = TAPE (1), TUBE (2), or FOLD (3):
- TAPE: `sig.tanh` saturation + sag + bias shift → **adds even harmonics + DC**
- TUBE: asymmetric waveshaping → **adds even harmonics + DC**
- FOLD: `Fold.ar` wavefolding → **massive harmonic generation**

The measured **DC offset of 0.12** strongly suggests TAPE or TUBE mode, which
both introduce asymmetric bias shifts that produce DC offset. A pure sine
through TUBE at moderate drive easily produces 40-50% THD.

**Verification:** Switch tap to **Pre-Analog** (source 0). If THD drops to
<6%, the analog stage is the source.

### Candidate B: Generator Residual Harmonics (MINOR)

The b258_dna generator at morph=0 is NOT a pure sine. The hardware-captured
harmonic tables at index 0 contain residual harmonics:

```
SAW oscillator at morph=0:
  h1=1.000, h2=0.012, h3=0.045, h4=0.008, h5=0.022,
  h6=0.007, h7=0.006, h8=0.008

Calculated THD = sqrt(h2² + h3² + ... + h8²) ≈ 5.3%
```

This 5.3% THD is from the hardware capture data itself — it represents the
real Buchla 258's residual nonlinearity at the "sine" position. It cannot
explain 48% THD.

### Candidate C: Endstage Filter Resonance

If tapping at **Post-Endstage** (source 2 = `~genBus`), the endstage applies:
- `~multiFilter` (LP/HP/BP with resonance)
- `~envVCA` (envelope + VCA)
- `Limiter.ar(sig, 0.95)`

A low-pass filter at 200Hz with high resonance would boost the fundamental
and add a resonance peak, significantly altering the waveform shape and THD.
This is expected behavior at this tap point.

---

## 4. Verification Test Protocol

### Setup
1. Load b258_dna in any slot
2. Set morph controls to 0 (P0=0, P1=0, P2=0)
3. Set frequency to ~100Hz
4. Disable the analog stage (ANALOG enable = OFF)
5. Set filter to OFF or cutoff = 20kHz (fully open)
6. Set envelope source to FREE (continuous)

### Test Matrix

| Step | Tap Point     | Analog Stage | Filter      | Expected THD | Expected DC |
|------|---------------|-------------|-------------|-------------|------------|
| 1    | Pre-Analog    | OFF         | Open        | ~5% (residual hw harmonics) | ~0.00 |
| 2    | Post-Analog   | OFF         | Open        | ~5% (same + LeakDC/softclip) | ~0.00 |
| 3    | Post-Analog   | TAPE, drive=0.5 | Open   | 20-50% (saturation) | 0.02-0.15 |
| 4    | Post-Analog   | TUBE, drive=0.5 | Open   | 30-60% (asymmetric) | 0.05-0.20 |
| 5    | Post-Endstage | OFF         | LP 200Hz, res=0.8 | varies (filtered) | ~0.00 |
| 6    | Post-Endstage | TAPE        | LP 200Hz, res=0.8 | high (both) | varies |

### Pass Criteria
- Step 1: THD < 6%, DC < 0.01 → Confirms generator is clean
- Step 2: THD < 6%, DC < 0.01 → Confirms analog bypass is transparent
- Step 3-4: THD > 20% → Confirms analog stage IS the coloring source
- Step 5-6: Waveform visibly filtered → Confirms endstage is post-tap for sources 0 & 1

### If Step 1 Shows 48% THD
That would indicate a genuine bus routing error (bus collision, wrong index).
Debug by printing bus indices at boot:
```supercollider
8.do { |i| "Slot %: inter=% enhanced=% gen=%".format(
    i+1, ~intermediateBus[i].index, ~enhancedBus[i].index, ~genBus[i].index
).postln; };
```
Check for overlapping indices.

---

## 5. Documentation Issue Found

**endstage.scd line 8** has a stale signal flow comment:
```
Signal flow per slot:
  [Generator] → intermediateBus[slot] → [End-Stage] → genBus[slot] → [Channel Strip]
```

This omits the analog stage and `enhancedBus`. The actual flow is:
```
[Generator] → intermediateBus → [Analog Stage] → enhancedBus → [End-Stage] → genBus → [Channel Strip]
```

This stale comment likely contributed to the confusion about what "downstream"
processing exists between the generator and the telemetry tap.

---

## 6. Summary

| Finding | Status |
|---------|--------|
| Bus wiring correct | YES — all 3 tap points map to the right buses |
| Tap synth execution order | CORRECT — runs after all writers |
| No bus collisions | CONFIRMED — no unexpected writers |
| Analog stage as THD source | LIKELY — especially TAPE/TUBE modes |
| DC offset from analog stage | LIKELY — TAPE sag bias or TUBE asymmetry |
| Stale endstage.scd comment | YES — line 8 omits analog stage |
| Generator THD at morph=0 | ~5.3% (from hardware capture residuals) |

**Conclusion:** The telemetry tap points are correctly wired. The observed
48% THD and 0.12 DC offset are most likely caused by the **analog stage**
(TAPE or TUBE mode) sitting between the generator and the Post-Analog tap
point. The fix is either:
1. Use Pre-Analog tap to measure raw generator output, or
2. Disable the analog stage before measuring, or
3. Acknowledge that Post-Analog includes analog stage coloring by design.
