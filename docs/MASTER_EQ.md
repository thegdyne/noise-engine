# Master EQ - DJ-Style 3-Band Isolator

**Status:** ✅ Complete (Phase 6)  
**Created:** 2025-12-14

---

## Overview

The master EQ is a **DJ-style 3-band isolator**, not a traditional parametric or graphic EQ. It splits the signal into three frequency bands using phase-coherent crossovers, allowing complete isolation (kill) of any band.

This design was chosen over a Mackie 8-Bus style 4-band EQ for its performance-oriented workflow - instant kills and dramatic tonal control.

---

## Signal Flow

```
Input → LR4 Split @ 250Hz → LO band ──────────────────┐
              ↓                                        │
           REST → LR4 Split @ 2500Hz → MID band ──────┼→ Sum → LO CUT → Output
                           ↓                           │
                        HI band ──────────────────────┘
```

---

## Architecture Decisions

### Why Serial LR4 Split (Not Subtraction)

**Problem with subtraction method:**
```supercollider
// BAD: Phase artifacts at crossover points
sigMid = HPF.ar(sig, 250) - HPF.ar(sig, 2500);
```

The subtraction method creates phase cancellation artifacts because the two HPFs have different phase responses at their crossover frequencies.

**Solution: Serial split**
```supercollider
// GOOD: Phase-coherent band sum
sigLo = LPF.ar(LPF.ar(sig, 250), 250);           // LO
sigRest = HPF.ar(HPF.ar(sig, 250), 250);         // Everything above 250Hz
sigMid = LPF.ar(LPF.ar(sigRest, 2500), 2500);   // MID (from REST)
sigHi = HPF.ar(HPF.ar(sigRest, 2500), 2500);    // HI (from REST)
```

This guarantees: `LO + MID + HI = Original Signal` (within filter artifacts)

### Why LR4 (Linkwitz-Riley 4th Order)

- 24dB/octave slope (double-filtered 12dB/oct filters)
- Flat summing at crossover point
- No phase issues when bands are summed
- Industry standard for crossover design

### Why -80dB Kill (Not -12dB)

**Problem:** `-12dB.dbamp = 0.25` - still audible, not a true kill

**Solution:** Dual-range gain mapping:
- Lower half of slider: -80dB to 0dB (practical silence to unity)
- Upper half of slider: 0dB to +12dB (unity to boost)

```supercollider
loGainLin = Select.kr(eqLoGain <= 0, [
    eqLoGain.linlin(0, 12, 0, 12).dbamp,      // Upper: 0 to +12dB
    eqLoGain.linlin(-12, 0, -80, 0).dbamp     // Lower: kill to unity
]).lag(0.02);
```

---

## Specifications

### Crossover Frequencies

| Band | Range | Crossover |
|------|-------|-----------|
| LO | 0 - 250Hz | LPF @ 250Hz |
| MID | 250Hz - 2500Hz | HPF @ 250Hz, LPF @ 2500Hz |
| HI | 2500Hz+ | HPF @ 2500Hz |

These frequencies are DJ-standard:
- 250Hz keeps kick/bass in LO
- 2500Hz puts hats/air in HI, presence in MID

### Gain Range

| Slider Position | Value | dB | Linear |
|-----------------|-------|-----|--------|
| Minimum (0) | -12 | -80dB | 0.0001 (kill) |
| Center (120) | 0 | 0dB | 1.0 (unity) |
| Maximum (240) | +12 | +12dB | 4.0 (boost) |

### Filter Topology

- Type: Linkwitz-Riley 4th order (LR4)
- Implementation: Cascaded 2nd-order filters (2× LPF or 2× HPF)
- Slope: 24dB/octave

---

## Controls

### Per-Band Sliders (LO / MID / HI)

- Range: -12dB (kill) to +12dB (boost)
- Center detent: 0dB (unity)
- ValuePopup shows current dB value

### Kill Buttons (LO / MID / HI)

- Instant mute regardless of slider position
- Toggle: click to kill, click again to restore
- Visual: dim when off, red when active
- Overrides slider gain with 0.0

### LO CUT Button

- 75Hz high-pass filter
- Removes sub-bass rumble
- Applied post-EQ (after band sum)
- 12dB/octave slope

### EQ Bypass Button

- Bypasses entire EQ section
- Signal passes through unprocessed
- Kill buttons have no effect when bypassed

---

## OSC Paths

| Path | Value | Description |
|------|-------|-------------|
| `/noise/master/eq/lo` | -12 to +12 | LO band gain (dB) |
| `/noise/master/eq/mid` | -12 to +12 | MID band gain (dB) |
| `/noise/master/eq/hi` | -12 to +12 | HI band gain (dB) |
| `/noise/master/eq/lo/kill` | 0/1 | LO kill button |
| `/noise/master/eq/mid/kill` | 0/1 | MID kill button |
| `/noise/master/eq/hi/kill` | 0/1 | HI kill button |
| `/noise/master/eq/locut` | 0/1 | LO CUT enable |
| `/noise/master/eq/bypass` | 0/1 | EQ bypass |

---

## UI Layout

```
┌─────────────────────────────────────┐
│ EQ                           [BYP] │
│  LO      MID      HI               │
│   █        █        █              │
│   █        █        █              │
│   █        █        █              │
│  [LO]    [MID]    [HI]   ← kills   │
│         [CUT]              ← lo cut │
└─────────────────────────────────────┘
```

---

## Implementation

### SuperCollider (master_passthrough.scd)

```supercollider
// First split: LO + REST
sigLo = LPF.ar(LPF.ar(sig, 250), 250);
sigRest = HPF.ar(HPF.ar(sig, 250), 250);

// Second split: MID + HI from REST
sigMid = LPF.ar(LPF.ar(sigRest, 2500), 2500);
sigHi = HPF.ar(HPF.ar(sigRest, 2500), 2500);

// Gain with kill override
loGainLin = Select.kr(eqLoKill, [loGainLin, DC.kr(0)]);

// Sum and apply LO CUT
sigEQ = (sigLo * loGainLin) + (sigMid * midGainLin) + (sigHi * hiGainLin);
sigEQ = Select.ar(eqLoCut, [sigEQ, HPF.ar(sigEQ, 75)]);
```

### Python (master_section.py)

- `eq_lo_slider`, `eq_mid_slider`, `eq_hi_slider` - DragSlider widgets
- `eq_lo_kill_btn`, `eq_mid_kill_btn`, `eq_hi_kill_btn` - Kill toggles
- `eq_locut_btn` - LO CUT toggle
- `eq_bypass_btn` - Bypass toggle

---

## Files

- `supercollider/effects/master_passthrough.scd` - DSP implementation
- `src/gui/master_section.py` - UI controls
- `src/config/__init__.py` - OSC path definitions

---

## Design Rationale

### Why DJ Isolator Instead of Parametric EQ?

1. **Performance-oriented** - Instant kills for live use
2. **Simple controls** - 3 sliders + 3 buttons vs 12+ knobs
3. **Dramatic effect** - Full band isolation, not subtle correction
4. **Phase-coherent** - Bands sum perfectly when at unity

### Why Fixed Crossovers?

- DJ-standard frequencies work for most material
- Reduces complexity (no sweep controls)
- Consistent behavior across sessions
- Sweepable crossovers can be added later if needed

### Kill Button Behavior

Kill buttons override slider position rather than setting slider to minimum because:
- Preserves slider position for instant restore
- Clearer visual feedback (button state vs slider position)
- Faster workflow (toggle vs drag)
