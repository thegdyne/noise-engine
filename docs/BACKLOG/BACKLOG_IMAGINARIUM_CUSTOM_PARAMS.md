# Imaginarium Custom Params (P1-P5)

**Priority:** P1 — Blocks pack usability  
**Effort:** 2-3 sessions  
**Status:** Not started

---

## Problem

Imaginarium-generated SynthDefs declare `customBus0-4` in the arglist (contract compliant) but **never read from them**. All synthesis parameters are baked as literals at generation time.

**Result:** P1-P5 sliders in the UI do nothing for Imaginarium packs.

### Evidence

```supercollider
// Current: values baked at generation time
width = 0.1186 + (SinOsc.kr(3.1665) * 0.3243);
fbAmount = 1.1463 * fbMod;
partialAmp = 1 / (harmonic ** 0.5242);

// Required: read from buses, user-controllable
var pulseWidth = In.kr(customBus0);
width = pulseWidth.linlin(0, 1, 0.1, 0.9);
```

### Scope

| Component | Status |
|-----------|--------|
| Core generators (supercollider/generators/) | ✓ Correct — have custom_params, read buses |
| Imaginarium pack generators | ✗ Broken — buses declared but ignored |
| Generator JSON export | ✗ Missing — custom_params array empty |

---

## Solution

### Part 1: Define Param Axes per Method

Each synthesis method template defines 5 controllable parameters mapped to customBus0-4.

**Example: dark_pulse method**
| Slot | Key | Label | Range | Description |
|------|-----|-------|-------|-------------|
| P1 | pulse_width | WID | 0.1-0.9 | Base pulse width |
| P2 | pwm_depth | PWM | 0-1 | Width modulation depth |
| P3 | pwm_rate | RAT | 0.1-10 Hz | Width LFO rate |
| P4 | drive | DRV | 0-1 | Saturation amount |
| P5 | brightness | BRT | 0-1 | Filter cutoff ratio |

### Part 2: Update SynthDef Templates

Templates must read all 5 custom buses and use them:

```supercollider
// Read custom params
var pulseWidth = In.kr(customBus0);
var pwmDepth = In.kr(customBus1);
var pwmRate = In.kr(customBus2);
var drive = In.kr(customBus3);
var brightness = In.kr(customBus4);

// Use them
width = pulseWidth.linlin(0, 1, 0.1, 0.9);
width = width + (SinOsc.kr(pwmRate.linexp(0, 1, 0.1, 10)) * pwmDepth * 0.4);
```

### Part 3: Export custom_params JSON

Export pipeline must generate proper custom_params array:

```json
{
  "name": "Dark Pulse 1 [pack]",
  "synthdef": "imaginarium_pack_dark_pulse_001",
  "custom_params": [
    {"key": "pulse_width", "label": "WID", "tooltip": "Base pulse width", "default": 0.5, "min": 0.0, "max": 1.0, "curve": "lin"},
    {"key": "pwm_depth", "label": "PWM", "tooltip": "Width modulation depth", "default": 0.3, "min": 0.0, "max": 1.0, "curve": "lin"},
    ...
  ]
}
```

---

## Method Templates Requiring Update

| Family | Method | P1 | P2 | P3 | P4 | P5 |
|--------|--------|----|----|----|----|-----|
| subtractive | bright_saw | Detune | Spread | Drive | Sub | Brightness |
| subtractive | dark_pulse | Width | PWM Depth | PWM Rate | Drive | Brightness |
| subtractive | multi_osc | Mix | Detune | Spread | Sub | Noise |
| fm | simple_fm | Ratio | Index | Feedback | Drift | Brightness |
| fm | feedback_fm | FB Amount | FB Mod | Drive | Drift | Brightness |
| physical | karplus | Damping | Brightness | Position | Noise | Stretch |
| physical | modal | Decay | Brightness | Inharmonic | Strike | Resonance |
| noise | filtered_noise | Color | Bandwidth | Movement | Density | Brightness |
| additive | additive | Partials | Odd/Even | Detune | Drift | Brightness |
| ring | ring_mod | Carrier | Mod Freq | Depth | Balance | Brightness |
| formant | formant | Vowel | Formant Shift | Breathiness | Vibrato | Brightness |

---

## Implementation Phases

### Phase 1: Reference Implementation (1 session)
- [ ] Pick one method (suggest: `dark_pulse` — simple, clear params)
- [ ] Define 5 param axes with ranges, curves, defaults
- [ ] Update SynthDef template to read customBus0-4
- [ ] Update export to include custom_params JSON
- [ ] Test: generate pack, verify P1-P5 sliders work
- [ ] Document pattern for other methods

### Phase 2: Subtractive Family (1 session)
- [ ] Apply pattern to bright_saw
- [ ] Apply pattern to multi_osc
- [ ] Verify determinism still works (same seed → same output)

### Phase 3: Remaining Families (1 session)
- [ ] FM family (simple_fm, feedback_fm)
- [ ] Physical family (karplus, modal)
- [ ] Texture family (filtered_noise, additive, ring_mod, formant)

### Phase 4: Validation
- [ ] Regenerate test pack with new templates
- [ ] Verify all 8 generators have working P1-P5
- [ ] Run determinism test (identical seeds → identical output)
- [ ] Update verification scripts if needed

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/imaginarium/methods/*.py` | Add `custom_params` definitions per method |
| `src/imaginarium/templates/*.scd.j2` | Read customBus0-4, use in synthesis |
| `src/imaginarium/export.py` | Include custom_params in JSON output |
| `tests/test_imaginarium_params.py` | New — verify params are controllable |

---

## Success Criteria

- [ ] All Imaginarium method templates define 5 custom params
- [ ] Generated SynthDefs read from customBus0-4 (not baked literals)
- [ ] Generated JSON includes proper custom_params array
- [ ] P1-P5 sliders audibly affect generated sounds
- [ ] Determinism preserved (seed contract still valid)
- [ ] One reference method documented as pattern for contributors

---

## Open Questions

1. **Default values** — Should defaults be baked from generation, or fixed per method?
   - Option A: Baked (current value becomes default) — more variety
   - Option B: Fixed (method defines standard defaults) — more predictable

2. **Param ranges** — Normalized 0-1 internally, or actual units (Hz, ms)?
   - Recommend: 0-1 normalized, mapped in SynthDef (matches core generators)

3. **Macro relationship** — How do custom params relate to IMAGINARIUM_SPEC macros (TONE, EDGE, MOTION)?
   - Probably orthogonal — macros are generation-time, custom params are runtime

---

## Notes

This is a **usability blocker** — users expect P1-P5 to do something. Packs without working custom params feel broken compared to core generators.

Fix priority: Higher than Detail Layer (Phase A in PlanTo100) because this affects existing generated packs.
