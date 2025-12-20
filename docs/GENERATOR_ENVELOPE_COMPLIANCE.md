# Generator Envelope Compliance Analysis

**Date:** December 2025  
**Status:** Analysis Complete, Awaiting Implementation  
**Related:** `docs/GENERATOR_SPEC.md`, Pack System Phase 3

---

## Executive Summary

Pack generators (Electric Shepherd, R'lyeh Collection) do not use the `~envVCA` helper function, causing ATK/DEC controls and CLK/MIDI triggering to be non-functional. This analysis documents the root cause, impact, and recommended fix.

---

## Problem Statement

### Observed Behavior

- ATK (Attack) and DEC (Decay) sliders have no audible effect on pack generators
- CLK (Clock) trigger mode produces no rhythmic gating
- MIDI trigger mode doesn't apply attack/decay envelope
- All pack generators behave as drones regardless of trigger mode setting

### Expected Behavior (per GENERATOR_SPEC.md)

- ATK/DEC should control envelope shape
- CLK mode should trigger envelope from clock divisions
- MIDI mode should trigger envelope from note-on messages
- OFF mode should drone (no envelope)

---

## Root Cause Analysis

### 1. Spec Exists But Tests Don't Enforce It

`test_generators.py` validates:
- ✅ JSON structure (name, synthdef, custom_params)
- ✅ SCD files exist and contain `SynthDef`
- ✅ Standard bus arguments present (freqBus, cutoffBus, attackBus, decayBus)
- ✅ Uses `~ensure2ch`

Critically missing:
- ❌ Uses `~envVCA`
- ❌ Uses `~multiFilter`

### 2. Pack Generators Have Zero SCD Validation

`test_packs.py` only checks:
- Manifest structure
- Discovery logic
- Synthdef name collisions

It never opens `.scd` files in pack generators to validate spec compliance.

### 3. Creative Session Drift

When atmospheric/drone generators were created, focus was on sound design. The pattern `sig * amp` was used once, then copy-pasted. Without a failing test, nothing flagged the deviation.

### 4. The Spec is Documentation, Not Enforcement

`GENERATOR_SPEC.md` is a guide — there's no CI check that rejects PRs when SCD doesn't call `~envVCA`.

---

## Technical Details

### What Pack Generators Do (Wrong)

All 16 pack generators end with:
```supercollider
sig = sig * amp;  // Direct amplitude - ignores envelope
```

### What They Should Do (Per Spec)

```supercollider
sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, 
               clockTrigBus, midiTrigBus, slotIndex);
```

### Affected Files

**Electric Shepherd (8 generators):**
- `packs/electric-shepherd/generators/beacon.scd`
- `packs/electric-shepherd/generators/dusk.scd`
- `packs/electric-shepherd/generators/feedr.scd`
- `packs/electric-shepherd/generators/husk.scd`
- `packs/electric-shepherd/generators/liminal.scd`
- `packs/electric-shepherd/generators/longing.scd`
- `packs/electric-shepherd/generators/static.scd`
- `packs/electric-shepherd/generators/tether.scd`

**R'lyeh Collection (8 generators):**
- `packs/rlyeh/generators/abyss.scd`
- `packs/rlyeh/generators/cthulhu.scd`
- `packs/rlyeh/generators/dagon.scd`
- `packs/rlyeh/generators/madness.scd`
- `packs/rlyeh/generators/rlyeh.scd`
- `packs/rlyeh/generators/tempest.scd`
- `packs/rlyeh/generators/tentacle.scd`
- `packs/rlyeh/generators/vessel.scd`

### Core Generators (Correct Reference)

These use `~envVCA` correctly:
- `supercollider/generators/additive.scd`
- `supercollider/generators/fm.scd`
- `supercollider/generators/subtractive.scd`
- (and all other core generators)

---

## Why This Fix is Safe

### ~envVCA Behavior by Mode

| envSource | Behavior |
|-----------|----------|
| 0 (OFF) | Just multiplies by `amp` — **identical to `sig * amp`** |
| 1 (CLK) | Applies attack/decay envelope triggered by clock |
| 2 (MIDI) | Applies attack/decay envelope triggered by MIDI notes |

**Key insight:** When user has OFF selected, `~envVCA` produces mathematically identical output to `sig * amp`. The fix adds capability without changing default sound.

### What Stays the Same

- All internal processing layers (the creative sound design)
- The character and texture of each generator
- Default behavior when trigger mode is OFF
- Custom parameter behavior (P1-P5)

### What Gets Added

- ATK/DEC sliders now functional
- CLK mode triggers rhythmic gating
- MIDI mode applies note-triggered envelopes

---

## Recommended Solution

### Phase 1: Fix Pack Generators

Replace `sig = sig * amp;` with full `~envVCA` call in all 16 pack generators.

**Change pattern:**
```supercollider
// BEFORE (line ~123-140 in each file)
sig = sig * amp;

// AFTER
sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, 
               clockTrigBus, midiTrigBus, slotIndex);
```

### Phase 2: Add CI Enforcement

**In `test_generators.py`:**
```python
def test_scd_files_use_envVCA(self, generators_dir):
    """Generators use ~envVCA helper for envelope control."""
    for filename in os.listdir(generators_dir):
        if filename.endswith('.scd'):
            filepath = os.path.join(generators_dir, filename)
            with open(filepath, 'r') as f:
                content = f.read()
            assert '~envVCA' in content, \
                f"{filename} should use ~envVCA helper for envelope control"
```

**In `test_packs.py`:**
```python
def test_pack_scd_files_use_envVCA(self):
    """Pack generators use ~envVCA helper."""
    # Similar logic, iterate over pack generator directories
```

### Phase 3: Update Spec Documentation

Add to `GENERATOR_SPEC.md`:

1. **REQUIRED helpers section** — clarify `~envVCA` is mandatory, not optional
2. **Drone-only pattern** (future) — if truly envelope-free generators are needed
3. **Common mistakes section** — document `sig * amp` anti-pattern

---

## Future Consideration: Drone-Only Generators

If creative needs require truly envelope-free generators, add optional JSON field:

```json
{
    "name": "Ambient Drone",
    "synthdef": "ambient_drone",
    "envelope_mode": "none",
    "custom_params": [...]
}
```

**UI behavior when `envelope_mode: "none"`:**
- Grey out ATK/DEC sliders
- Grey out CLK in trigger selector (only OFF/MIDI)
- MIDI pitch still works
- Show subtle "DRONE" or "∞" indicator

**Not implementing now** — all current pack generators benefit from envelope capability. Can add if a genuine use case emerges.

---

## Testing Checklist

| Test | Expected | Status |
|------|----------|--------|
| FEEDR with OFF mode | Sounds identical to before | ⬜ |
| FEEDR with CLK mode | Rhythmic gating works | ⬜ |
| FEEDR with MIDI mode | Note triggers envelope | ⬜ |
| ATK slider audible in CLK mode | Attack time changes | ⬜ |
| DEC slider audible in CLK mode | Decay time changes | ⬜ |
| All 8 Electric Shepherd gens | Pass above tests | ⬜ |
| All 8 R'lyeh gens | Pass above tests | ⬜ |
| CI passes with new tests | ~envVCA enforcement works | ⬜ |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Sound changes in OFF mode | Very Low | High | Math is identical; test each generator |
| Fix introduces bugs | Low | Medium | Mechanical change; test CLK/MIDI modes |
| CI blocks valid generators | Low | Low | Test on existing core generators first |
| Users confused by change | Very Low | Low | No UI change; adds capability |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Dec 2025 | Fix all pack generators to use ~envVCA | Adds capability without changing default sound; aligns with spec |
| Dec 2025 | Add CI test for ~envVCA presence | Prevents future drift |
| Dec 2025 | Defer drone_only flag | No current need; can add later if required |

---

## References

- `docs/GENERATOR_SPEC.md` — Generator creation specification
- `docs/PACK_SYSTEM_SPEC.md` — Pack system specification
- `tests/test_generators.py` — Core generator tests
- `tests/test_packs.py` — Pack discovery tests
- `supercollider/core/helpers.scd` — ~envVCA implementation

---

*This document should be updated when the fix is implemented and tests are passing.*
