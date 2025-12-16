# Feature Request: LFO Quadrature Expansion

**Created:** December 16, 2025  
**Status:** Proposal  
**Priority:** Medium

---

## Summary

Expand LFO from 3 outputs to 4 outputs with quadrature phase alignment (0°, 90°, 180°, 270°). Add a "Phase Pattern" control that shifts all phases together through preset patterns, exposable as a modulation target.

---

## Current State

- 3 outputs: A, B, C
- Default phases: 0°, 135°, 225° (roughly 120° spread)
- Per-output phase selection: 8 steps (0°-315° in 45° increments)
- Manual phase adjustment only

---

## Proposed Changes

### 1. Expand to 4 Outputs

| Output | Default Phase | Label |
|--------|---------------|-------|
| A | 0° | I (In-phase) |
| B | 90° | Q (Quadrature) |
| C | 180° | I̅ (Inverted) |
| D | 270° | Q̅ (Inverted Q) |

Classic quadrature arrangement used in:
- Analog synth quad LFOs (Buchla, Serge)
- Radio/DSP I/Q signals
- Vector synthesis panning

### 2. Phase Pattern Control

A new parameter that applies a **global phase offset** to all outputs simultaneously, shifting the entire pattern while maintaining relative spacing.

**Button behaviour:**
- Click cycles through preset patterns
- Each pattern defines base phases for A/B/C/D
- Individual per-output phase adjustments ADD to the pattern base

**Preset Patterns:**

| Pattern | A | B | C | D | Character |
|---------|---|---|---|---|-----------|
| QUAD | 0° | 90° | 180° | 270° | Classic quadrature |
| PAIR | 0° | 0° | 180° | 180° | Two pairs, opposition |
| SPREAD | 0° | 45° | 180° | 225° | Asymmetric tension |
| TIGHT | 0° | 22° | 45° | 67° | Subtle phase cluster |
| WIDE | 0° | 120° | 180° | 300° | Skewed hexagonal |
| SYNC | 0° | 0° | 0° | 0° | All in phase |

### 3. Phase Rotate Control

A stepped parameter (24 steps = 15° each) that rotates the entire pattern:

```
actual_phase[n] = (pattern_base[n] + per_output_offset[n] + (rotate_step * 15)) % 360
```

**Steps:** 0-23 (0°, 15°, 30°, 45° ... 330°, 345°)

**UI:** CycleButton or stepped slider, displays current rotation angle.

**Modulation target:** When mod routing is implemented, this becomes a powerful destination:
- Slow Sloth → drifting phase relationships
- Fast LFO → creates pseudo-chord phasing effects
- Envelope → phase sweep on each note

### 4. Phase Animation Modes (Future)

Beyond static patterns, animated phase relationships:

| Mode | Behaviour |
|------|-----------|
| STATIC | Manual control only |
| ROTATE | Continuous rotation at set rate |
| BOUNCE | Oscillate between two patterns |
| RANDOM | Jump to random pattern on trigger |
| CHASE | Sequential phase cascade |

**Pattern Transition Toggle:**
- HARD: Instant switch between patterns (default)
- MORPH: Smooth interpolation over ~100ms

---

## Implementation Notes

### Config Changes

```python
# config/__init__.py
MOD_OUTPUTS_PER_SLOT = 4  # was 3
MOD_LFO_OUTPUTS = ["A", "B", "C", "D"]  # new
MOD_LFO_PHASE_PATTERNS = {
    "QUAD": [0, 90, 180, 270],
    "PAIR": [0, 0, 180, 180],
    "SPREAD": [0, 45, 180, 225],
    "TIGHT": [0, 22, 45, 67],
    "WIDE": [0, 120, 180, 300],
    "SYNC": [0, 0, 0, 0],
}
MOD_BUS_COUNT = 16  # was 12 (4 slots × 4 outputs)
```

### JSON Changes (lfo.json)

```json
{
  "params": [
    {"key": "rate", ...},
    {"key": "shape", ...},
    {"key": "mode", ...},
    {"key": "pattern", "label": "PAT", "steps": 6, "default": 0},
    {"key": "rotate", "label": "ROT", "steps": 24, "default": 0}
  ],
  "outputs": 4
}
```

### SuperCollider Changes

```supercollider
// modLFO SynthDef - add 4th output bus
SynthDef(\modLFO, {
    arg outA, outB, outC, outD,  // 4 output buses
        rate=0, shape=0.5, mode=0, freq=1,
        waveA=0, waveB=0, waveC=0, waveD=0,
        phaseA=0, phaseB=2, phaseC=4, phaseD=6,  // 0°, 90°, 180°, 270° (in 45° steps)
        polA=1, polB=1, polC=1, polD=1,
        pattern=0, rotate=0;
    
    // ... phasor + pattern + rotate logic ...
    
    Out.kr(outA, sigA);
    Out.kr(outB, sigB);
    Out.kr(outC, sigC);
    Out.kr(outD, sigD);
}).add;
```

### UI Changes

- Output rows: 4 instead of 3
- New PAT button (CycleButton): QUAD/PAIR/SPREAD/TIGHT/WIDE/SYNC
- New ROT slider: 0-360° with drag popup showing degrees
- Scope: 4 traces (need 4th colour in skin)

### Bus Allocation

With 4 slots × 4 outputs = 16 mod buses:

| Slot | Outputs | Bus Range |
|------|---------|-----------|
| MOD 1 | A,B,C,D | 0-3 |
| MOD 2 | A,B,C,D | 4-7 |
| MOD 3 | A,B,C,D | 8-11 |
| MOD 4 | A,B,C,D | 12-15 |

---

## Visual Mockup

```
┌─────────────────────────────────────────┐
│ MOD 1                           [LFO]   │
├─────────────────────────────────────────┤
│  RATE  SHAP  MODE   PAT   ROT           │
│  ┌──┐  ┌──┐  ┌───┐ ┌────┐ ┌──┐          │
│  │▓▓│  │▓ │  │CLK│ │QUAD│ │▓▓│          │
│  └──┘  └──┘  └───┘ └────┘ └──┘          │
│                                         │
│  A  [Saw▼] [0°▼]   [BI]                 │
│  B  [Saw▼] [90°▼]  [BI]                 │
│  C  [Saw▼] [180°▼] [BI]                 │
│  D  [Saw▼] [270°▼] [BI]                 │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ ~~~~  ____  ....  ----          │    │  ← 4 traces
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## Modulation Target (Future)

When mod routing is implemented:

```
MOD 2 Sloth X  →  MOD 1 LFO ROT  (depth: 100%)
```

This would make the LFO's phase pattern slowly rotate based on Sloth chaos output - creating evolving, never-repeating phase relationships.

---

## Breaking Changes

- `MOD_OUTPUTS_PER_SLOT`: 3 → 4
- `MOD_BUS_COUNT`: 12 → 16
- Existing presets with mod routing would need migration
- Scope display needs 4th trace colour

---

## Decisions

1. **Sloth outputs:** Expand to 4 - add rectified sum output (see below)
2. **Pattern interpolation:** Switchable - hard cut default, smooth morph option
3. **Rotate steps:** 24 steps (15° each) - fine enough for musicality, coarse enough for easy control

---

## Sloth 4th Output: Rectified Sum

Based on NLC Triple Sloth rectifier circuit:

```
D = max(0, Apathy + Inertia - Torpor)
```

This creates a gate-like output that goes positive only when the slower outputs (Apathy + Inertia) overcome Torpor. Useful for:
- Irregular trigger/gate generation
- Threshold-based modulation
- Complex rhythmic patterns from chaos

**Output labels:**
| Output | Source | Character |
|--------|--------|-----------|
| X | Torpor | Fast chaos (15-30s) |
| Y | Apathy | Medium chaos (60-90s) |
| Z | Inertia (inverted) | Slow chaos (30-40min) |
| R | Rectified sum | Gate-like bursts |

---

## Dependencies

- None for basic 4-output expansion
- Mod routing system for ROT as modulation target

---

## Effort Estimate

| Task | Effort |
|------|--------|
| Config updates | Small |
| SC SynthDef changes | Medium |
| UI layout (4 rows + new controls) | Medium |
| Scope 4-trace support | Small |
| Pattern presets | Small |
| Rotate parameter | Small |
| Testing | Medium |
| **Total** | **~1 session** |

---

## References

- Buchla 281 Quad Function Generator
- Make Noise Maths (complementary outputs)
- Joranalogue Orbit (3-phase system)
- Doepfer A-143-9 Quadrature LFO
